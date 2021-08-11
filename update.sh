#!/bin/sh

src="http://192.168.1.92/~steven/files/update.tar.gz"
dest="/dev/shm/update.tar.gz"
progdir="/home/all-line/build-master"
conf="$progdir/config.json"
conftemp="/dev/shm/config.json"

# Copy the config file somewhere else, remove the program data,
# and then put the config file back.
cp -v "$conf" "$conftemp"
rm -vfr "$progdir/*"
cp -v "$conftemp" "$conf"

# Download the update file.
[ -f "$dest" ] && rm -v "$dest"
wget -O "$dest" "$src" || {
   echo 'Something went wrong downloading the update.'
   exit 1
}

# Unpack it.
tar xvzf "$dest" -C "$progdir"
