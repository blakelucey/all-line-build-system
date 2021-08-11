# All-Line Equipment Company

import os
import sys
import time
import re
import shutil
import subprocess
import shlex
import stat

from urllib import urlretrieve

from interprocess import RemoteHaltRequest
from utils import get_path
from pollsomething import Pollable
from logger import *
from eventlog import log_event

class FirmwareWatcher (Pollable):
   def __init__ (self, remote, ipc, display, link):
      self.remote = remote
      self.display = display
      self.ipc = ipc
      self.link = link

      # Update status
      self.is_updating = False
      self.status_text = ''

      self.ipc.add_handler('firmware_update', self.ipc_firmware_update)
      self.ipc.add_handler('firmware_update_status', self.ipc_firmware_update_status)
      self.ipc.add_handler('software_update', self.ipc_software_update)

      # Polling for USB update interruption
      Pollable.__init__(self, **{
         'poll_interval': 2.5
      })

   def get_file (self, src, dest, decrypt = False):
      '''Retrieves (or copies, if local) 'src' to 'dest', and decrypts if asked to do so.
      Returns (code, message), where code is True on success and message is 'dest' on success.'''

      # Does the destination already exist?
      if os.path.exists(dest):
         os.remove(dest)

      # Is this a remote file?
      if src.startswith('http://') or src.startswith('https://'):
         log_info('Downloading file {} to {}.'.format(src, dest))

         try:
            tempfile, _ = urlretrieve(src)
         except:
            return (False, 'File could not be downloaded.')

         with open(dest, 'wb') as f:
            f.write(open(tempfile, 'rb').read())

      else:
         # Local file; just copy it.
         log_info('Copying file: {} to {}.'.format(src, dest))

         try:
            shutil.copy(src, dest)
         except:
            return (False, 'File could not be copied.')

      # Looks OK so far.
      if not decrypt:
         return (True, dest)

      # Decrypt the file by moving it to a different name and decrypting into 'dest'.
      tempfile = dest + '.tmp'
      shutil.move(dest, tempfile)
      key = 'all-lineequipmentcompany'
      openssl_command = '"{binary}" {method} -pass \'pass:{key}\' -d -in "{infile}" -out "{outfile}"'
      openssl_command = openssl_command.format(**{
         'binary': 'openssl',
         'method': 'aes-256-cbc',
         'key': key,
         'infile': tempfile,
         'outfile': dest
      })

      ret = os.system(openssl_command)

      if ret != 0:
         return (False, 'File could not be decrypted.')

      return (True, dest)

   def is_valid_intel_hex_file (self, filename):
      '''Validates an Intel HEX file (.ihex, .hex) and returns True if it looks OK.'''
      try:
         fh = open(filename, 'rb')
      except (IOError, OSError, PermissionError):
         return False

      for line in fh:
         if not re.match('^:[0-9A-F]+$', line.strip()):
            fh.close()
            return False

      # Looks okay
      fh.close()
      return True

   def ipc_software_update (self, skt, data):
      '''Updates the system's web interface software using a remote file.'''

      if 'file' not in data:
         skt.error('Missing update file.')
         return

      src = data['file']
      dest = get_path('temp') + 'update.tar'
      result = self.get_file(src, dest, True)

      if not result[0]:
         skt.error(result[1])
         return

      # Reply ahead of time.
      skt.send({
         'reply_to': data['request_type'],
         'error': False
      })

      # The software update is very quick; we don't need to pause.
      # Simply update ourselves and restart the system.
      command = get_path('program') + 'update.sh "{}"'.format(dest)
      os.system(command)

      # Now run an install script, if one exists.
      install = get_path('program') + 'install.sh'
      exec_bits = (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

      log_debug('Checking for installation script at {}.'.format(install))
      if os.path.exists(install):
         log_debug('Found. Checking to see if it\'s executable.')
         perms = os.stat(install).st_mode

         # Is this executable?
         if (perms & exec_bits) != 0:
            # Yes; run it and clear the execute bit.
            log_debug('Installation script is executable.')
            log_info('Found an installation script. Running it now.')
            os.system(install)
            os.chmod(install, perms & ~exec_bits)
         else:
            log_debug('Installation script was not executable.')

      # Synchronize file systems.
      os.system('sync')

      # Wait for the HTTP request to complete; then reboot.
      # Handle IPC requests, more or less.

      now = time.time()
      self.ipc.busy([
         'firmware_update_status'
      ])

      while time.time() - now < 5.0:
         self.ipc.poll()
         time.sleep(0.05)

      # Log this.
      log_event('System', 'The web interface software was remotely updated.')

      # Raise a halt exception. Previously this just rebooted.
      raise RemoteHaltRequest()

      while True:
         time.sleep(1.0)

   def ipc_firmware_update (self, skt, data):
      '''Updates the mainboard firmware using a remote file.'''

      if 'file' not in data:
         skt.error('Missing update file.')
         return

      src = data['file']
      dest = get_path('temp') + 'fw.hex'
      result = self.get_file(src, dest, True)

      if not result[0]:
         skt.error(result[1])
         return

      # Validate the data itself.
      if not self.is_valid_intel_hex_file(dest):
         skt.error('Invalid firmware update file.')
         return

      # So far, so good. Report back.
      skt.send({
         'reply_to': data['request_type'],
         'error': False
      })

      # Try to apply the firmware update.
      # We temporarily take over from the main loop in main.py.
      # When things are done, or have gone terribly wrong, we return
      # control back to main.

      # Note that avrdude is passed -D. This skips a chip erase, which is not
      # supported by our STK500v2 implementation.

      self.is_updating = True
      exec_start = time.time()
      exec_timeout = 3.0 * 60.0
      log_file = get_path('temp') + 'avrdude.log'
      if os.path.exists(log_file):
         os.remove(log_file)
      command = 'avrdude -l {log} -c {tool} -P {port} -p {chip} -b {baud} -D -U flash:w:{dest} &'
      command = command.format(**{
         'log': get_path('temp') + 'avrdude.log',
         'tool': 'stk500v2',
         'port': self.link.port,
         'chip': 'atmega2560',
         'baud': 115200,
         'dest': dest,
      })

      # Reboot mode 2 is the network loader, which understands the STK500v2 protocol.
      self.remote.reboot(2)
      time.sleep(0.05)

      self.link.close()
      self.ipc.busy([
         'firmware_update_status'
      ])
      time.sleep(0.05)

      log_info('Executing command: {}'.format(command))
      os.system(command)

      # Wait for avrdude to finish, up to 3 minutes.
      while time.time() - exec_start < exec_timeout:
         # Is avrdude done?
         check = os.system('pidof avrdude > /dev/null')
         if check != 0:
            # It's no longer running.
            break

         # Grab the latest status text

         # Python will spit out billions of exceptions if the file
         # is empty because Python IO has no sensible error handling
         # other than exceptions. How about returning an empty string?
         # How about seeking past 0 seeks to 0?
         if os.path.exists(log_file):
            try:
               with open(log_file, 'rb') as f:
                  try:
                     f.seek(-1024, 2)
                  except IOError:
                     pass

                  try:
                     last_line = f.readlines()[-1].strip()
                     percent = last_line.count('#') / 49.0 * 100.0
                     task = 'read' if 'Reading' in last_line else 'write'
                     self.status_text = '{{"process": "{}", "percent": {:.1f}}}'.format(
                        task, percent
                     )
                  except IndexError:
                     self.status_text = '{"process": "write", "percent": 0.0}'
            except (IOError, OSError):
               self.status_text = '{"process": "write", "percent": 0.0}'
         else:
            self.status_text = '{"process": "write", "percent": 0.0}'

         # Handle IPC requests
         self.ipc.poll()

         # Pause briefly
         time.sleep(0.1)

      # Make sure avrdude is trashed.
      os.system('killall avrdude >/dev/null 2>&1')

      # Save this event.
      log_event('System', 'The firmware was remotely updated.')

      # Wait just a second for things to settle down.
      time.sleep(3.5)

      self.link.open()
      self.ipc.not_busy()
      self.is_updating = False

   def ipc_firmware_update_status (self, skt, data):
      skt.send({
         'reply_to': data['request_type'],
         'is_updating': self.is_updating,
         'status_text': self.status_text,
         'error': False
      })

   def action (self):
      usb_update = self.remote.get_param_value('Firmware Update Status')
      if usb_update:
         # The system is performing a USB update very shortly and won't be available
         # for a while.
         log_info('System is about to be busy for a while.')
         self.is_updating = True
         self.ipc.busy([
            'firmware_update_status'
         ])

         # 60 seconds should do just fine unless something awful happens.
         start = time.time()
         while time.time() - start < 60.0:
            self.ipc.poll()
            time.sleep(0.1)

         log_event('System', 'The firmware was locally updated via USB.')
         log_info('System is most likely no longer busy.')
         self.ipc.not_busy()
         self.is_updating = False

