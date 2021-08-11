#!/bin/bash

sudo apt install \
   lm-sensors \
   bzr \
   cvs \
   git \
   mercurial \
   rsync \
   subversion \
   vim \
   mc \
   build-essential \
   binutils \
   patch \
   perl \
   cpio \
   unzip \
   bc \
   curl \
   libncurses5-dev \
   bmon \
   xfonts-terminus \
   avrdude \
   cifs-utils \
   gcc-avr \
   avr-libc \
   srecord \
   htop \
   tmux \
   xinit \
   xserver-xorg \
   rxvt-unicode-256color

sudo cp -v /etc/sudoers /etc/sudoers.backup
echo 'all-line ALL=(ALL) NOPASSWD: /bin/mount, /bin/umount,/sbin/mkfs.vfat,/sbin/mkfs.ext2,/sbin/fdisk,/bin/dd,/bin/chown,/bin/chmod' | sudo tee -a /etc/sudoers
echo 'You will need to reboot. Just type "sudo reboot" and hit ENTER. Or else.'
