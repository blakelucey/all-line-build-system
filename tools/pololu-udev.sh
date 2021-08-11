#!/bin/bash

sudo cp -v 99-pololu.rules /etc/udev/rules.d
sudo udevadm control --reload

