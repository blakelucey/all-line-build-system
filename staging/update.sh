#!/bin/sh

HOST=192.168.1.10
TARBALL=files/update.tar
URL=http://$HOST/$TARBALL
TEMP=/dev/shm/update.tar
DEST=/program
MOUNTRO=
POSTUPDATE=$DEST/post-update.py
POSTUPDATEC=$DEST/post-update.pyc

# Use a different URL?
[ ! -z "$1" ] && URL="$1"

# Is this a direct file reference?
if [ "${URL:0:1}" == "/" ]; then
   # This is the file we want
   TEMP=$URL
   NODL=1
else
   # Remove the previous update file
   rm -f "$TEMP"
   NODL=
fi

# Check for a read-only program partition.
if mount | grep -E 'program.+\(ro' > /dev/null ; then
   echo -n "Remounting $DEST read-write... "
   mount -o remount,rw $DEST >/dev/null 2>&1
   echo OK
   MOUNTRO=1
fi

if [ -z "$NODL" ]; then
   echo -n 'Downloading update... '
   if ! wget -q $URL -O $TEMP > /dev/null; then
      echo 'error!'
      exit 1
   fi
   echo "got $(du -k $TEMP | cut -f 1) KB."
else
   echo 'Update file is local; skipping download.'
fi

echo -n 'Unpacking... '
COUNT=$(tar xvf $TEMP -C $DEST | wc -l)
echo OK, unpacked $COUNT files.
echo -n 'Modifying ownership... '
chown -R root:root $DEST/*
echo OK
echo -n 'Changing permissions... '
chmod -R 755 $DEST/*
echo OK
echo -n 'Syncing file systems... '
sync
echo OK

if [ -x "$POSTUPDATE" ]; then
   python -B $POSTUPDATE
else
   if [ -x "$POSTUPDATEC" ]; then
      python $POSTUPDATEC
   fi
fi

if [ ! -z "$MOUNTRO" ]; then
   echo -n "Remounting $DEST read-only... "
   mount -o remount,ro $DEST >/dev/null 2>&1
   echo OK
fi

echo "Done!"

