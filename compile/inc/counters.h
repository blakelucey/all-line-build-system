/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

*/

#pragma once

#include "common.h"

#define NUM_COUNTERS 8

typedef uint32_t COUNTER;

void InitializeCounters (void);
void SyncWithCounterChip (void);
void SetCounterDebounce (uint8_t id, uint8_t periods);
uint8_t GetCounterDebounce (uint8_t id);
void ClearCounter (uint8_t id);
COUNTER GetCounter (uint8_t id);
