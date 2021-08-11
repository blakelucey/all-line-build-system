/*

   All-Line Equipment Company
   Fuel Boss DFM/Tank Gauge Interface Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

   Diagnostic Screen

*/

#include "common.h"
#include "dfmadapter.h"
#include "card.h"
#include "display.h"
#include "keypad.h"
#include "inputs.h"
#include "outputs.h"
#include "counters.h"
#include "speaker.h"
#include "time.h"
#include "uart.h"

// This is required for some functions we want to keep, but throw a warning because they
// currently are not used.
#define USED __attribute__((used))

#define MAX_ITEMS 8

typedef struct DIAGNOSTIC_ITEM {
   void (*Proc)(void *param);
   const char *Title;
} DIAGNOSTIC_ITEM;

uint8_t NumItems = 0;
DIAGNOSTIC_ITEM Items[MAX_ITEMS];

static void AddItem (const char *title, void (*proc)(void *param))
{
   Items[NumItems].Proc = proc;
   Items[NumItems].Title = title;
   NumItems++;
}

static void DrawItems (void)
{
   const uint8_t start = 2;

   for (uint8_t i = 0; i < NumItems; i++) {
      DrawStringPF(4, (start + i) * 8, F("%d"), i + 1);
      InvertRowSegment(start + i, 3, 9);
      DrawStringPF(12, (start + i) * 8, Items[i].Title);
   }
}

static void DrawDiagnostics (void)
{
   Clear();
   DrawStringP(0, 0, F("IO BOARD DIAGNOSTICS"));
   DrawItems();
   Refresh();
}

static void DrawHelp (const char *text)
{
   Clear();
   DrawStringP(0, DISPLAY_LAST_ROW * 8, text);
   InvertRow(DISPLAY_LAST_ROW);
}

static void USED RelaysPulsersHandles (void *param)
{
   // Drawing coordinates. x_coords has an extra element for width calculation.
   static const uint8_t x_coords[]  = {0, 16, 32, 48, 64, 80, 96, 112, 128};
   static const uint8_t handle_row  = (DISPLAY_LAST_ROW - 2);
   static const uint8_t relay_row   = (DISPLAY_LAST_ROW - 1);
   static const uint8_t handle_y    = handle_row * 8;
   static const uint8_t relay_y     = relay_row * 8;
   static const uint8_t px_coords[] = {0, 0, 0, 0, 64, 64, 64, 64};
   static const uint8_t py_coords[] = {0, 8, 16, 24, 0, 8, 16, 24};
   static const uint8_t p_rows[]    = {0, 1, 2, 3, 0, 1, 2, 3};

   // Strings.
   char temp[3] = {0, 0, 0};

   uint32_t redraw_time = 0;
   char key;

   // Clear all counters.
   for (uint8_t i = 0; i < NUM_COUNTERS; i++) {
      ClearCounter(i);
   }

   DrawHelp(F("1-8:Relays  0:Reset  NO:Exit"));

   for (;;) {
      key = GetKey();

      if (key >= '1' && key <= '8') {
         SetOutput(key - '1', !GetOutput(key - '1'));
      }
      else if (key == '0') {
         for (uint8_t i = 0; i < NUM_COUNTERS; i++) {
            ClearCounter(i);
         }
         redraw_time = 0;
      }
      else if (key == 'N') {
         break;
      }

      if (Now() - redraw_time > 50) {
         // Clear the handle and relay rows.
         ClearRow(handle_row);
         ClearRow(relay_row);

         // Redraw our handle indicators.
         temp[0] = 'H';
         for (uint8_t i = 0; i < NUM_HANDLES; i++) {
            temp[1] = '1' + i;
            DrawString(x_coords[i] + 2, handle_y, temp);
            if (GetHandleState(i)) {
               InvertRowSegment(handle_row, x_coords[i], x_coords[i + 1] - 1);
            }
         }

         // Redraw our relay indicators.
         temp[0] = 'R';
         for (uint8_t i = 0; i < NUM_OUTPUTS; i++) {
            temp[1] = '1' + i;
            DrawString(x_coords[i] + 2, relay_y, temp);
            if (GetOutput(i)) {
               InvertRowSegment(relay_row, x_coords[i], x_coords[i + 1] - 1);
            }
         }

         // Redraw our counters.
         for (uint8_t i = 0; i < NUM_COUNTERS / 2; i++) {
            ClearRow(p_rows[i]);
         }

         temp[0] = 'P';
         for (uint8_t i = 0; i < NUM_COUNTERS; i++) {
            temp[1] = '1' + i;
            DrawString(px_coords[i], py_coords[i], temp);
            DrawStringPF(px_coords[i] + 12, py_coords[i], F("%lu"), GetCounter(i));
         }

         Refresh();

         redraw_time = Now();
      }
   }

   // Make sure everything is turned off.
   for (uint8_t i = 0; i < NUM_OUTPUTS; i++) {
      SetOutput(i, false);
   }
}

static void USED TankGauges (void *param)
{
   uint32_t timer = 0;

   Clear();

   for (;;) {
      if (GetKey() == 'N') break;

      if (Now() - timer > 100) {
         // Refresh the display.
         Clear();

         for (uint8_t i = 0; i < NUM_GAUGES; i++) {
            DrawStringPF(0, i * 8, F("Gauge %d"), i);
            DrawStringPF(40, i * 8, F("%d"), GetGaugeReading(i));
         }

         Refresh();

         timer = Now();
      }
   }
}

#if defined(CAP_DFM)
static void USED TestDfm (void *param)
{
}

static void USED DebugDfm (void *param)
{
   char k;
   uint32_t then = 0;
   uint32_t recv = 0;
   uint32_t fe = 0, pe = 0, bo = 0;
   uint8_t reg = 0;

   Clear();
   DrawStringP(0, 0, F("DFM Serial Test"));
   Refresh();

   // Tell the DFM board we're ready to be connected directly
   // to the DFM port.
   BeginDfmTransfer();

   for (;;) {
      // Receive?
      if (Uart0Available()) {
         Uart0Read();
         recv++;
      }

      // Something wrong?
      reg = UCSR0A;
      if (reg & (1 << FE0)) fe++;
      if (reg & (1 << DOR0)) bo++;
      if (reg & (1 << UPE0)) pe++;

      // Key?
      k = GetKey();

      if (k == 'N') break;
      if (k == 'Y') {
         recv = fe = bo = pe = 0;
         then = 0;
      }
      
      // Refresh?
      if (Now() - then > 100) {
         ClearRow(3);
         ClearRow(4);
         DrawStringPF(0, 3 * 8, F("%lu bytes"), recv);
         DrawStringPF(0, 4 * 8, F("FE: %lu"), fe);
         DrawStringPF(40, 4 * 8, F("BO: %lu"), bo);
         DrawStringPF(80, 4 * 8, F("PE: %lu"), pe);
         Refresh();

         then = Now();
      }
   }

   // We're done.
   EndDfmTransfer();
}
#endif

#ifdef CAP_MAGNETIC_CARD
void USED MagneticCard (void *param)
{
   char k;
   char buffer[64];
   int num = 0;
   
   Clear();
   DrawStringP(0, 0, F("Magnetic Card Test"));
   DrawStringP(0, 8, F("(Test does not check parity)"));
   DrawStringP(0, 56, F("NO key returns."));
   Refresh();

   // Set up to report the card data serially.
   InitializeUart0(115200, 8, NO_PARITY, ONE_STOP_BIT);

   for (;;) {
      if (IsCardDataAvailable()) {
         Play(2200, 25);

         // Capture and also report the data.
         CopyCardDataAsText(buffer);
         Uart0Write('S');
         SendCardData(Uart0Write);
         Uart0Write('E');

         // Display the data.
         ClearRow(3);
         ClearRow(4);
         ClearRow(5);
         ClearRow(6);

         int x = DrawStringPF(0, 24, F("Data: "));
         int y = 24;
         char temp[2] = {0, 0};
         for (uint8_t i = 0; i < strlen(buffer); i++) {
            // Will another character fit?
            temp[0] = buffer[i];
            if (x + MeasureString(temp) > 127) {
               x = 0;
               y += 8;
            }
            x += DrawString(x, y, temp);
         }

         DrawStringPF(0, 40, F("(%d characters read)"), strlen(buffer));
         DrawStringPF(0, 48, F("Cards read: %d  "), num);
         Refresh();

         // Reset the card reader.
         ResetCardReader();
         num++;
      }
      
      k = GetKey();
      if (k == 'N') break;
      if (k == '0') ResetCardReader();
   }
}
#endif

#if defined(CAP_HID_CARD) || defined(CAP_HID_CARD_2)
static void USED HidCard (void *param)
{
   char k;
   uint8_t beepy = false;

   Clear();
   DrawStringP(0, 0, F("HID Card Test"));
   DrawStringP(0, 56, F("NO key returns. 0 key resets."));
   Refresh();

   for (;;) {
      if (IsCardDataAvailable()) {
         if (!beepy) {
            Beep();
            beepy = true;
            ClearRow(3);
            ClearRow(4);
            DrawStringPF(0, 24, F("Facility: %u"), GetHidFacility());
            DrawStringPF(0, 32, F("Number: %u"), GetHidNumber());
            Refresh();
         }
      }

      k = GetKey();
      if (k == 'N') break;
      if (k == '0') {
         beepy = false;
         ClearRow(3);
         ClearRow(4);
         Refresh();
         ResetCardReader();
      }
   }
}

static void USED HidCard2 (void *param)
{
}
#endif

void CheckForDiagnostics (void)
{
   // If the NO key is pushed immediately after startup, we'll enter an IO controller
   // diagnostics screen.
   char key = 0;

   for (uint32_t t = Now(); Now() - t < 500;) {
      if ((key = GetKey()) == 'N') break;
   }

   if (!key) return;

   // Set up the appropriate items.
   AddItem(F("Relays, Pulsers, Handles"), RelaysPulsersHandles);

#ifdef CAP_TANK_GAUGES
   AddItem(F("Tank Gauges"), TankGauges);
#endif

#ifdef CAP_DFM
   //AddItem(F("DFM Test"), TestDfm);
   AddItem(F("DFM Debug"), DebugDfm);
#endif

#ifdef CAP_MAGNETIC_CARD
   AddItem(F("Magnetic Card"), MagneticCard);
#endif

#ifdef CAP_HID_CARD
   AddItem(F("HID Card"), HidCard);
#endif

#ifdef CAP_HID_CARD_2
   AddItem(F("HID Card 2"), HidCard2);
#endif

   DrawDiagnostics();

   for (;;) {
      key = GetKey();

      if (key >= '1' && key <= '1' + NumItems - 1) {
         Items[key - '1'].Proc(NULL);

         // Repaint the items after returning.
         DrawDiagnostics();
      }
   }
}
