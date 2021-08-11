/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

*/

#include "log.h"
#include "uart.h"

#ifdef LOGGING

#define LOG_BAUD 115200

static int LogPut (char ch, FILE *fp)
{
   Uart0Write(ch);
   return 1;
}

FILE LogFile = FDEV_SETUP_STREAM(LogPut, NULL, _FDEV_SETUP_WRITE);

void PrintP (const char *str)
{
   char ch;
   while ((ch = pgm_read_byte_far(str))) {
      Uart0Write(ch);
      str++;
   }
}

void PrintC (char ch)
{
   Uart0Write(ch);
}

void PrintF (const char *fmt, ...)
{
   va_list args;
   va_start(args, fmt);
   vfprintf_P(&LogFile, fmt, args);
   va_end(args);
}

void InitializeLog (void)
{
   InitializeUart0(LOG_BAUD, 8, NO_PARITY, ONE_STOP_BIT);

   LOG("Logging started.");
}

#endif // if defined LOGGING

