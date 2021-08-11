/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

   Command Processor

   This receives commands over a serial link and executes them. If arguments are not sent in a
   timely manner, then the command is aborted and the system resumes as if it never happened.

*/

#include "common.h"
#include "dfmadapter.h"
#include "uart.h"
#include "display.h"
#include "counters.h"
#include "inputs.h"
#include "outputs.h"
#include "keypad.h"
#include "card.h"
#include "speaker.h"
#include "log.h"
#include "time.h"
#include "cmd.h"

// This is required for some functions we want to keep, but throw a warning because they
// currently are not used.
#define USED __attribute__((used))

#define CMD_BAUD_RATE            38400
#define CYCLE_TIMEOUT            2000
#define GFX_LOADSERIAL_TIMEOUT   1500

static int16_t Cycles = 0;
static uint8_t CurrentCommand = 0;
static uint16_t TotalErrors = 0;

// These are the command arguments. I keep them in static storage so that the stack doesn't
// have to be adjusted on each command execution.
static uint8_t ByteArgs[16];
static uint16_t WordArgs[4];
static char StringArg[MAX_STRING_SIZE];
static uint32_t Timer = 0;

// This is the buffer for bitmap data. Add 4 bytes for width, height and other stuff.
static BITMAP BitmapStruct;
static uint8_t BitmapBuffer[FRAMEBUFFER_SIZE + 4];
static const uint8_t *BitmapBufferEnd;
static uint8_t *BitmapPointer;

// These are for the framebuffer loading/saving.
static volatile uint8_t *FramebufferBegin = NULL;
static const uint8_t *FramebufferEnd = NULL;

// The arguments are also named these.
#define ARG_ID       (ByteArgs[0])
#define ARG_STATE    (ByteArgs[1])
#define ARG_X        (ByteArgs[2])
#define ARG_Y        (ByteArgs[3])
#define ARG_X2       (ByteArgs[4])
#define ARG_Y2       (ByteArgs[5])
#define ARG_COLOR    (ByteArgs[6])
#define ARG_W        (ByteArgs[7])
#define ARG_H        (ByteArgs[8])

#define ARG_FREQ     (WordArgs[0])
#define ARG_DURATION (WordArgs[1])

#define ARG_STRING   (StringArg)

// Argument error handler
#define ARG_ERROR()  goto ErrorHandler;

static void USED ByteWriterImpl (uint8_t ch)
{
   Uart3Write(ch);
}

static inline uint8_t GetByte (uint8_t *dest)
{
   // Immediately available?
   if (Uart3Available()) {
      *dest = Uart3Read();
      return true; 
   }

   // Not immediately available!
   for (Cycles = 0; Cycles < CYCLE_TIMEOUT; Cycles++) {
      if (Uart3Available()) {
         *dest = Uart3Read();
         return true;
      }
   }

   // We never received anything.
   return false;
}

static inline uint8_t GetWord (uint16_t *dest)
{
   union { uint16_t word; uint8_t bytes[2]; } var;

   if (!GetByte(&var.bytes[0])) return false;
   if (!GetByte(&var.bytes[1])) return false;

   return var.word;
}

static inline uint8_t GetDWord (uint32_t *dest)
{
   union { uint32_t dword; uint8_t bytes[4]; } var;

   if (!GetByte(&var.bytes[0])) return false;
   if (!GetByte(&var.bytes[1])) return false;
   if (!GetByte(&var.bytes[2])) return false;
   if (!GetByte(&var.bytes[3])) return false;

   return var.dword;
}

static uint8_t GetString (char *dest)
{
   uint8_t ch;

   for (;;) {
      if (!GetByte(&ch)) return false;
      *dest++ = ch;
      if (!ch) break;
   }

   return true;
}

static inline void WriteByte (uint8_t byte)
{
   Uart3Write(byte);
}

static inline void WriteWord (uint16_t word)
{
   union { uint16_t word; uint8_t bytes[2]; } var = {.word = word};

   WriteByte(var.bytes[0]);
   WriteByte(var.bytes[1]);
}

static inline void WriteDWord (uint32_t dword)
{
   union { uint32_t dword; uint8_t bytes[4]; } var = {.dword = dword};

   WriteByte(var.bytes[0]);
   WriteByte(var.bytes[1]);
   WriteByte(var.bytes[2]);
   WriteByte(var.bytes[3]);
}

static void USED WriteString (const char *str)
{
   // Write all characters, followed by a NULL terminator.
   while (*str) WriteByte(*str++);
   WriteByte(0);
}

void InitializeCommands (void)
{
   InitializeUart3(CMD_BAUD_RATE, 8, NO_PARITY, ONE_STOP_BIT);

   // Set up the framebuffer load and save pointers.
   FramebufferBegin = GetFramebuffer();
   FramebufferEnd = (void *)FramebufferBegin + FRAMEBUFFER_SIZE;
}

void CheckForCommand (void)
{
   // Return immediately unless data is available.
   if (!Uart3Available()) return;

   // Find out which command this is.
   CurrentCommand = Uart3Read();

   switch (CurrentCommand) {
      case CMD_SYNC: {
         BEGIN_ARGS();
         if (!GetByte(&ARG_ID)) ARG_ERROR();
         END_ARGS();
         WriteByte(~ARG_ID);
         break;
      } 

      case CMD_GET_CAPABILITIES:
         BEGIN_ARGS();
         if (!GetByte(&ARG_ID)) ARG_ERROR();
         END_ARGS();
         WriteByte(GetCapabilityBits());
         break;

#pragma region DFM Commands
      // GetGaugeReading is #define'd to be (0) when CAP_TANK_GAUGES is not enabled.
      case CMD_GET_GAUGE_READING:
         BEGIN_ARGS();
         if (!GetByte(&ARG_ID)) ARG_ERROR();
         END_ARGS();
         WriteWord(GetGaugeReading(ARG_ID));
         break;

#ifdef CAP_DFM
      case CMD_DFM_TRANSFER:
         BEGIN_ARGS();
         if (!GetByte(&ARG_ID)) ARG_ERROR();
         END_ARGS();
         // This is a two-byte command so it can't happen by accident.
         if (ARG_ID == CMD_DFM_TRANSFER_BYTE_2) {
            DoDfmTransfer();
         }
         break;

#else // CAP_DFM
      case CMD_DFM_TRANSFER:
         BEGIN_ARGS();
         if (!GetByte(&ARG_ID)) ARG_ERROR();
         END_ARGS();
         // This does nothing and returns immediately.
         break;
#endif // CAP_DFM
#pragma endregion

#pragma region Card Reader
#if !defined(CAP_MAGNETIC_CARD) && !defined(CAP_HID_CARD) && !defined(CAP_HID_CARD_2)
      // These commands simulate a magnetic card reader for compatibility, but always report
      // the card as "missing/not inserted".
      case CMD_CARD_DATA:
         // Send 240 empty bytes.
         BEGIN_ARGS();
         END_ARGS();
         for (uint8_t i = 0; i < 240; i++) WriteByte(0);
         break;

      case CMD_CARD_DETECT:
         BEGIN_ARGS();
         END_ARGS();
         WriteByte(0);
         break;

      case CMD_CARD_RESET:
         BEGIN_ARGS();
         END_ARGS();
         break;
#else // If there's a card reader ...
      // There is card reader support. Implement these commands.
      case CMD_CARD_DATA:
         BEGIN_ARGS();
         END_ARGS();
         SendCardData(ByteWriterImpl);
         break;

      case CMD_CARD_DETECT:
         BEGIN_ARGS();
         END_ARGS();
         WriteByte(IsCardDataAvailable() ? 'Y' : 0);
         break;

      case CMD_CARD_RESET:
         BEGIN_ARGS();
         END_ARGS();
         ResetCardReader();
         break;
#endif
#pragma endregion

#pragma region Hardware
      case CMD_GET_ERRORS:
         WriteWord(TotalErrors);
         break;

      case CMD_BEEP:
         Beep();
         break;

      case CMD_CLEAR_PULSES:
         BEGIN_ARGS();
         if (!GetByte(&ARG_ID)) ARG_ERROR();
         END_ARGS();
         ClearCounter(ARG_ID);
         break;

      case CMD_GET_ALARM:
         BEGIN_ARGS();
         if (!GetByte(&ARG_ID)) ARG_ERROR();
         END_ARGS();
         WriteByte(GetAlarmOutput(ARG_ID));
         break;

      case CMD_GET_DEBOUNCE:
         BEGIN_ARGS();
         if (!GetByte(&ARG_ID)) ARG_ERROR();
         END_ARGS();
         WriteByte(GetCounterDebounce(ARG_ID));
         break;

      case CMD_GET_OUTPUT:
         BEGIN_ARGS();
         if (!GetByte(&ARG_ID)) ARG_ERROR();
         END_ARGS();
         WriteByte(GetOutput(ARG_ID));
         break;

      case CMD_GET_SENSOR:
         BEGIN_ARGS();
         if (!GetByte(&ARG_ID)) ARG_ERROR();
         END_ARGS();
         WriteByte(GetSensorState(ARG_ID));
         break;

      case CMD_PLAY_SOUND:
         BEGIN_ARGS();
         if (!GetWord(&ARG_FREQ)) ARG_ERROR();
         if (!GetWord(&ARG_DURATION)) ARG_ERROR();
         END_ARGS();
         Play(ARG_FREQ, ARG_DURATION);
         break;

      case CMD_READ_CLOCK:
         break;

      case CMD_READ_HANDLE:
         BEGIN_ARGS();
         if (!GetByte(&ARG_ID)) ARG_ERROR();
         END_ARGS();
         WriteByte(GetHandleState(ARG_ID));
         break;

      case CMD_READ_KEY:
         WriteByte(GetKey());
         break;

      case CMD_READ_PULSES:
         BEGIN_ARGS();
         if (!GetByte(&ARG_ID)) ARG_ERROR();
         END_ARGS();
         WriteDWord(GetCounter(ARG_ID));
         break;

      case CMD_READ_TICKS:
         break;

      case CMD_SET_ALARM:
         BEGIN_ARGS();
         if (!GetByte(&ARG_ID)) ARG_ERROR();
         if (!GetByte(&ARG_STATE)) ARG_ERROR();
         END_ARGS();
         SetAlarmOutput(ARG_ID, ARG_STATE);
         break;

      case CMD_SET_DEBOUNCE:
         BEGIN_ARGS();
         if (!GetByte(&ARG_ID)) ARG_ERROR();
         if (!GetByte(&ARG_Y)) ARG_ERROR();
         END_ARGS();
         SetCounterDebounce(ARG_ID, ARG_Y);
         break;

      case CMD_SET_LEDS:
         // No longer supported since we don't have keypad LEDs any more.
         // Simply do nothing, but pretend like we did something.
         BEGIN_ARGS();
         if (!GetByte(&ARG_X)) ARG_ERROR();
         if (!GetByte(&ARG_Y)) ARG_ERROR();
         END_ARGS();
         break;

      case CMD_SET_OUTPUT:
         BEGIN_ARGS();
         if (!GetByte(&ARG_ID)) ARG_ERROR();
         if (!GetByte(&ARG_STATE)) ARG_ERROR();
         END_ARGS();
         SetOutput(ARG_ID, ARG_STATE);
         break;

      case CMD_SILENCE:
         break;
#pragma endregion

#pragma region Graphics
      case CMD_GFX_CENTERTEXT:
         BEGIN_ARGS();
         if (!GetByte(&ARG_Y)) ARG_ERROR();
         if (!GetString(ARG_STRING)) ARG_ERROR();
         ARG_W = MeasureString(ARG_STRING);
         END_ARGS();
         DrawString(DISPLAY_WIDTH / 2 - ARG_W / 2, ARG_Y, ARG_STRING);
         break;

      case CMD_GFX_CLEAR:
         BEGIN_ARGS();
         END_ARGS();
         Clear();
         break;

      case CMD_GFX_CLEARROW:
         BEGIN_ARGS();
         if (!GetByte(&ARG_Y)) ARG_ERROR();
         END_ARGS();
         ClearRow(ARG_Y);
         break;

      case CMD_GFX_CLEARROWSEG:
         BEGIN_ARGS();
         if (!GetByte(&ARG_Y)) ARG_ERROR();
         if (!GetByte(&ARG_X)) ARG_ERROR();
         if (!GetByte(&ARG_X2)) ARG_ERROR();
         END_ARGS();
         ClearRowSegment(ARG_Y, ARG_X, ARG_X2);
         break;

      case CMD_GFX_DOTTEDHLINE:
         BEGIN_ARGS();
         if (!GetByte(&ARG_X)) ARG_ERROR();
         if (!GetByte(&ARG_X2)) ARG_ERROR();
         if (!GetByte(&ARG_Y)) ARG_ERROR();
         if (!GetByte(&ARG_COLOR)) ARG_ERROR();
         END_ARGS();
         HDottedLine(ARG_X, ARG_X2, ARG_Y, ARG_COLOR);
         break;

      case CMD_GFX_DOTTEDVLINE:
         BEGIN_ARGS();
         if (!GetByte(&ARG_X)) ARG_ERROR();
         if (!GetByte(&ARG_Y)) ARG_ERROR();
         if (!GetByte(&ARG_Y2)) ARG_ERROR();
         if (!GetByte(&ARG_COLOR)) ARG_ERROR();
         END_ARGS();
         VDottedLine(ARG_X, ARG_Y, ARG_Y2, ARG_COLOR);
         break;

      case CMD_GFX_DRAWBITMAP:
         BEGIN_ARGS();
         if (!GetByte(&ARG_X)) ARG_ERROR();
         if (!GetByte(&ARG_Y)) ARG_ERROR();
         if (!GetByte(&ARG_W)) ARG_ERROR();
         if (!GetByte(&ARG_H)) ARG_ERROR();
         BitmapPointer = BitmapBuffer;
         BitmapBufferEnd = BitmapBuffer + (ARG_W * ARG_H);
         LOG("Expecting %d bytes for bitmap data (%d x %d).", ARG_W * ARG_H, ARG_W, ARG_H);
         Timer = Now();
         while (BitmapPointer != BitmapBufferEnd) {
            if (Now() - Timer > GFX_LOADSERIAL_TIMEOUT) {
               LOG("Did not receive all bitmap bytes! Only %d so far.", (intptr_t)(BitmapPointer - BitmapBuffer));
               ARG_ERROR();
            }

            if (Uart3Available()) {
               *BitmapPointer++ = Uart3Read();
            }
         }
         END_ARGS();
         LOG("Got %d bytes for bitmap data in %lu milliseconds.", ARG_W * ARG_H, (Now() - Timer));
         BitmapStruct.Width = ARG_W;
         BitmapStruct.Height = ARG_H;
         BitmapStruct.Data = BitmapBuffer;
         DrawBitmapFromRAM(ARG_X, ARG_Y, &BitmapStruct);
         break;

      case CMD_GFX_DRAWTEXT:
         BEGIN_ARGS();
         if (!GetByte(&ARG_X)) ARG_ERROR();
         if (!GetByte(&ARG_Y)) ARG_ERROR();
         if (!GetString(ARG_STRING)) ARG_ERROR();
         END_ARGS();
         LOG("Got string: %s", ARG_STRING);
         DrawString(ARG_X, ARG_Y, ARG_STRING);
         break;

      case CMD_GFX_FILLRECT:
         BEGIN_ARGS();
         if (!GetByte(&ARG_X)) ARG_ERROR();
         if (!GetByte(&ARG_Y)) ARG_ERROR();
         if (!GetByte(&ARG_X2)) ARG_ERROR();
         if (!GetByte(&ARG_Y2)) ARG_ERROR();
         if (!GetByte(&ARG_COLOR)) ARG_ERROR();
         END_ARGS();
         FilledRect(ARG_X, ARG_Y, ARG_X2, ARG_Y2, ARG_COLOR);
         break;

      case CMD_GFX_HLINE:
         BEGIN_ARGS();
         if (!GetByte(&ARG_X)) ARG_ERROR();
         if (!GetByte(&ARG_X2)) ARG_ERROR();
         if (!GetByte(&ARG_Y)) ARG_ERROR();
         if (!GetByte(&ARG_COLOR)) ARG_ERROR();
         END_ARGS();
         HLine(ARG_X, ARG_X2, ARG_Y, ARG_COLOR);
         break;

      case CMD_GFX_INVRECT:
         BEGIN_ARGS();
         if (!GetByte(&ARG_X)) ARG_ERROR();
         if (!GetByte(&ARG_Y)) ARG_ERROR();
         if (!GetByte(&ARG_X2)) ARG_ERROR();
         if (!GetByte(&ARG_Y2)) ARG_ERROR();
         END_ARGS();
         InvertRect(ARG_X, ARG_Y, ARG_X2, ARG_Y2);
         break;

      case CMD_GFX_INVROW:
         BEGIN_ARGS();
         if (!GetByte(&ARG_Y)) ARG_ERROR();
         END_ARGS();
         InvertRow(ARG_Y);
         break;

      case CMD_GFX_INVROWSEG:
         BEGIN_ARGS();
         if (!GetByte(&ARG_Y)) ARG_ERROR();
         if (!GetByte(&ARG_X)) ARG_ERROR();
         if (!GetByte(&ARG_X2)) ARG_ERROR();
         END_ARGS();
         InvertRowSegment(ARG_Y, ARG_X, ARG_X2);
         break;

      case CMD_GFX_LINE:
         break;

      case CMD_GFX_LOAD:
         break;

      case CMD_GFX_LOADSERIAL:
         // This receives the entire display via the serial link (see CMD_GFX_SAVESERIAL)
         BEGIN_ARGS();
         END_ARGS();

         Timer = Now();

         FramebufferBegin = GetFramebuffer();
         while (FramebufferBegin != FramebufferEnd) {
            if (Now() - Timer > GFX_LOADSERIAL_TIMEOUT) {
               // This has taken a long time. From here, clear the rest of the framebuffer
               // and exit.
               while (FramebufferBegin != FramebufferEnd) *FramebufferBegin++ = 0;
               break;
            }

            if (Uart3Available()) {
               *FramebufferBegin++ = Uart3Read();
            }
         }
         break;

      case CMD_GFX_RECT:
         BEGIN_ARGS();
         if (!GetByte(&ARG_X)) ARG_ERROR();
         if (!GetByte(&ARG_Y)) ARG_ERROR();
         if (!GetByte(&ARG_X2)) ARG_ERROR();
         if (!GetByte(&ARG_Y2)) ARG_ERROR();
         if (!GetByte(&ARG_COLOR)) ARG_ERROR();
         END_ARGS();
         Rectangle(ARG_X, ARG_Y, ARG_X2, ARG_Y2, ARG_COLOR);
         break;

      case CMD_GFX_REFRESH:
         BEGIN_ARGS();
         END_ARGS();
         Refresh();
         break;

      case CMD_GFX_RIGHTTEXT:
         break;

      case CMD_GFX_SAVE:
         break;

      case CMD_GFX_SAVESERIAL:
         // This transmits the entire display via the serial link.
         BEGIN_ARGS();
         END_ARGS();

         FramebufferBegin = (void *)GetFramebuffer();
         while (FramebufferBegin != FramebufferEnd) {
            WriteByte(*FramebufferBegin++);
         }

         break;

      case CMD_GFX_SETBRIGHT:
         BEGIN_ARGS();
         if (!GetByte(&ARG_ID)) ARG_ERROR();
         END_ARGS();
         SetBrightness(((int)(ARG_ID) * 15) / 100);
         break;

      case CMD_GFX_SETBRIGHTEX:
         BEGIN_ARGS();
         if (!GetByte(&ARG_ID)) ARG_ERROR();
         END_ARGS();
         SetBrightness(ARG_ID);
         break;

      case CMD_GFX_SETPIXEL:
         break;

      case CMD_GFX_SIZETEXT:
         BEGIN_ARGS();
         if (!GetString(ARG_STRING)) ARG_ERROR();
         END_ARGS();
         WriteWord(MeasureString(ARG_STRING));
         break;

      case CMD_GFX_VLINE:
         BEGIN_ARGS();
         if (!GetByte(&ARG_X)) ARG_ERROR();
         if (!GetByte(&ARG_Y)) ARG_ERROR();
         if (!GetByte(&ARG_Y2)) ARG_ERROR();
         if (!GetByte(&ARG_COLOR)) ARG_ERROR();
         END_ARGS();
         VLine(ARG_X, ARG_Y, ARG_Y2, ARG_COLOR);
         break;

#pragma endregion Graphics

#pragma region NVRAM
      case CMD_NVRAM_READ:
         break;

      case CMD_NVRAM_WRITE:
         break;
#pragma endregion

      default:
         ARG_ERROR();
         break;
   }

   // The command handler exited successfully.
   return;

   // This is used when a command handler did not exit successfully.
   // We can rescue the state of the system in a few instances.
   // Also, totalize each error. The error count can be queried.
ErrorHandler:
   END_ARGS();
   LOG("Invalid arguments for command %X.", CurrentCommand);
   TotalErrors++;
   return;   
}
