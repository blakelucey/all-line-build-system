/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

*/

#pragma once

#include "common.h"

#define NUM_GAUGES 8

#ifdef CAP_DFM

#define DFM_RECORD_SIZE 32

void InitializeDfmAdapter (void);
void BeginDfmTransfer (void);
void EndDfmTransfer (void);
void DoDfmTransfer (void);
int16_t GetGaugeReading (uint8_t id);
void InvokeDfmAdapterBootloader (void);

#else

// Dummy initialization.
#define InitializeDfmAdapter()
#define GetGaugeReading(n) (int16_t)(0)

#endif
