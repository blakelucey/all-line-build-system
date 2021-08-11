/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

   Interfaces with the DFM Adapter Board

*/

#include "dfmadapter.h"
#include "time.h"
#include "cmd.h"
#include "display.h"
#include "uart.h"

#ifdef CAP_DFM

#define BAUD_RATE             38400
#define DFM_ADAPTER_TIMEOUT   200
#define GAUGE_INTERVAL        500
#define NUM_GAUGES            8

#define PACKET_SIGNATURE   0xDEADBEEF
#define BOOT_SIGNATURE     0xB007

#define PTYPE_DFM_TRANSFER 0xAC
#define PTYPE_GAUGES       0x7B
#define PTYPE_HELLO        0x9C
#define PTYPE_MEMORY_TEST  0x2E
#define PTYPE_BOOTLOADER   0x4F

// These are packets that we receive from the DFM adapter board.
typedef struct IN_PACKET {
   uint32_t Signature;
   uint8_t Type;
   uint16_t Index;
   uint8_t Payload[DFM_RECORD_SIZE];
   uint8_t Checksum; // Checksum is a good idea for a large packet like this.
} IN_PACKET;

// These are packets that we send from the Fuel Boss board.
typedef struct OUT_PACKET {
   uint32_t Signature;
   uint8_t Type;
   uint8_t TypeAgain; // No checksum needed, just compare Type == TypeAgain.
   uint16_t Param;
   uint16_t ParamAgain; // Same.
} OUT_PACKET;

// Incoming and outgoing packet memory.
static IN_PACKET InPacket;
static OUT_PACKET OutPacket;

// Sliding window packet detection.
#define WAITING_FOR_WINDOW 0
#define WAITING_FOR_DATA   1

static union { uint32_t Signature; uint8_t Data[4]; } Window;
static uint8_t PacketState = WAITING_FOR_WINDOW;
static uint8_t PacketPointer = 0;
static uint8_t PacketComplete = false;
static uint16_t BadChecksums = 0;

static uint32_t LastGaugeReading = 0;
static int16_t GaugeReadings[NUM_GAUGES];

static inline uint8_t ComputeChecksum (const void *vptr, const void *const vend)
{
   const uint8_t *ptr = vptr;
   const uint8_t *const end = vend;
   uint8_t cksum = 0;

   while (ptr != end) cksum += *ptr++;

   return cksum;
}

static inline void ProcessPacket (void)
{
   PacketComplete = false;
}

static inline void SendPacket (uint8_t type, uint16_t param)
{
   OutPacket.Signature = PACKET_SIGNATURE;
   OutPacket.Type = type;
   OutPacket.TypeAgain = type;
   OutPacket.Param = param;
   OutPacket.ParamAgain = param;

   const uint8_t *ptr = (void *)&OutPacket;
   const uint8_t *const end = ptr + sizeof(OUT_PACKET);

   while (ptr != end) Uart0Write(*ptr++);
}

static void WaitingForWindow (void)
{
   // See the DFM adapter board's fuelboss.c for this.
   // If we haven't processed the stored packet, don't try getting a new one.
   if (PacketComplete) return;
   if (!Uart0Available()) return;

   // Fast and simple signature detection.
   Window.Data[0] = Window.Data[1];
   Window.Data[1] = Window.Data[2];
   Window.Data[2] = Window.Data[3];
   Window.Data[3] = Uart0Read();

   // Signature match?
   if (Window.Signature == PACKET_SIGNATURE) {
      InPacket.Signature = PACKET_SIGNATURE;
      PacketPointer = 0;
      PacketState = WAITING_FOR_DATA;
   }
}

static void WaitingForData (void)
{
   // Write to the packet starting after the signature.
   // We need to write sizeof(packet)-4 bytes.
   static uint8_t *const PacketMemory = (void *)(&InPacket.Type);

   // We're waiting for enough data to fill the packet.
   while (Uart0Available()) {
      // Incoming data?
      PacketMemory[PacketPointer++] = Uart0Read();

      // Complete packet?
      if (PacketPointer == sizeof(IN_PACKET) - sizeof(InPacket.Signature)) {
         PacketState = WAITING_FOR_WINDOW;

         // Check the data integrity.
         uint8_t comp = ComputeChecksum(PacketMemory, &InPacket.Checksum);

         if (InPacket.Checksum != comp) {
            // Bad checksum.
            BadChecksums++;
            break;
         }

         // This looks okay.
         PacketComplete = true;
      }
   }
}

uint8_t WaitForPacket (void)
{
   // This waits up to 200ms for a complete packet from the DFM adapter board.
   // If one does not arrive, return false. Otherwise, return true.
   uint32_t timer = Now();

   for (;;) {
      if (Now() - timer >= DFM_ADAPTER_TIMEOUT) return false;

      switch (PacketState) {
         case WAITING_FOR_WINDOW:
            WaitingForWindow();
            break;

         case WAITING_FOR_DATA:
            WaitingForData();
            break;
      }

      if (PacketComplete) {
         // Looks OK!
         return true;
      }
   }

   return false;
}

int16_t GetGaugeReading (uint8_t id)
{
   // If we haven't refreshed the reading in a while, do that.
   if (LastGaugeReading == 0 || Now() - LastGaugeReading > GAUGE_INTERVAL) {
      SendPacket(PTYPE_GAUGES, 0);
      if (WaitForPacket()) {
         // This packet contains 'Param' number of 16-bit signed ints.
         // Unpack those into our analog reading cache.
         // NUM_GAUGES must match 'Param'!
         uint8_t high, low, ptr = 0;

         for (uint8_t i = 0; i < NUM_GAUGES; i++) {
            low  = InPacket.Payload[ptr++];
            high = InPacket.Payload[ptr++];

            GaugeReadings[i] = high << 8 | low;
         }

         ProcessPacket();
      }

      // We may not have gotten our packet. That means we'll have weird readings
      // until we have to ask the DFM adapter board again.
      LastGaugeReading = Now();
   }

   return GaugeReadings[id];
}

void BeginDfmTransfer (void)
{
   SendPacket(PTYPE_DFM_TRANSFER, 0);
}

void EndDfmTransfer (void)
{
   Uart0Write(CMD_DFM_TRANSFER_STOP);
}

void DoDfmTransfer (void)
{
   // This stalls the entire command processor to stream data from the
   // DFM, to the DFM adapter, to the mainboard, then to the ARM CPU.
   // The DFM is awfully picky about timing, so capturing the data this
   // way lets the much stronger ARM CPU disassemble the packets.

   uint8_t TotalBytes = 0;
   SendPacket(PTYPE_DFM_TRANSFER, 0);

   for (;;) {
      if (Uart3Available() && Uart3Read() == CMD_DFM_TRANSFER_STOP) {
         // The DFM adapter board understands the STOP command like we do.
         // It doesn't have to be a packet.
         Uart0Write(CMD_DFM_TRANSFER_STOP);
         break;
      }

      // Anything coming from the DFM board gets sent to the ARM CPU.
      while (Uart0Available()) {
         Uart3Write(Uart0Read());
         TotalBytes++;
         if (TotalBytes == 32) {
            // Toggle an indicator on the display.
            InvertRowSegment(5, DISPLAY_WIDTH / 2 - 4, DISPLAY_WIDTH / 2 + 3);
            Refresh();
            TotalBytes = 0;
         }
      }
   }
}

void InvokeDfmAdapterBootloader (void)
{
   // Send a command to invoke the bootloader.
   SendPacket(PTYPE_BOOTLOADER, BOOT_SIGNATURE);
}

void InitializeDfmAdapter (void)
{
   // We're using the RS-232 port to talk to the DFM adapter board.
   // That's on USART0.
   InitializeUart0(BAUD_RATE, 8, NO_PARITY, ONE_STOP_BIT);
}

void UpdateDfmAdapter (void)
{
}

#endif // CAP_DFM
