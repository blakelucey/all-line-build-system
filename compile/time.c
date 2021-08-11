/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

*/

#include "common.h"

volatile uint32_t Milliseconds = 0;

ISR(TIMER0_COMPA_vect)
{
   Milliseconds++;
}

void InitializeTime (void)
{
   // Disable interrupts and set a timer routine every 1 ms
   // Timer 0 will have a prescaler of 64.
   cli();

   TCCR0A = 0;
   TCCR0B = 0;
   TCNT0 = 0;

   OCR0A = 0x7C;
   TCCR0A |= (1 << WGM01);
   TCCR0B |= (1 << CS00) | (1 << CS01);
   TIMSK0 |= (1 << OCIE0A);
   sei();
}

volatile uint32_t Now (void)
{
   cli();
   uint32_t temp = Milliseconds;
   sei();
   return temp;
}
