/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

*/

#include "common.h"
#include "outputs.h"

#define OUTPUT_DDR      DDRC
#define OUTPUT_PORT     PORTC
#define OUTPUT_PIN      PINC
#define OUTPUT_BIT(n)   (1 << (n))
#define OUTPUT_ALLBITS  0xFF

#define ALARM_DDR       DDRD
#define ALARM_PORT      PORTD
#define ALARM_PIN       PIND
#define ALARM_BIT(n)    (1 << ((n) + 6))
#define ALARM_ALLBITS   0xC0

void InitializeOutputs (void)
{
   OUTPUT_DDR |= OUTPUT_ALLBITS;
   OUTPUT_PORT &= ~OUTPUT_ALLBITS;

   ALARM_DDR |= ALARM_ALLBITS;
   ALARM_PORT &= ~ALARM_ALLBITS;
}

void SetOutput (uint8_t id, uint8_t state)
{
   if (state) {
      OUTPUT_PORT |= OUTPUT_BIT(id);
   }
   else {
      OUTPUT_PORT &= ~OUTPUT_BIT(id);
   }
}

uint8_t GetOutput (uint8_t id)
{
   return (OUTPUT_PIN & OUTPUT_BIT(id)) != 0;
}

void SetAlarmOutput (uint8_t id, uint8_t state)
{
   if (state) {
      ALARM_PORT |= ALARM_BIT(id);
   }
   else {
      ALARM_PORT &= ~ALARM_BIT(id);
   }
}

uint8_t GetAlarmOutput (uint8_t id)
{
   return (ALARM_PIN & ALARM_BIT(id)) != 0;
}
