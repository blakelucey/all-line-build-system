/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

   The counter chip is interfaced over serial channel 1. I'm choosing to use the
   port directly rather than used my buffered serial functions.

*/

#include <avr/eeprom.h>
#include "counters.h"
#include "time.h"

#define CTR_CYCLE_TIMEOUT        500

#define CTR_CMD_RESET            (0x40)
#define CTR_CMD_GET(n)           (0x10 | (n))
#define CTR_CMD_CLEAR(n)         (0x20 | (n))
#define CTR_CMD_SET_DEBOUNCE(n)  (0x30 | (n))
#define CTR_CMD_SYNC             (0x50)

#define CTR_EEPROM_START         (0x010)
#define CTR_EEPROM_PTR(n)        ((CTR_EEPROM_START) + (n))

#define CTR_WRITE(n) do { \
   while (!(UCSR1A & (1 << UDRE1))); \
   UDR1 = (n); \
} while (0)

static int16_t Cycles = 0;

static inline uint8_t GetByte (uint8_t *dest)
{
   Cycles = 0;

   while (!(UCSR1A & (1 << RXC1))) {
      if (Cycles == CTR_CYCLE_TIMEOUT) return false;
      Cycles++;
   }

   *dest = UDR1;

   return true;
}

void InitializeCounters (void)
{
   cli();

   UCSR1A = (1 << U2X1);
   UCSR1B = (1 << TXEN1) | (1 << RXEN1);
   UCSR1C = (1 << UCSZ10) | (1 << UCSZ11);

   UBRR1 = 0x19;

   sei();

   SyncWithCounterChip();

   // Upload all of our debounce periods into the debounce chip.
   // If the value is 0xFF, it's uninitialized, and assume the default 0x20 (32).
   uint8_t periods;
   for (uint8_t id = 0; id < NUM_COUNTERS; id++) {
      periods = GetCounterDebounce(id);
      if (periods == 0xFF) periods = 0x20;
      SetCounterDebounce(id, periods);
   }
}

void SyncWithCounterChip (void)
{
   // Send the reset command.
   CTR_WRITE(CTR_CMD_RESET);
   _delay_ms(2.5);

   // To synchronize with the counter chip, we send it CTR_CMD_SYNC, followed
   // by any number. It will send back that number plus one. Do this a few times.
   const uint8_t sends[] = {130, 37, 99, 84, 17, 62, 177, 204, 220, 140, 0};
   uint8_t iter = 0;
   uint8_t got = 0;

   while (sends[iter] != 0) {
      // Send the sync command.
      CTR_WRITE(CTR_CMD_SYNC);

      // Send the challenge byte.
      CTR_WRITE(sends[iter]);

      // Read the result.
      if (!GetByte(&got)) {
         // We aren't hearing back from it. Something bad has probably happened.
         // Todo: fix counter chip failure detection
         break;
      }

      got = UDR1;

      if ((int16_t)got != ((sends[iter] + 1) & 0xff)) {
         // No match; retry.
         continue;
      }
      else {
         // Match. Increase iteration.
         iter++;
      }
   }
}

void SetCounterDebounce (uint8_t id, uint8_t periods)
{
   CTR_WRITE(CTR_CMD_SET_DEBOUNCE(id));
   _delay_us(50.0);
   CTR_WRITE(periods);

   eeprom_update_byte((void *)CTR_EEPROM_PTR(id), periods);
}

uint8_t GetCounterDebounce (uint8_t id)
{
   // Read the debounce period from EEPROM.
   uint8_t period;
   
   period = eeprom_read_byte((void *)CTR_EEPROM_PTR(id));   
   return period;
}

void ClearCounter (uint8_t id)
{
   CTR_WRITE(CTR_CMD_CLEAR(id));
}

COUNTER GetCounter (uint8_t id)
{
   CTR_WRITE(CTR_CMD_GET(id));

   union { uint32_t dword; uint8_t bytes[4]; } var;

   if (!GetByte(&var.bytes[0])) return 0;
   if (!GetByte(&var.bytes[1])) return 0;
   if (!GetByte(&var.bytes[2])) return 0;
   if (!GetByte(&var.bytes[3])) return 0;

   return var.dword;
}
