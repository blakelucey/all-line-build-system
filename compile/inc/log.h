/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

*/

#pragma once

#include "common.h"

extern FILE LogFile;

#ifdef LOGGING
void InitializeLog (void);
void PrintF (const char *fmt, ...);
void PrintP (const char *str);
void PrintC (char ch);

#define LOG(fmt, ...) do { \
   PrintF(F(fmt), ##__VA_ARGS__); \
   PrintF(F("\r\n")); \
} while (0)

#else // !LOGGING
#define InitializeLog(...)
#define PrintF(...)
#define PrintP(...)
#define PrintC(...)
#define LOG(...)
#endif
