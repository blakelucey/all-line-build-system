/*

   All-Line Equipment Company
   Fuel Boss I/O Controller Firmware

   Copyright (C) 2011-2017 All-Line Equipment Company

*/

#pragma once

#include "common.h"

#define BEGIN_ARGS()
#define END_ARGS()

#define CMD_READ_HANDLE          0x01
#define CMD_READ_PULSES          0x02
#define CMD_READ_CLOCK           0x03
#define CMD_READ_TICKS           0x04
#define CMD_READ_KEY             0x05
#define CMD_PLAY_SOUND           0x06
#define CMD_SILENCE              0x07
#define CMD_BEEP                 0x08
#define CMD_SET_OUTPUT           0x09
#define CMD_GET_OUTPUT           0x45
#define CMD_SET_LEDS             0x1F
#define CMD_CLEAR_PULSES         0x44
#define CMD_SET_DEBOUNCE         0x70
#define CMD_GET_DEBOUNCE         0x71
#define CMD_SET_ALARM            0x46
#define CMD_GET_ALARM            0x47
#define CMD_GET_SENSOR           0x53

// Graphics commands
#define CMD_GFX_CLEAR            0x10
#define CMD_GFX_REFRESH          0x11
#define CMD_GFX_HLINE            0x12
#define CMD_GFX_VLINE            0x13
#define CMD_GFX_LINE             0x14
#define CMD_GFX_RECT             0x15
#define CMD_GFX_FILLRECT         0x16
#define CMD_GFX_CLEARROW         0x48
#define CMD_GFX_CLEARROWSEG      0x52
#define CMD_GFX_INVROWSEG        0x49
#define CMD_GFX_INVRECT          0x17
#define CMD_GFX_INVROW           0x18
#define CMD_GFX_DRAWBITMAP       0x19
#define CMD_GFX_DRAWTEXT         0x1A
#define CMD_GFX_SIZETEXT         0x1B
#define CMD_GFX_CENTERTEXT       0x1C
#define CMD_GFX_RIGHTTEXT        0x1D
#define CMD_GFX_SETPIXEL         0x1E
#define CMD_GFX_DOTTEDHLINE      0x20
#define CMD_GFX_DOTTEDVLINE      0x21
#define CMD_GFX_SAVE             0x22
#define CMD_GFX_LOAD             0x23
#define CMD_GFX_SAVESERIAL       0x50
#define CMD_GFX_LOADSERIAL       0x51
#define CMD_GFX_SETBRIGHT        0x24
#define CMD_GFX_SETBRIGHTEX      0x25

#define CMD_NVRAM_READ           0x30
#define CMD_NVRAM_WRITE          0x31

#define CMD_CARD_DETECT          0x40
#define CMD_CARD_DATA            0x41
#define CMD_CARD_RESET           0x42

#define CMD_SYNC                 0x5A
#define CMD_GET_CAPABILITIES     0x56
#define CMD_GET_ERRORS           0x57

#define CMD_DFM_TRANSFER         0x60
#define CMD_DFM_TRANSFER_BYTE_2  0x55
#define CMD_DFM_TRANSFER_STOP    0xFB
#define CMD_GET_GAUGE_READING    0x62

#define CMD_INVOKE_DFM_BOOT      0x63

void InitializeCommands (void);
void CheckForCommand (void);
