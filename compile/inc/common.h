/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

   Common Header File

*/

#pragma once

#include <avr/io.h>
#include <avr/interrupt.h>
#include <avr/pgmspace.h>
#include <util/delay.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdarg.h>
#include <string.h>
#include <stdio.h>
#include "features.h"

#ifndef TRUE
#define TRUE 1
#define FALSE 0
#endif

#ifndef true
#define true 1
#define false 0
#endif

// String-in-ROM macro
#define F PSTR

// Maximum buffered string size
#define MAX_STRING_SIZE    128
#define MAX_STRING_LEN     127

// Byte reader and writer functions.
typedef uint8_t (*BYTE_READER) (uint8_t *dest);
typedef void (*BYTE_WRITER) (uint8_t byte);
