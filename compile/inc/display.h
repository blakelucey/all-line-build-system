/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

   Noritake 800B Vacuum Fluorescent Display Support Header File

*/

#pragma once

#include "common.h"

// Display metrics.
#define DISPLAY_WIDTH      128
#define DISPLAY_HEIGHT     64
#define DISPLAY_LAST_X     (DISPLAY_WIDTH - 1)
#define DISPLAY_LAST_Y     (DISPLAY_HEIGHT - 1)
#define DISPLAY_ROWS       8
#define DISPLAY_LAST_ROW   (DISPLAY_ROWS - 1)

// Font height, in pixels. Must be 8, currently.
#define FONT_HEIGHT        8

// Framebuffer size.
#define FRAMEBUFFER_SIZE   (DISPLAY_WIDTH * DISPLAY_HEIGHT / 8)

// Coordinate type is an unsigned char; so are "colors".
typedef uint8_t COORD;
typedef uint8_t COLOR;

typedef struct BITMAP {
   uint16_t Width, Height;
   const uint8_t *Data;
} BITMAP;

enum {
   BLACK, WHITE
};

// Prototypes.
void InitializeDisplay (void);
volatile uint8_t *GetFramebuffer (void);
void SetBrightness (COORD level);
void Clear (void);
void ClearRow (COORD row);
void ClearRowSegment (COORD row, COORD startx, COORD endx);
void Refresh (void);
void HDottedLine (COORD x, COORD x2, COORD y, COLOR c);
void HLine (COORD x, COORD x2, COORD y, COLOR c);
void VDottedLine (COORD x, COORD y, COORD y2, COLOR c);
void VLine (COORD x, COORD y, COORD y2, COLOR c);
void Rectangle (COORD x, COORD y, COORD x2, COORD y2, COLOR c);
void FilledRect (COORD x, COORD y, COORD x2, COORD y2, COLOR c);
void InvertRect (COORD x, COORD y, COORD x2, COORD y2);
void InvertRow (COORD row);
void InvertRowSegment (COORD row, COORD startx, COORD endx);
void DrawBitmapFromRAM (COORD destx, COORD desty, const BITMAP *bitmap);
void DrawBitmapFromROM (COORD x, COORD y, const uint8_t *bitmap);
void DrawBitmapUsingFunc (COORD x, COORD y, COORD w, COORD h, uint8_t (*)(uint8_t, uint8_t, void *), void *param);
uint16_t DrawString (COORD x, COORD y, const char *string);
uint16_t DrawStringP (COORD x, COORD y, const char *string);
uint16_t DrawStringPF (COORD x, COORD y, const char *fmt, ...);
uint16_t MeasureString (const char *string);
uint16_t MeasureStringP (const char *string);
uint16_t MeasureStringPF (const char *fmt, ...);
