/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

*/

#include "common.h"
#include "speaker.h"

#define SPK_DDR      DDRE
#define SPK_PORT     PORTE
#define SPK_BIT      (1 << 3)
#define SPK_PRESCALE 256UL

volatile uint16_t Counter = 0;
volatile uint16_t Limit = 0;

ISR(TIMER3_COMPA_vect)
{
   Counter++;
   if (Counter >= Limit) {
      // Stop the speaker.
      TCCR3A &= ~(1 << COM3A0);
      TIMSK3 &= ~(1 << OCIE3A);
      SPK_PORT &= ~SPK_BIT;
   }
}

void Silence (void)
{
   TCCR3A &= ~(1 << COM3A0);
   TIMSK3 &= ~(1 << OCIE3A);
   SPK_PORT &= ~SPK_BIT;
}

void Play (uint16_t freq, uint16_t dur)
{
   uint16_t calc = (F_CPU / (2UL * SPK_PRESCALE * (uint32_t)freq));

   // Turn off interrupts before setting Limit or Counter
   cli();

   Limit = (uint32_t)dur * (uint32_t)freq / 1000UL;

   // Set up the wave mode
   TCCR3B &= ~((1 << CS30) | (1 << CS31));
   TCCR3B |= (1 << CS32);

   // Trigger the timer and interrupt on compare match
   TCCR3A |= (1 << COM3A0);
   TIMSK3 |= (1 << OCIE3A);
   TCNT0 = 0;
   OCR3A = calc;
   Counter = 0;

   // Enable interrupts. The speaker will handle itself.
   sei();
}

void Click (void)
{
   // Generates a single "click" from the speaker
   cli();
   Counter = 0;
   Limit = 16;
   SPK_PORT |= SPK_BIT;
   TIMSK3 |= (1 << OCIE3A);
   sei();
}

void Beep (void)
{
   Play(BEEP_FREQ, BEEP_DUR);
}

void ErrorBeep (void)
{
   Play(ERROR_FREQ, ERROR_DUR);
}

void InitializeSpeaker (void)
{
   SPK_DDR |= SPK_BIT;
   SPK_PORT &= ~SPK_BIT;

   cli();
   TCCR3A = 0;
   TCCR3B = 0;
   TCCR3B = (1 << WGM32);
   sei();
}
