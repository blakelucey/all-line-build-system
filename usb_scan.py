# This scans for any attached USB mass storage devices.

import subprocess
import os
import json
import time

from menu import menu
from __main__ import stdscr
import draw

mount_dir = '/dev/shm/usb_device'

def is_mounted (dev):
   command = f'mount | grep "{dev}" > /dev/null'
   result = subprocess.run(command, shell = True)
   return result.returncode == 0

def mount_device (dev):
   if is_mounted(dev):
      return True

   command = f'sudo mount -t vfat "{dev}" "{mount_dir}" -o uid=1000,gid=1000,rw,sync > /dev/null'
   if not os.path.exists(mount_dir):
      os.mkdir(mount_dir)

   result = subprocess.run(command, shell = True)
   return result.returncode == 0

def unmount_device (dev):
   if not is_mounted(dev):
      return True

   os.system('sync')

   command = f'sudo umount "{dev}" > /dev/null'
   result = subprocess.run(command, shell = True)
   return result.returncode == 0

def find_devices ():
   # Ask lsblk for some fancy JSON output.
   try:
      command = 'lsblk -o NAME,FSTYPE,HOTPLUG,LABEL,TYPE,SUBSYSTEMS,SIZE -J'
      result = subprocess.run(command, stdout = subprocess.PIPE, shell = True)
      text = result.stdout.decode('utf-8')
      data = json.loads(text)
   except (ValueError, AttributeError):
      # Return an error; we couldn't get device information.
      return None

   out = []
   for dev in data['blockdevices']:
      # Is this very likely a USB device?
      if dev['type'] == 'disk' and dev['hotplug'] in ('1', True) and 'usb' in dev['subsystems']:
         # It is.
         dev['device'] = f'/dev/{dev["name"]}'
         out.append(dev)

   return out

def select_device (can_skip = True, narrow_selection = True):
   def rescan ():
      draw.begin_wait('Scanning for USB devices...')
      time.sleep(0.5)
      devs = find_devices()
      draw.end_wait()

      items = [('Rescan USB Devices', 'rescan')]
      if can_skip:
         items.append(('Skip Writing Flash Drive', 'skip'))

      items.append('-')

      if devs is None or not len(devs):
         items.append(('No devices were found.', ''))
      else:
         items.append('-Device Name'.ljust(27) + 'Size'.ljust(16) + 'Label'.ljust(20))
         for dev in devs:
            label = dev['label']
            if not label or not len(label):
               # Empty label.
               label = '(No Label)'

            name = f'Device /dev/{dev["name"]}'.ljust(26)
            size = dev['size'].ljust(16)
            items.append((name + size + label, f'/dev/{dev["name"]}'))

      return (items, devs)

   menu_items, devs = rescan()
   while True:
      # Narrow the selection down to just a single device?
      if narrow_selection and len(devs) == 1:
         return devs[0]['device']

      try:
         sel = menu(menu_items, title = 'Select a USB Device')
      except IndexError:
         import pprint
         raise RuntimeError(pprint.pformat(menu_items))

      if sel == 'quit' or sel == -1:
         # They bailed.
         return False

      elif sel == 'skip':
         # They said to skip.
         return True

      elif sel == 'rescan':
         menu_items, devs = rescan()

      elif sel.startswith('/dev'):
         # They picked an item.
         return sel

