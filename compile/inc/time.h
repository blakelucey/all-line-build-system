/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

*/

#pragma once

extern volatile uint32_t Milliseconds;

void InitializeTime (void);
volatile uint32_t Now (void);
