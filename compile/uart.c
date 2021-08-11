/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

*/

#include <avr/io.h>
#include <avr/interrupt.h>
#include "uart.h"

#define UART_BUFFER_SIZE 128
#define UART_BUFFER_MOD  127

#define UART_RX_VECTOR(nr) \
   ISR(USART##nr##_RX_vect) { \
      uint8_t i = (uint8_t)(RxBuffer##nr.Head + 1) & UART_BUFFER_MOD; \
      if (i != RxBuffer##nr.Tail) { \
         RxBuffer##nr.Buffer[RxBuffer##nr.Head] = UDR##nr; \
         RxBuffer##nr.Head = i; \
      } \
   }

#define UART_TX_VECTOR(nr) \
   ISR(USART##nr##_UDRE_vect) { \
      if (TxBuffer##nr.Head == TxBuffer##nr.Tail) { \
         UCSR##nr##B &= ~_BV(UDRIE##nr); \
      } else { \
         uint8_t c = TxBuffer##nr.Buffer[TxBuffer##nr.Tail]; \
         TxBuffer##nr.Tail = (TxBuffer##nr.Tail + 1) & UART_BUFFER_MOD; \
         UDR##nr = c; \
      } \
   }

#define UART_INIT_MACRO(nr) \
   void InitializeUart##nr (uint32_t baud, uint8_t data_bits, uint8_t parity, uint8_t stop_bits) { \
      uint16_t baud_setting; \
      uint8_t use2x = 1; \
      \
      if (baud == 57600) { \
         use2x = 0; \
      } \
      \
      try_again: \
      if (use2x) { \
         UCSR##nr##A = _BV(U2X##nr); \
         baud_setting = (F_CPU / 4 / baud - 1) / 2; \
      } else { \
         UCSR##nr##A = 0; \
         baud_setting = (F_CPU / 8 / baud - 1) / 2; \
      } \
      \
      if ((baud_setting > 4095) && use2x) { \
         use2x = 0; \
         goto try_again; \
      } \
      \
      UBRR##nr##H = baud_setting >> 8; \
      UBRR##nr##L = baud_setting; \
      \
      UCSR##nr##C &= ~(_BV(UCSZ##nr##0) | _BV(UCSZ##nr##1)); \
      UCSR##nr##B &= ~(_BV(UCSZ##nr##2)); \
      switch (data_bits) { \
         case 6: \
            UCSR##nr##C |= _BV(UCSZ##nr##0); \
            break; \
         case 7: \
            UCSR##nr##C |= _BV(UCSZ##nr##1); \
            break; \
         case 9: \
            UCSR##nr##C |= (_BV(UCSZ##nr##0) | _BV(UCSZ##nr##1)); \
            UCSR##nr##B |= _BV(UCSZ##nr##2); \
            break; \
         default: \
         case 8: \
            UCSR##nr##C |= (_BV(UCSZ##nr##0) | _BV(UCSZ##nr##1)); \
            break; \
      } \
      \
      UCSR##nr##C &= ~(_BV(UPM##nr##0) | _BV(UPM##nr##1)); \
      switch (parity) { \
         case EVEN_PARITY: \
            UCSR##nr##C |= _BV(UPM##nr##1); \
            break; \
         case ODD_PARITY: \
            UCSR##nr##C |= (_BV(UPM##nr##0) | _BV(UPM##nr##1)); \
            break; \
      } \
      \
      UCSR##nr##C &= ~_BV(USBS##nr); \
      if (stop_bits == TWO_STOP_BITS) { \
         UCSR##nr##C |= _BV(USBS##nr); \
      } \
      \
      UCSR##nr##B |= (_BV(RXEN##nr) | _BV(TXEN##nr) | _BV(RXCIE##nr)); \
      UCSR##nr##B &= ~_BV(UDRIE##nr); \
   }

#define UART_DEINIT_MACRO(nr) \
   void DeInitializeUart##nr () { \
      while (TxBuffer##nr.Head != TxBuffer##nr.Tail); \
      UCSR##nr##B &= ~(_BV(RXEN##nr) | _BV(TXEN##nr) | _BV(RXCIE##nr) | _BV(UDRIE##nr)); \
      RxBuffer##nr.Head = RxBuffer##nr.Tail; \
   }

#define UART_AVAILABLE_MACRO(nr) \
   int16_t Uart##nr##Available () { \
      return (int16_t)(UART_BUFFER_SIZE + RxBuffer##nr.Head - RxBuffer##nr.Tail) % UART_BUFFER_SIZE; \
   }

#define UART_PEEK_MACRO(nr) \
   int16_t Uart##nr##Peek () { \
      if (RxBuffer##nr.Head == RxBuffer##nr.Tail) { \
         return -1; \
      } else { \
         return RxBuffer##nr.Buffer[RxBuffer##nr.Tail]; \
      } \
   }

#define UART_READ_MACRO(nr) \
   int16_t Uart##nr##Read () { \
      if (RxBuffer##nr.Head == RxBuffer##nr.Tail) { \
         return -1; \
      } else { \
         uint8_t c = RxBuffer##nr.Buffer[RxBuffer##nr.Tail]; \
         RxBuffer##nr.Tail = (uint16_t)(RxBuffer##nr.Tail + 1) & UART_BUFFER_MOD; \
         return c; \
      } \
   }

#define UART_FLUSH_MACRO(nr) \
   void Uart##nr##Flush () { \
      while (TxBuffer##nr.Head != TxBuffer##nr.Tail); \
   }

#define UART_WRITE_MACRO(nr) \
   void Uart##nr##Write (uint8_t c) { \
      uint16_t i = (TxBuffer##nr.Head + 1) & UART_BUFFER_MOD; \
      \
      while (i == TxBuffer##nr.Tail); \
      TxBuffer##nr.Buffer[TxBuffer##nr.Head] = c; \
      TxBuffer##nr.Head = i; \
      \
      UCSR##nr##B |= _BV(UDRIE##nr); \
   }

typedef struct RING_BUFFER {
   uint8_t Buffer[UART_BUFFER_SIZE];
   volatile uint16_t Head;
   volatile uint16_t Tail;
} RING_BUFFER;

#ifdef USE_UART_0
   static RING_BUFFER RxBuffer0 = {{0}, 0, 0};
   static RING_BUFFER TxBuffer0 = {{0}, 0, 0};

   UART_INIT_MACRO(0)
   UART_DEINIT_MACRO(0)
   UART_AVAILABLE_MACRO(0)
   UART_PEEK_MACRO(0)
   UART_READ_MACRO(0)
   UART_WRITE_MACRO(0)
   UART_FLUSH_MACRO(0)
   UART_RX_VECTOR(0)
   UART_TX_VECTOR(0)
#endif

#ifdef USE_UART_1
   static RING_BUFFER RxBuffer1 = {{0}, 0, 0};
   static RING_BUFFER TxBuffer1 = {{0}, 0, 0};

   UART_INIT_MACRO(1)
   UART_DEINIT_MACRO(1)
   UART_AVAILABLE_MACRO(1)
   UART_PEEK_MACRO(1)
   UART_READ_MACRO(1)
   UART_WRITE_MACRO(1)
   UART_FLUSH_MACRO(1)
   UART_RX_VECTOR(1)
   UART_TX_VECTOR(1)
#endif

#ifdef USE_UART_2
   static RING_BUFFER RxBuffer2 = {{0}, 0, 0};
   static RING_BUFFER TxBuffer2 = {{0}, 0, 0};

   UART_INIT_MACRO(2)
   UART_DEINIT_MACRO(2)
   UART_AVAILABLE_MACRO(2)
   UART_PEEK_MACRO(2)
   UART_READ_MACRO(2)
   UART_WRITE_MACRO(2)
   UART_FLUSH_MACRO(2)
   UART_RX_VECTOR(2)
   UART_TX_VECTOR(2)
#endif

#ifdef USE_UART_3
   static RING_BUFFER RxBuffer3 = {{0}, 0, 0};
   static RING_BUFFER TxBuffer3 = {{0}, 0, 0};

   UART_INIT_MACRO(3)
   UART_DEINIT_MACRO(3)
   UART_AVAILABLE_MACRO(3)
   UART_PEEK_MACRO(3)
   UART_READ_MACRO(3)
   UART_WRITE_MACRO(3)
   UART_FLUSH_MACRO(3)
   UART_RX_VECTOR(3)
   UART_TX_VECTOR(3)
#endif
