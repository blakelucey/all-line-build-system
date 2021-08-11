/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

   Interfaces with a MagTek Card Reader

   Cannot be used at the same time as the Brush card reader, since the same
   GPIO pins, interrupts and timers are used. Also can't be used with the
   HID card reader.

*/

#include "common.h"
#include "card.h"

#if defined(CAP_MAGNETIC_CARD) && defined(MAGCARD_MAGTEK)

// TODO: Fix the MagTek reading logic; it's a little outdated.
//#error MagTek card readers currently do not work correctly; tell Steven you need this fixed.

#define MAG_DDR         DDRK
#define MAG_PORT        PORTK
#define MAG_ALLBITS     ((1 << 0) | (1 << 1) | (1 << 2) | (1 << 3))

#define RESET_TIMEOUT() do { TCNT4 = 1; } while (0)

#define FRONT_SIGNAL    ((PINK & (1 << 3)) == 0)
#define BACK_SIGNAL     ((PINK & (1 << 2)) == 0)
#define STROBE_SIGNAL   ((PINK & (1 << 1)) == 0)
#define DATA_SIGNAL     ((PINK & (1 << 0)) == 0)

#define FRONT_PCINT     (1 << PCINT19)
#define BACK_PCINT      (1 << PCINT18)
#define STROBE_PCINT    (1 << PCINT17)
#define DATA_PCINT      (1 << PCINT16)

#define TRACK_2_SIZE             40
#define TRACK_2_BITS_PER_CHAR    5
#define TRACK_2_TOTAL_BITS       (TRACK_2_SIZE * TRACK_2_BITS_PER_CHAR)

// The Magtek-baseds reader is not deep enough to read the whole card.
// That means there's really only 30 or so "reliable" characters.
#define TRACK_2_RELIABLE_CHARS   30
#define TRACK_2_RELIABLE_BITS    (TRACK_2_RELIABLE_CHARS * TRACK_2_BITS_PER_CHAR)

#define ENABLE_PCINTS()          do { PCICR |= (1 << PCIE2); } while (0)
#define DISABLE_PCINTS()         do { PCICR &= ~(1 << PCIE2); } while (0)

#define PCINT_MASK               PCMSK2

// Resets the state machine to get ready for a card read.
#define RESET_STATE() do { \
   MagPointer = 0; \
   MagState = S_FRONT; \
   MagLrcCheck = 1; \
   cli(); \
   TIMSK4 &= ~(1 << OCIE4A); \
   PCICR |= (1 << PCIE2); \
   PCMSK2 |= FRONT_PCINT; \
   sei(); \
} while (0)

// Sets the state machine up to handle an error.
#define ERROR_STATE() do { \
   MagState = S_ERROR; \
   cli(); \
   PCINT_MASK = FRONT_PCINT; \
   RESET_TIMEOUT(); \
   TCCR4B = 0; \
   TIMSK4 &= ~(1 << OCIE4A); \
   sei(); \
} while (0)

enum {
   S_FRONT,       // Waiting for the "card has hit the front sensor" signal
   S_LOW_DATA,    // Waiting for the data line to go low
   S_READING,     // Reading data; if card hits the back sensor, we're done
   S_NO_FRONT,    // Waiting for the front sensor to no longer trigger
   S_COMPLETE,    // We have completed a valid read. Wait to be manually reset.
   S_ERROR        // Something bad has happened; wait for the card to be completely removed.
};

static volatile uint8_t MagData[TRACK_2_TOTAL_BITS];
static volatile uint8_t MagPointer = 0;
static volatile uint8_t MagState = S_FRONT;
static volatile uint8_t MagLrcCheck = 1;

ISR(PCINT2_vect)
{
   switch (MagState) {
   case S_COMPLETE:
      // There is a result stored that has not yet been retrieved. Do nothing.
      return;

   case S_FRONT:
      // We're waiting for the front-of-card detection to trigger.
      if (FRONT_SIGNAL) {
         // We've got it. Disable the int for this pin, and enable it for the data pin.
         PCINT_MASK = DATA_PCINT;

         // Additionally, enable timer 4. When timer 4's ISR triggers, it's been too long
         // and we need to reset the state machine.
         RESET_TIMEOUT();
         OCR4A = 0x5b8d; // About 750 ms
         TCCR4A = 0;
         TCCR4B = (1 << CS42) | (1 << WGM42);
         TIMSK4 |= (1 << OCIE4A);

         // Reset our pointer.
         MagPointer = 0;

         MagState = S_LOW_DATA;
      }

      break;

   case S_LOW_DATA:
      // We're waiting for the data line to go low.
      if (DATA_SIGNAL) {
         // It's low. Disable the int for this pin, and enable it for the strobe pin.
         PCINT_MASK = STROBE_PCINT;
         MagState = S_READING;

         // Reset the timer.
         RESET_TIMEOUT();
      }

      break;

   case S_READING:
      // We are reading data from the card.
      if (!STROBE_SIGNAL) {
         // Clock in data on the falling edge of the strobe signal.
         MagData[MagPointer++] = DATA_SIGNAL;
         if (MagPointer == TRACK_2_RELIABLE_BITS) {
            PCINT_MASK = FRONT_PCINT;
            MagState = S_NO_FRONT;
            RESET_TIMEOUT();
         }
      }

      break;

   case S_NO_FRONT:
      // Wait for the front detection pin to go high.
      if (!FRONT_SIGNAL && !BACK_SIGNAL) {
         PCINT_MASK = 0;
         MagState = S_COMPLETE;

         // Disable the error timer.
         TCCR4B = 0;
         TIMSK4 &= ~(1 << OCIE4A);

         break;
      }

      break;

   case S_ERROR:
      // Something has gone wrong and we're now waiting for the card to be removed
      // completely before we can read anything again.
      if (!FRONT_SIGNAL && !BACK_SIGNAL) {
         // Card is out. Disable everything except the front int.
         PCINT_MASK = FRONT_PCINT;
         MagState = S_FRONT;
         MagPointer = 0;
         break;
      }

      break;
   }
}

ISR(TIMER4_COMPA_vect)
{
   // If this is executing, the card read has timed out or otherwise had an error.
   // Set the card reader to the error state.
   ERROR_STATE();
}

void InitializeCard (void)
{
   // Set up the inputs for the data and strobe connection.
   MAG_DDR &= ~MAG_ALLBITS;
   MAG_PORT &= ~MAG_ALLBITS;

   cli();
   PCMSK2 = 0;

   // Configure timer 4.
   TCCR4A = 0;
   TCCR4B = 0;
   sei();

   ResetCardReader();
}

uint8_t IsCardDataAvailable (void)
{
   return MagState == S_COMPLETE;
}

uint8_t IsCardError (void)
{
   return MagState == S_ERROR;
}

void CopyCardDataAsText (char *dest)
{
   uint8_t ch;

   cli();
   uint8_t len = MagPointer;
   for (uint8_t i = 0; i < len; i += 5) {
      ch = 
         ((MagData[i + 4]) << 4) |
         ((MagData[i + 3]) << 3) |
         ((MagData[i + 2]) << 2) |
         ((MagData[i + 1]) << 1) |
         ((MagData[i + 0]) << 0);

      *dest++ = (char)((ch & 0xf) + '0');
   }
   *dest = 0;
   sei();
}

int16_t CopyCardData (char *dest)
{
   for (uint8_t i = 0; i < TRACK_2_TOTAL_BITS; i++) {
      dest[i] = (MagData[i] & 0x0F) + '0';
   }

   return TRACK_2_TOTAL_BITS;
}

void SendCardData (BYTE_WRITER writer)
{
   uint8_t len = MagPointer;

   for (uint8_t i = 0; i < len; i++) {
      writer(MagData[i]);
   }

   // The ARM side expects 240 bytes, and not 200. Sent some padding.
   // It also wants a final 0xFF byte after the real data, so do that first.
   writer(0xFF);
   for (uint8_t i = 0; i < 240 - 1 - len; i++) {
      writer(0);
   }
}

void ResetCardReader (void)
{
   RESET_STATE();
}

#endif // CAP_MAGNETIC_CARD && MAGCARD_BRUSH
