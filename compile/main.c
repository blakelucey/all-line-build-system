/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

*/

#include "common.h"
#include "dfmadapter.h"
#include "diag.h"
#include "display.h"
#include "time.h"
#include "keypad.h"
#include "speaker.h"
#include "cmd.h"
#include "card.h"
#include "counters.h"
#include "outputs.h"
#include "uart.h"
#include "log.h"
#include "inputs.h"

uint8_t GetCapabilityBits (void)
{
   uint8_t caps = 0;

#if defined(CAP_DFM)
   caps |= CAPBIT_DFM;
#endif

#if defined(CAP_TANK_GAUGES)
   caps |= CAPBIT_TANK_GAUGES;
#endif

#if defined(CAP_MAGNETIC_CARD)
   caps |= CAPBIT_MAGNETIC_CARD;
#endif

#if defined(CAP_HID_CARD)
   caps |= CAPBIT_HID_CARD;
#endif

#if defined(CAP_HID_CARD_2)
   caps |= CAPBIT_HID_CARD_2;
#endif

#if defined(CAP_DFM_READING)
   caps |= CAPBIT_DFM_READING;
#endif

   return caps;
}

uint8_t Ptr = 0;
uint8_t Temp[100];

void Writer (uint8_t ch)
{
   Temp[Ptr++] = ch;
}

static void InitializeGPIO (void)
{
   // Set up our GPIO lines to the Pi as all high-impedance
   DDRG &= ~(1 << 2);
   DDRJ &= ~((1 << 2) | (1 << 3) | (1 << 4) | (1 << 5) | (1 << 6));

   PORTG &= ~(1 << 2);
   PORTJ &= ~((1 << 2) | (1 << 3) | (1 << 4) | (1 << 5) | (1 << 6));
}

int main (void)
{
   InitializeGPIO();
   InitializeTime();
   InitializeLog();
   InitializeCounters();
   InitializeSpeaker();
   InitializeDisplay();
   InitializeKeypad();
   InitializeInputs();
   InitializeOutputs();
   InitializeCommands();
   InitializeCard();
   InitializeDfmAdapter();

   _delay_ms(500);
   Beep();
   Clear();
   DrawStringP(4, 4, F("System is booting up..."));
   Refresh();

   //void MagneticCard (void *param);
   //for (;;) MagneticCard(NULL);
   CheckForDiagnostics();
   for (;;) CheckForCommand();
}

