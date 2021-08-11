/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

*/

#pragma once

#define USE_UART_0
//#define USE_UART_1
//#define USE_UART_2
#define USE_UART_3

#define NO_PARITY       0
#define EVEN_PARITY     1
#define ODD_PARITY      2

#define ONE_STOP_BIT    0
#define TWO_STOP_BITS   1

#define UART_PROTOTYPES(n) \
   void InitializeUart##n (uint32_t baud_rate, uint8_t data_bits, uint8_t parity, uint8_t stop_bits); \
   void DeInitializeUart##n (void); \
   int16_t Uart##n##Available (void); \
   int16_t Uart##n##Peek (void); \
   int16_t Uart##n##Read (void); \
   void Uart##n##Write (uint8_t data); \
   void Uart##n##Flush (void);

#ifdef USE_UART_0
UART_PROTOTYPES(0)
#endif

#ifdef USE_UART_1
UART_PROTOTYPES(1)
#endif

#ifdef USE_UART_2
UART_PROTOTYPES(2)
#endif

#ifdef USE_UART_3
UART_PROTOTYPES(3)
#endif
