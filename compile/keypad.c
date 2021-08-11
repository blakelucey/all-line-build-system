/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

*/

#include "common.h"
#include "keypad.h"
#include "speaker.h"
#include "time.h"

#define ROWS      4
#define COLS      4

#define KP_DDR    DDRH
#define KP_PORT   PORTH
#define KP_PIN    PINH

// The fourth keypad column is manually driven for speed
#define KPC4_DDR  DDRB
#define KPC4_PORT PORTB
#define KPC4_PIN  PINB

#define LED_DDR   DDRB
#define LED_PORT  PORTB
#define LED_BIT(n) (1 << (4 + (n)))

#define FIRST_REPEAT_TIME  400
#define NEXT_REPEAT_TIME   125

static const KEYCODE KeyChars[ROWS][COLS] = {
   {'1', '2', '3', 'P'},
   {'4', '5', '6', 'T'},
   {'7', '8', '9', 'D'},
   {'N', '0', 'Y', 'H'}
};

static const uint8_t Rows[] = {1 << 1, 1 << 6, 1 << 5, 1 << 3};
static const uint8_t Cols[] = {1 << 2, 1 << 0, 1 << 4, 1 << 4};
static KEYCODE Current = 0;
static uint32_t CurrentPressTime = 0;
static uint8_t RepeatCount = 0;

// Initialize the keypad rows and columns
void InitializeKeypad (void)
{
   for (uint8_t c = 0; c < COLS; c++) {
      KP_DDR |= Cols[c];
      KP_PORT &= ~Cols[c];
   }

   for (uint8_t r = 0; r < ROWS; r++) {
      KP_DDR &= ~Rows[r];
      KP_PORT |= Rows[r];
   }

   KPC4_DDR |= Cols[4];
   KPC4_PORT |= Cols[4];
   
   // Keypad LEDs are no longer used
   LED_DDR |= 0xF0;
   LED_PORT &= ~0xF0;
} 

static KEYCODE ScanKeys (void)
{
   KEYCODE cur = 0;
   uint8_t any = false;

   for (uint8_t c = 0; c < COLS; c++) {
      if (c == COLS - 1) {
         KPC4_PORT |= Cols[c];
      }
      else {
         KP_PORT &= ~Cols[c];
      }

      for (uint8_t r = 0; r < ROWS; r++) {
         cur = (KP_PIN & Rows[r]);
         if (!cur) {
            // If it's a new key, set its just-pushed time
            if (Current != KeyChars[r][c]) {
               RepeatCount = 0;
               CurrentPressTime = Now();
            }
            Current = KeyChars[r][c];
            any = true;
         }
      }

      if (c == COLS - 1) {
         KPC4_PORT &= ~Cols[c];
      }
      else {
         KP_PORT |= Cols[c];
      }
   }

   if (!any) {
      Current = 0;
      CurrentPressTime = 0;
   }

   return any;
}

KEYCODE GetKey (void)
{
   static uint32_t limiter = 0;
   static KEYCODE last = 0;
   uint8_t found = false;

   if (Now() - limiter > 25) {
      found = ScanKeys();
      limiter = Now();
   }

   if (last != Current) {
      last = Current;
      if (found) {
         Beep();
      }

      return Current;
   }
   else {
      if (Current) {
         if (Now() - CurrentPressTime > (RepeatCount ? NEXT_REPEAT_TIME : FIRST_REPEAT_TIME)) {
            RepeatCount++;
            last = Current;
            CurrentPressTime = Now();
            Click();
            return Current;
         }
      }
   }

   last = Current;
   return 0;
}
