/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

   Noritake 800B Vacuum Fluorescent Display Support

*/

#include "common.h"
#include "display.h"
#include "font.h"

#include <stdio.h>

// Direction, port, and bit definitions.
#define WR_DIR    DDRK
#define CD_DIR    DDRK
#define RD_DIR    DDRK
#define CS_DIR    DDRK
#define WR_PORT   PORTK
#define CD_PORT   PORTK
#define RD_PORT   PORTK
#define CS_PORT   PORTK
#define WR_BIT    (1 << 7)
#define CD_BIT    (1 << 6)
#define RD_BIT    (1 << 5)
#define CS_BIT    (1 << 4)
#define DATA_DIR  DDRA
#define DATA_PORT PORTA

#define DATA()    do { \
   CD_PORT &= ~CD_BIT; \
} while (0)

#define COMMAND() do { \
   CD_PORT |= CD_BIT; \
} while (0)

#define WRITE_DATA(n) do { \
   WR_PORT &= ~WR_BIT; \
   DATA_PORT = n; \
   WR_PORT |= WR_BIT; \
} while (0)

#define WRITE_COMMAND(n) do { \
   WR_PORT &= ~WR_BIT; \
   DATA_PORT = n; \
   WR_PORT |= WR_BIT; \
} while (0)

// Masked clamping.
#define CLAMP_X(n)   do { (n) &= 0x7f; } while (0)
#define CLAMP_Y(n)   do { (n) &= 0x3f; } while (0)

// Display operations.
enum {
   DISPLAY_OFF       = 0x00,
   DISPLAY_OR        = 0x00,
   DISPLAY_ON        = 0x40,
   DISPLAY_REVERSE   = 0x10,
   DISPLAY_AND       = 0x08,
   DISPLAY_XOR       = 0x04
};

enum {
   DISPLAY_LAYER_0   = 0x04,
   DISPLAY_LAYER_1   = 0x08
};

enum {
   DISPLAY_NO_INCR   = 0x00,
   DISPLAY_INCR_X    = 0x04,
   DISPLAY_INCR_Y    = 0x08
};

// Font and bitmap structures and definitions.
typedef struct FONT {
   const uint8_t *Widths;
   const uint16_t *Offsets;
   const uint8_t *Data;
} FONT;

typedef struct PRINT_INFO {
   uint16_t Width;
   COORD Y;
   COORD TopRow, BottomRow;
   COORD TopShift, BottomShift;
} PRINT_INFO;

PRINT_INFO Print;

const FONT Font = {
   FontWidths, FontOffsets, FontData
};

// Framebuffer memory.
static volatile uint8_t Framebuffer[DISPLAY_WIDTH][DISPLAY_ROWS];
#define FRAMEBUFFER(fx, fy) *((volatile uint8_t *)Framebuffer + ((fy) << 7) + (fx))

// Single-pixel framebuffer access macros.
#define SET_PIXEL(px, py, pc) do { \
   if (pc) { \
      FRAMEBUFFER((px), (py) >> 3) |= (1 << ((py) & 0x07)); \
   } \
   else { \
      FRAMEBUFFER((px), (py) >> 3) &= ~(1 << ((py) & 0x07)); \
   } \
} while (0)

#define INV_PIXEL(px, py) do { \
   FRAMEBUFFER((px), (py) >> 3) ^= (1 << ((py) & 0x07)); \
} while (0)

#define WHITE_PIXEL(px, py) do { \
   FRAMEBUFFER((px), (py) >> 3) |= (1 << ((py) & 0x07)); \
} while (0)

#define BLACK_PIXEL(px, py) do { \
   FRAMEBUFFER((px), (py) >> 3) &= ~(1 << ((py) & 0x07)); \
} while (0)

void SetBrightness (uint8_t level)
{
   COMMAND();
   WRITE_COMMAND(0x40 | (0x0f - (level & 0x0f)));
}

void SetLayers (uint8_t layers, uint8_t mode)
{
   layers = (layers & (DISPLAY_LAYER_0 | DISPLAY_LAYER_1));
   COMMAND();
   WRITE_COMMAND(0x20 | layers);
   WRITE_COMMAND(mode);
}

void SetAddress (uint8_t x, uint8_t row)
{
   COMMAND();
   WRITE_COMMAND(0x64);
   WRITE_COMMAND(x);
   WRITE_COMMAND(0x60);
   WRITE_COMMAND(row);
}

void SetAddressMode (uint8_t amode)
{
   amode = (amode & (DISPLAY_INCR_X | DISPLAY_INCR_Y));
   COMMAND();
   WRITE_COMMAND(0x80 | amode);
}

void InitializeDisplay (void)
{
   // Set up the IO ports.
   WR_DIR |= WR_BIT;
   CD_DIR |= CD_BIT;
   RD_DIR |= RD_BIT;
   CS_DIR |= CS_BIT;
   DATA_DIR = 0xff;

   // We will never read from the display.
   CD_PORT &= ~CD_BIT;
   RD_PORT |= RD_BIT;

   // Clear everything and reset the display.
   COMMAND();
   WRITE_COMMAND(0x5f);
   _delay_ms(25.0);

   // We need to initialize the display's RAM as graphics RAM/GRAM, and not as DDRAM
   // since the 800B displays have no character generator.
   for (uint8_t n = 0; n < 8; n++) {
      COMMAND();
      WRITE_COMMAND(0x62);
      WRITE_COMMAND(n);
      DATA();
      WRITE_DATA(0xff);
   }

   // Layer 0 ANDed with layer 1, regular display, cursor in the upper left.
   SetLayers(DISPLAY_LAYER_0, DISPLAY_ON);
   SetAddress(0, 0);
   SetAddressMode(DISPLAY_INCR_X);

   // Clear and get ready.
   Clear();
   Refresh();
}

// Draw a horizontal dotted line.
void HDottedLine (COORD x, COORD x2, COORD y, COLOR c)
{
   for (COORD dx = x; dx <= x2; dx += 2) {
      SET_PIXEL(dx, y, c);
   }
}

// Draw a horizontal solid line.
void HLine (COORD x, COORD x2, COORD y, COLOR c)
{
   for (COORD dx = x; dx <= x2; dx++) {
      SET_PIXEL(dx, y, c);
   }
}

// Draw a vertical dotted line.
void VDottedLine (COORD x, COORD y, COORD y2, COLOR c)
{
   for (COORD dy = y; dy <= y2; dy += 2) {
      SET_PIXEL(x, dy, c);
   }
}

// Draw a vertical solid line.
void VLine (COORD x, COORD y, COORD y2, COLOR c)
{
   for (COORD dy = y; dy <= y2; dy++) {
      SET_PIXEL(x, dy, c);
   }
}

// Draw a frame/rectangle.
void Rectangle (COORD x, COORD y, COORD x2, COORD y2, COLOR c)
{
   SET_PIXEL(x, y, c);
   SET_PIXEL(x, y2, c);
   SET_PIXEL(x2, y, c);
   SET_PIXEL(x2, y2, c);

   for (COORD dx = x + 1; dx < x2; dx++) {
      SET_PIXEL(dx, y, c);
      SET_PIXEL(dx, y2, c);
   }

   for (COORD dy = y + 1; dy < y2; dy++) {
      SET_PIXEL(x, dy, c);
      SET_PIXEL(x2, dy, c);
   }
}

// Fill a frame/rectangle.
void FilledRect (COORD x, COORD y, COORD x2, COORD y2, COLOR c)
{
   CLAMP_X(x);
   CLAMP_Y(y);
   CLAMP_X(x2);
   CLAMP_Y(y2);

   // Preselect which function we're going to use.
   if (c) {
      for (COORD dy = y; dy <= y2; dy++) {
         for (COORD dx = x; dx <= x2; dx++) {
            WHITE_PIXEL(dx, dy);
         }
      }
   }
   else {
      for (COORD dy = y; dy <= y2; dy++) {
         for (COORD dx = x; dx <= x2; dx++) {
            BLACK_PIXEL(dx, dy);
         }
      }
   }
}

// Invert a frame/rectangle.
void InvertRect (COORD x, COORD y, COORD x2, COORD y2)
{
   for (COORD dy = y; dy <= y2; dy++) {
      for (COORD dx = x; dx <= x2; dx++) {
         INV_PIXEL(dx, dy);
      }
   }
}

// Invert a whole row.
void InvertRow (COORD row)
{
   for (COORD x = 0; x < DISPLAY_WIDTH; x++) {
      FRAMEBUFFER(x, row) = ~FRAMEBUFFER(x, row);
   }
}

// Clear a whole row.
void ClearRow (COORD row)
{
   for (COORD x = 0; x < DISPLAY_WIDTH; x++) {
      FRAMEBUFFER(x, row) = 0;
   }
}

// Clear a bit of a row.
void ClearRowSegment (COORD row, COORD startx, COORD endx)
{
   for (COORD x = startx; x <= endx; x++) {
      FRAMEBUFFER(x, row) = 0;
   }
}

// Invert a bit of a row.
void InvertRowSegment (COORD row, COORD startx, COORD endx)
{
   for (COORD x = startx; x <= endx; x++) {
      FRAMEBUFFER(x, row) = ~FRAMEBUFFER(x, row);
   }
}

// Draw a bitmap from a structure.
void DrawBitmapFromRAM (COORD destx, COORD desty, const BITMAP *bitmap)
{
   uint8_t w = bitmap->Width;
   uint8_t h = bitmap->Height;
   uint16_t index = 0;

   for (COORD col = 0; col < w; col++) {
      for (COORD row = 0; row < h; row++) {
         FRAMEBUFFER(destx + col, desty + row) = bitmap->Data[index++];
      }
   }
}

// Draw a bitmap directly from ROM.
void DrawBitmapFromROM (COORD x, COORD y, const uint8_t *ptr)
{
   const uint8_t *bitmap = (const uint8_t *)ptr;
   uint8_t w = pgm_read_byte_far(bitmap);
   uint8_t h = pgm_read_byte_far(bitmap + 1);

   // Skip the width and height
   bitmap += 2;

   // Read in the data
   for (COORD col = 0; col < w; col++) {
      for (COORD row = 0; row < h; row++) {
         FRAMEBUFFER(x + col, y + row) = pgm_read_byte_far(bitmap);
         bitmap++;
      }
   }
}

// Draw a bitmap using a callback function for each byte.
void DrawBitmapUsingFunc (
   COORD x, COORD y, COORD w, COORD h, 
   uint8_t (*read)(uint8_t, uint8_t, void *), void *param
)
{
   for (COORD col = 0; col < w; col++) {
      for (COORD row = 0; row < h; row++) {
         FRAMEBUFFER(x + col, y + row) = read(col, row, param);
      }
   }
}

// Clear the entire display.
void Clear (void)
{
   memset((void *)Framebuffer, 0, FRAMEBUFFER_SIZE);
}

// This is the display refresh logic.
// The entire display can be uploaded in a millisecond or so by unrolling the upload
// loop manually.
#define UNROLL_8() do { \
   WRITE_DATA(*b++); WRITE_DATA(*b++); WRITE_DATA(*b++); WRITE_DATA(*b++); \
   WRITE_DATA(*b++); WRITE_DATA(*b++); WRITE_DATA(*b++); WRITE_DATA(*b++); \
} while (0)

#define UNROLL_64() do { \
   UNROLL_8(); UNROLL_8(); UNROLL_8(); UNROLL_8(); \
   UNROLL_8(); UNROLL_8(); UNROLL_8(); UNROLL_8(); \
} while (0)

#define UNROLL_ROW(r) do { \
   SetAddress(0, (r)); \
   DATA(); \
   UNROLL_64(); \
   UNROLL_64(); \
} while (0)

void Refresh (void)
{
   const uint8_t *b = (const uint8_t *)Framebuffer;
   UNROLL_ROW(0);
   UNROLL_ROW(1);
   UNROLL_ROW(2);
   UNROLL_ROW(3);
   UNROLL_ROW(4);
   UNROLL_ROW(5);
   UNROLL_ROW(6);
   UNROLL_ROW(7);
}

volatile uint8_t *GetFramebuffer (void)
{
   return (uint8_t *)Framebuffer;
}

uint16_t MeasureString (const char *string)
{
   Print.Width = 0;
   while (*string) {
      Print.Width += pgm_read_byte_far(&(Font.Widths[*string - ' ']));
      string++;
   }
   return Print.Width;
}

uint16_t MeasureStringP (const char *string)
{
   char ch;
   Print.Width = 0;
   while ((ch = pgm_read_byte_far(string))) {
      Print.Width += pgm_read_byte_far(&(Font.Widths[ch - ' ']));
   }
   return Print.Width;
}

uint16_t MeasureStringPF (const char *fmt, ...)
{
   // These formatted strings are only used by the diagnostics system.
   va_list args;
   va_start(args, fmt);
   char buffer[MAX_STRING_SIZE];
   vsnprintf_P(buffer, MAX_STRING_LEN, fmt, args);
   buffer[MAX_STRING_LEN] = 0;
   va_end(args);

   return MeasureString(buffer);
}

// Draw a single character, all on one row.
#pragma region Raw Character Drawing
static inline uint8_t DrawChar (COORD x, uint8_t c)
{
   uint8_t code = c - ' ';
   uint8_t width = pgm_read_byte_far(&(Font.Widths[code]));
   uint16_t offset = pgm_read_word_far(&(Font.Offsets[code]));

   if (x + width > DISPLAY_LAST_X) return 0;

   for (uint8_t cx = 0; cx < width; cx++) {
      // Increase the X position
      FRAMEBUFFER(x++, Print.TopRow) = pgm_read_byte_far(&(Font.Data[offset + cx]));
   }

   return width;
}

// Draw a single character, split across two rows.
static inline uint8_t DrawSplitChar (COORD x, uint8_t c)
{
   uint8_t code = c - ' ';
   uint8_t width = pgm_read_byte_far(&(Font.Widths[code]));
   uint16_t offset = pgm_read_word_far(&(Font.Offsets[code]));

   if (x + width > DISPLAY_LAST_X) return 0;

   // Is either row off-screen?
   if (Print.TopRow >= DISPLAY_ROWS) {
      // Draw only the bottom row.
      for (uint8_t cx = 0; cx < width; cx++) {
         FRAMEBUFFER(x++, Print.BottomRow) =
            pgm_read_byte_far(&(Font.Data[offset + cx])) >> Print.BottomShift;
      }
   }
   else if (Print.BottomRow >= DISPLAY_ROWS) {
      // Draw only the top row.
      for (uint8_t cx = 0; cx < width; cx++) {
         FRAMEBUFFER(x++, Print.TopRow) =
            pgm_read_byte_far(&(Font.Data[offset + cx])) << Print.TopShift;
      }
   }
   else {
      // Both rows are visible on-screen.
      for (uint8_t cx = 0; cx < width; cx++) {
         // Do NOT increase the X position
         FRAMEBUFFER(x, Print.TopRow) = 
            pgm_read_byte_far(&(Font.Data[offset + cx])) << Print.TopShift;

         // Increase the X position
         FRAMEBUFFER(x++, Print.BottomRow) =
            pgm_read_byte_far(&(Font.Data[offset + cx])) >> Print.BottomShift;
      }
   }

   return width;
} 

// Figure out the character split metrics.
static inline void ComputeCharSplit (void)
{
   Print.TopRow = Print.Y >> 3;
   Print.BottomRow = (Print.Y + FONT_HEIGHT - 1) >> 3;

   if (Print.TopRow != Print.BottomRow) {
      // This print spans two rows.
      Print.TopShift = Print.Y & 0x07;
      Print.BottomShift = (FONT_HEIGHT - ((Print.Y - FONT_HEIGHT) & 0x07));
   }
}
#pragma endregion

// Draw a string.
uint16_t DrawString (COORD x, COORD y, const char *string)
{
   uint16_t charwidth;
   Print.Width = 0;
   Print.Y = y;

   // Is it entirely off-screen? Don't print anything.
   if (y > DISPLAY_LAST_Y) return 0;
   if (x > DISPLAY_LAST_X) return 0;

   ComputeCharSplit();

   if (Print.TopRow == Print.BottomRow) {
      // Everything is on a single row.
      while (*string) {
         charwidth = DrawChar(x, *string++);
         Print.Width += charwidth;
         x += charwidth;
      }
   }
   else {
      // The characters will span two rows.
      while (*string) {
         charwidth = DrawSplitChar(x, *string++);
         Print.Width += charwidth;
         x += charwidth;
      }
   }

   return Print.Width;
}

// Draw a string in ROM.
uint16_t DrawStringP (COORD x, COORD y, const char *string)
{
   uint16_t charwidth;
   Print.Width = 0;
   Print.Y = y;

   // Is it entirely off-screen? Don't print anything.
   if (y > DISPLAY_LAST_Y) return 0;
   if (x > DISPLAY_LAST_X) return 0;

   ComputeCharSplit();

   char ch;

   if (Print.TopRow == Print.BottomRow) {
      // Everything is on a single row.
      while ((ch = pgm_read_byte_far(string++))) {
         charwidth = DrawChar(x, ch);
         Print.Width += charwidth;
         x += charwidth;
      }
   }
   else {
      // The characters will span two rows.
      while ((ch = pgm_read_byte_far(string++))) {
         charwidth = DrawSplitChar(x, ch);
         Print.Width += charwidth;
         x += charwidth;
      }
   }

   return Print.Width;
}

// Draw a string in ROM with formatting.
uint16_t DrawStringPF (COORD x, COORD y, const char *fmt, ...)
{
   va_list args;
   va_start(args, fmt);
   char buffer[MAX_STRING_SIZE];
   vsnprintf_P(buffer, MAX_STRING_LEN, fmt, args);
   buffer[MAX_STRING_LEN] = 0;
   va_end(args);

   return DrawString(x, y, buffer);
}
