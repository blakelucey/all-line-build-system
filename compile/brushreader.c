/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

   Interfaces with a Brush Card Reader (TTL Type)

   Cannot be used at the same time as the MagTek card reader, since the same
   GPIO pins, interrupts and timers are used. Also can't be used with the
   HID card reader.

*/

#include "common.h"
#include "time.h"
#include "card.h"
#include "speaker.h"
#include "outputs.h"

#if defined(CAP_MAGNETIC_CARD) && defined(MAGCARD_BRUSH)

#define MAG_DDR         DDRK
#define MAG_PORT        PORTK
#define MAG_ALLBITS     ((1 << 0) | (1 << 1) | (1 << 2) | (1 << 3))

#define RESET_TIMEOUT() do { TCNT4 = 1; } while (0)

#define DETECT_SIGNAL   ((PINK & (1 << 3)) == 0)
#define STROBE_SIGNAL   ((PINK & (1 << 1)) == 0)
#define DATA_SIGNAL     ((PINK & (1 << 0)) == 0)

#define DETECT_PCINT    (1 << PCINT19)
#define STROBE_PCINT    (1 << PCINT17)
#define DATA_PCINT      (1 << PCINT16)

#define TRACK_2_SIZE             40
#define TRACK_2_BITS_PER_CHAR    5
#define TRACK_2_TOTAL_BITS       (TRACK_2_SIZE * TRACK_2_BITS_PER_CHAR)

#define ENABLE_PCINTS()          do { PCICR |= (1 << PCIE2); } while (0)
#define DISABLE_PCINTS()         do { PCICR &= ~(1 << PCIE2); } while (0)

#define PCINT_MASK               PCMSK2

// Reset the state machine to get ready for a new read.
#define RESET_STATE() do { \
   MagPointer = 0; \
   MagState = S_DETECT; \
   MagError = false; \
   cli(); \
   TIMSK4 &= ~(1 << OCIE4A); \
   PCICR |= (1 << PCIE2); \
   PCMSK2 = DETECT_PCINT; \
   sei(); \
} while (0)

// Sets the state machine up to expect card removal.
#define ERROR_STATE() do { \
   MagState = S_REMOVAL; \
   MagError = true; \
   cli(); \
   PCINT_MASK = DETECT_PCINT; \
   RESET_TIMEOUT(); \
   TCCR4B = 0; \
   TIMSK4 &= ~(1 << OCIE4A); \
   sei(); \
} while (0)

enum {
   S_DETECT,
   S_READING,
   S_COMPLETE,
   S_REMOVAL
};

static volatile uint8_t MagData[TRACK_2_TOTAL_BITS];
static volatile uint8_t MagPointer = 0;
static volatile uint8_t MagError = false;
static volatile uint8_t MagState = S_DETECT;

ISR(PCINT2_vect)
{
   switch (MagState) {
   case S_COMPLETE:
      // There is a result stored that has not yet been retrieved. Do nothing.
      return;

   case S_DETECT:
      // We are waiting for the card detect pin to go low.
      if (DETECT_SIGNAL) {
         // It happened; get ready to read some data.
         PCINT_MASK = STROBE_PCINT;

         // Use timer 4 to time out independently.
         RESET_TIMEOUT();
         OCR4A = 0x5b8d;
         TCCR4A = 0;
         TCCR4B = (1 << CS42) | (1 << WGM42);
         TIMSK4 |= (1 << OCIE4A);

         MagPointer = 0;
         MagState = S_READING;
      }

      break;

   case S_READING:
      // We are reading data from the card.
      // We clock in bits on the falling edge of the strobe signal.
      if (!STROBE_SIGNAL) {
         MagData[MagPointer++] = DATA_SIGNAL;
         if (MagPointer == TRACK_2_TOTAL_BITS) {
            PCINT_MASK = DETECT_PCINT;
            MagState = S_REMOVAL;
            RESET_TIMEOUT();
         }
      }

      break;

   case S_REMOVAL:
      // Wait for the card detect pin to go high.
      if (!DETECT_SIGNAL) {
         PCINT_MASK = 0;
         MagState = S_COMPLETE;

         // Disable the timer.
         TCCR4B = 0;
         TIMSK4 &= ~(1 << OCIE4A);
      }

      break;
   }
}

ISR(TIMER4_COMPA_vect)
{
   // If this is executing, it's been too long.
   ERROR_STATE();
}

void InitializeCard (void)
{
   // Set up the inputs for the data and strobe connection.
   MAG_DDR &= ~MAG_ALLBITS;
   MAG_PORT &= ~MAG_ALLBITS;

   cli();
   PCMSK2 = 0;

   // Configure timer 4.
   TCCR4A = 0;
   TCCR4B = 0;
   sei();

   ResetCardReader();
}

uint8_t IsCardDataAvailable (void)
{
   return MagState == S_COMPLETE;
}

uint8_t IsCardError (void)
{
   return MagError;
}

void CopyCardDataAsText (char *dest)
{
   uint8_t ch;

   // Set the destination to hold a zero-length string, first.
   *dest = 0;

   cli();

   // First, find the start sentinel. Look through the data a single bit at
   // a time, and then start copying from there.
   uint8_t ss = 0;
   uint8_t len = MagPointer;
   uint8_t i = 0;

   for (; i < len; i++) {
      // Does this contain the start sentinel? Before the start sentinel,
      // there should be nothing but zeroes. Check that the pattern is
      // 00 01011.
      ss = (ss << 1) | MagData[i];

      if ((ss & 0x7f) == 0b0011010) {
         // Return to the beginning of the character.
         i -= 4;
         break;
      }
   }
   if (i >= len) goto return_value;

   // Now grab the 5-bit characters, one at a time.
   for (; i < len; i+= 5) {
      ch = 
         ((MagData[i + 4]) << 4) |
         ((MagData[i + 3]) << 3) |
         ((MagData[i + 2]) << 2) |
         ((MagData[i + 1]) << 1) |
         ((MagData[i + 0]) << 0);

      *dest++ = (char)((ch & 0xf) + '0');
   }
   *dest = 0;

return_value:
   sei();
}

void SendCardData (BYTE_WRITER writer)
{
   // This sents the raw card data, and does no processing at all.
   // The receiver should do all of the work to reconstruct the data.
   uint8_t len = MagPointer;

   for (uint8_t i = 0; i < len; i++) {
      writer(MagData[i]);
   }

   // The ARM side expects 240 bytes, and not 200. Sent some padding.
   // It also wants a final 0xFF byte after the real data, so do that first.
   writer(0xFF);
   for (uint8_t i = 0; i < 240 - 1 - len; i++) {
      writer(0);
   }
}

void ResetCardReader (void)
{
   RESET_STATE();
}

#endif // CAP_MAGNETIC_CARD && MAGCARD_BRUSH
