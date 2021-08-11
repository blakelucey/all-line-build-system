/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

*/

#include "common.h"
#include "inputs.h"

#define HANDLE_DDR      DDRL
#define HANDLE_PORT     PORTL
#define HANDLE_PIN      PINL
#define HANDLE_BIT(n)   (1 << (n))
#define HANDLE_ALLBITS  0xFF

#define SENSOR_DDR      DDRF
#define SENSOR_PORT     PORTF
#define SENSOR_PIN      PINF
#define SENSOR_BIT(n)   (1 << (4 + (n)))
#define SENSOR_ALLBITS  0xF0

#define HANDLE_POLL(n)  do { \
   HandleCounters[n] = (HandleCounters[n] << 1) | ((HANDLE_PIN & HANDLE_BIT(n)) == 0); \
   if (HandleStates[n] == 0) { \
      if (HandleCounters[n] == 0xff) { \
         HandleStates[n] = 1; \
      } \
   } \
   else { \
      if (HandleCounters[n] == 0x00) { \
         HandleStates[n] = 0; \
      } \
   } \
} while (0)

#define SENSOR_POLL(n)  do { \
   if (SensorTypes[n]) break; \
   SensorCounters[n] = (SensorCounters[n] << 1) | ((SENSOR_PIN & SENSOR_BIT(n)) == 0); \
   if (SensorStates[n] == 0) { \
      if (SensorCounters[n] == 0xff) { \
         SensorStates[n] = 1; \
      } \
   } \
   else { \
      if (SensorCounters[n] == 0x00) { \
         SensorStates[n] = 0; \
      } \
   } \
} while (0)

volatile uint8_t HandleStates[NUM_HANDLES] = {0, };
volatile uint8_t HandleCounters[NUM_HANDLES] = {0, };

volatile uint8_t SensorTypes[NUM_SENSORS] = {0, };
volatile uint8_t SensorStates[NUM_SENSORS] = {0, };
volatile uint8_t SensorCounters[NUM_SENSORS] = {0, };

ISR(TIMER1_COMPA_vect)
{
   HANDLE_POLL(0);
   HANDLE_POLL(1);
   HANDLE_POLL(2);
   HANDLE_POLL(3);

   HANDLE_POLL(4);
   HANDLE_POLL(5);
   HANDLE_POLL(6);
   HANDLE_POLL(7);

   SENSOR_POLL(0);
   SENSOR_POLL(1);
   SENSOR_POLL(2);
   SENSOR_POLL(3);
}

void SetSensorType (uint8_t id, uint8_t type)
{
   SensorTypes[id] = type;
}

uint8_t GetSensorType (uint8_t id)
{
   return SensorTypes[id];
}

uint8_t GetSensorState (uint8_t id)
{
   if (SensorTypes[id]) return 0;
   return SensorStates[id];
}

uint8_t GetHandleState (uint8_t id)
{
   return HandleStates[id];
}

uint16_t GetSensorReading (uint8_t id)
{
   if (!SensorTypes[id]) return 0;

   // Activate the ADC and perform a conversion. The sensors from 0-3 are actually
   // on ADC channels 4-7.
   id += 4;

   ADMUX = (ADMUX & ~0x1F) | (id & 0x1F);
   ADCSRA |= (1 << ADSC);

   // Wait for the conversion to complete.
   while ((ADCSRA & (1 << ADSC)));

   // Grab the result using the 16-bit ADC register.
   // Saves us from accessing ADCH/L in the wrong order.
   uint16_t result = ADC;

   return result;
}

void InitializeInputs (void)
{
   // Input, with a weak pull-up
   HANDLE_DDR &= ~HANDLE_ALLBITS;
   HANDLE_PORT |= HANDLE_ALLBITS;

   // Input, also with a weak pull-up
   SENSOR_DDR &= ~SENSOR_ALLBITS;
   SENSOR_PORT |= SENSOR_ALLBITS;

   // Start a periodic timer for sampling in the inputs.
   cli();
   TCCR1A = 0;
   TCCR1B = 0;
   TCNT1 = 0;

   OCR1A = 0x1869;
   TCCR1B = (1 << CS10) | (1 << CS11) | (1 << WGM12);
   TIMSK1 |= (1 << OCIE1A);

   // Also initialize the analog-to-digital converter.
   ADCSRA = (1 << ADPS0) | (1 << ADPS1) | (1 << ADPS2);
   ADMUX = (1 << REFS0);
   ADCSRB = 0;
   ADCSRA |= (1 << ADEN);

   sei();
}
