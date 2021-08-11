/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

   Card Reader Functionality

*/

#pragma once

#include "common.h"

// If we're using HID, dual HID, or magnetic cards, these functions are linked
// to hidcard.c or magcard.c.

#if defined(CAP_MAGNETIC_CARD) || defined(CAP_HID_CARD) || defined(CAP_HID_CARD_2)

void InitializeCard (void);
uint8_t IsCardDataAvailable (void);
uint8_t IsCardError (void);
void SendCardData (BYTE_WRITER writer);
void ResetCardReader (void);
int16_t GetHidFacility (void);
int16_t GetHidNumber (void);
int16_t CopyCardData (char *dest);
void CopyCardDataAsText (char *dest);

// Otherwise, these functions are silently removed.
#else

#define InitializeCard() do { } while (0)
#define IsCardDataAvailable() (false)
#define IsCardError() (false)
#define SendCardData(...) do { } while (0)
#define ResetCardReader() do { } while (0)
#define GetHidFacility() (0)
#define GetHidNumber() (0)

#endif // CAP_MAGNETIC_CARD || CAP_HID_CARD || CAP_HID_CARD_2
