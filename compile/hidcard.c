/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

   HID Card Support

   The HID reader sends 16 bytes to the caller. Currently, the first word is the HID
   facility number, and the second word is the HID card number. The rest of the data
   is unused but reserved for further expansion.

*/

#include "common.h"
#include "card.h"
#include "time.h"

#ifdef CAP_HID_CARD 

// Todo: support dual HID card readers
#ifdef CAP_HID_CARD_2
#error Dual HID card readers are not yet supported.
#endif

#define HID_DDR      DDRK
#define HID_PORT     PORTK
#define HID_ALLBITS  ((1 << 0) | (1 << 1) | (1 << 2) | (1 << 3))

// 26-bit Wiegand data format
#define HID_DATASIZE 26

// This is the size of the HID data packet that gets sent to the receiver.
#define HID_SENDSIZE ((sizeof(uint16_t) * 2) + (sizeof(uint32_t) * 8))

// Read timeout
#define HID_TIMEOUT  50

#define A_STATE      ((PINK & (1 << 0)) == 0)
#define B_STATE      ((PINK & (1 << 1)) == 0)

// Parity check results 
#define PC_EVEN      0
#define PC_ODD       1

static volatile uint32_t HidData = 0;
static volatile uint8_t HidBitCounter = 0;
static volatile uint32_t HidTimer = 0;

static uint16_t HidNumber = 0;
static uint16_t HidFacility = 0;

ISR(TIMER4_COMPA_vect)
{
   // This interrupt resets the card reader state automatically when no data has
   // arrived for a while.
   if (HidBitCounter > 0 && HidBitCounter < HID_DATASIZE) {
      if (HidTimer > 0 && Milliseconds - HidTimer >= HID_TIMEOUT) {
         HidData = 0;
         HidBitCounter = 0;
         HidTimer = 0;
      }
   }
}

ISR(PCINT2_vect)
{
   if (A_STATE && !B_STATE) {
      HidData = (HidData << 1) | 1;
      HidBitCounter++;
      HidTimer = Milliseconds;
   }
   else if (!A_STATE && B_STATE) {
      HidData <<= 1;
      HidBitCounter++;
      HidTimer = Milliseconds;
   }
   else {
      // Invalid state.
      return;
   }

   // Do we have all of the bits?
   if (HidBitCounter == HID_DATASIZE) {
      // Yes, we can disable this interrupt so we don't get any more data.
      PCICR &= ~(1 << PCIE2);
      return;
   }
}

static uint8_t CheckParity (uint16_t word)
{
   uint8_t parity = 0;
   uint32_t temp = word;

   for (parity = 0; temp > 0; temp >>= 1) {
      parity ^= (temp & 0x01);
   }

   return parity;
}

uint8_t IsCardDataAvailable (void)
{
   // Cache volatiles.
   cli();
   uint32_t data = HidData;
   uint8_t bits = HidBitCounter;
   sei();

   // Not enough data?
   if (bits < HID_DATASIZE) return false;

   // Split the card data into two 13-bit fields.
   uint16_t f, n;

   f = (data >> 13) & 0x1fff;
   n = (data & 0x1fff);

   // Parity check.
   if (CheckParity(f) != PC_EVEN || CheckParity(n) != PC_ODD) {
      // No, one or both checks failed.
      return false;
   } 

   // Everything looks good.
   data >>= 1;
   HidNumber = data & 0xffff;

   data >>= 16;
   HidFacility = data & 0xff;

   return true;
}

// This resets the card reader to get it ready to scan another card.
void ResetCardReader (void)
{
   HidData = 0;
   HidTimer = 0;
   HidBitCounter = 0;

   // Re-enable the interrupt.
   cli();
   PCICR |= (1 << PCIE2);
   sei();
}

void SendCardData (BYTE_WRITER writer)
{
   union { uint16_t word; uint8_t bytes[2]; } var;

   // Write H (to indicate HID data), followed by a one-byte facility code.
   writer('H');
   writer(HidFacility);

   // Now write a 2-byte HID card number.
   var.word = HidNumber;
   writer(var.bytes[0]);
   writer(var.bytes[1]);

   // Send some padding bytes.
   for (uint8_t i = 0; i < HID_SENDSIZE - sizeof(uint16_t) * 2; i++) writer(0);
}

int16_t GetHidFacility (void)
{
   int16_t ret;
   cli();
   ret = HidFacility;
   sei();
   return ret;
}

int16_t GetHidNumber (void)
{
   int16_t ret;
   cli();
   ret = HidNumber;
   sei();
   return ret;
}

void InitializeCard (void)
{
   // The HID reader uses two digital input pins with no pull-up
   HID_DDR &= ~HID_ALLBITS;
   HID_PORT &= ~HID_ALLBITS;

   // Those input pins have pin-change interrupts we can attach to them.
   cli();
   PCMSK2 |= ((1 << PCINT17) | (1 << PCINT16));

   // Additionally, set up timer 4 for periodic state resets. (See the ISRs above.)
   TCCR4A = 0;
   TCCR4B = 0;
   TCNT4 = 0;

   OCR4A = 0x1869;
   TCCR4B = (1 << CS40) | (1 << CS41) | (1 << WGM42);
   TIMSK4 |= (1 << OCIE4A);
   sei();

   // Reset the card; this also enables the pin-change interrupt.
   ResetCardReader();
}

#endif // CAP_HID_CARD

