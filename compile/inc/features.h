/*

All-Line Equipment Company
Fuel Boss I/O Controller Firmware

Copyright (C) 2011-2017 All-Line Equipment Company

Optional Feature Support

*/

#pragma once

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
//                                FEATURE SELECTION
// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

// Use this to spit out some debugging information over the RS-232 port.
//#define LOGGING

// Tank gauge support will provide analog readings for up to 8 tank gauges
// via a connected gauge/DFM adapter board.
#define CAP_TANK_GAUGES

// DFM board support is required for tank gauges.
#define CAP_DFM

// DFM reading will provide DFM record caching and reporting via a connected
// gauge/DFM adapter board.
//#define CAP_DFM_READING

// Magnetic card support will provide support for a single magnetic card
// reader (OPW/K800 type or Brush type) attached to the "MAG CARD" port on
// the mainboard.
#define CAP_MAGNETIC_CARD
#define MAGCARD_BRUSH
//#define MAGCARD_MAGTEK

// HID card support will provide support for either one or two HID card
// readers using the 26-bit Wiegand protocol on the "MAG CARD" port on the
// mainboard.
//#define CAP_HID_CARD
//#define CAP_HID_CARD_2

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
//                                DO NOT EDIT BELOW
// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

#if defined(CAPBIT_MAGNETIC_CARD) && (defined(CAP_HID_CARD) || defined(CAPBIT_HID_CARD_2))
#error Magnetic card reader cannot be used simultaneously with an HID card reader.
#endif

#if defined(CAP_TANK_GAUGES) && !defined(CAP_DFM)
#error DFM adapter board support is required for analog tank gauges.
#endif

#if defined(LOGGING)
#warning ***** Debug logging via RS-232 is ENABLED. DO NOT SHIP THIS SYSTEM WITH THIS ENABLED!!! *****
#endif

#if defined(CAP_MAGNETIC_CARD)
#  if defined(MAGCARD_MAGTEK) && defined(MAGCARD_BRUSH)
#     error Magnetic card reader must be a Magtek or Brush, but not both.
#  elif !defined(MAGCARD_MAGTEK) && !defined(MAGCARD_BRUSH)
#     error Magnetic card reader must be a Magtek or Brush, but not neither.
#  endif
#endif

// These are the actual capability bits that we report to an attached Fuel Boss
// controller board.
#define CAPBIT_MAGNETIC_CARD   0x01
#define CAPBIT_HID_CARD        0x02
#define CAPBIT_DFM             0x04
#define CAPBIT_HID_CARD_2      0x08
#define CAPBIT_TANK_GAUGES     0x10
#define CAPBIT_DFM_READING     0x20
#define CAPBIT_RESERVED_2      0x40
#define CAPBIT_RESERVED_3      0x80

// This is used to get a mask of all of our capabilities.
uint8_t GetCapabilityBits (void);