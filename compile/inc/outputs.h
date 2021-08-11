/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

*/

#pragma once

#include "common.h"

#define NUM_OUTPUTS  8
#define NUM_ALARMS   2

void InitializeOutputs (void);
void SetOutput (uint8_t id, uint8_t state);
uint8_t GetOutput (uint8_t id);
void SetAlarmOutput (uint8_t id, uint8_t state);
uint8_t GetAlarmOutput (uint8_t id);
