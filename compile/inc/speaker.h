/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

*/

#pragma once

#define BEEP_FREQ    1500
#define BEEP_DUR     85

#define ERROR_FREQ   2250
#define ERROR_DUR    200

void InitializeSpeaker (void);
void Beep (void);
void Silence (void);
void Play (uint16_t freq, uint16_t dur);
void ErrorBeep (void); 
void Click (void);
