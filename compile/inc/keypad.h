/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

*/

#pragma once

typedef uint8_t KEYCODE;

void InitializeKeypad (void);
KEYCODE GetKey (void);
