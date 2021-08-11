/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

*/

#pragma once

#include "common.h"

#define NUM_HANDLES  8
#define NUM_SENSORS  4

#define HANDLE_0  0
#define HANDLE_1  1
#define HANDLE_2  2
#define HANDLE_3  3
#define HANDLE_4  4
#define HANDLE_5  5
#define HANDLE_6  6
#define HANDLE_7  7

#define SENSOR_0  0
#define SENSOR_1  1
#define SENSOR_2  2

#define DIGITAL_SENSOR  0
#define ANALOG_SENSOR   1

void InitializeInputs (void);
void SetSensorType (uint8_t id, uint8_t type);
uint8_t GetSensorType (uint8_t id);
uint16_t GetSensorReading (uint8_t id);
uint8_t GetSensorState (uint8_t id);
uint8_t GetHandleState (uint8_t id);

