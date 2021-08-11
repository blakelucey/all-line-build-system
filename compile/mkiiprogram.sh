#!/bin/sh

RELEASE=Debug

if [ "$1" == "fuses" ]; then
   avrdude -c avrispmkii -P usb -p atmega640 -B 128 -U lfuse:w:0xff:m -U hfuse:w:0xd0:m -U efuse:w:0xf6:m
else
   avrdude -c avrispmkii -P usb -p atmega640 -B 1 -U flash:w:$RELEASE/new_fb_io_controller.hex
fi
