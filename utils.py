import subprocess
import os
import datetime
import curses
import time
import json
import shutil
import xml.etree.ElementTree as xml
import xml.dom.minidom as dom
import fnmatch

import config
import gfx_chars
import draw
from __main__ import stdscr

ramdisk = '/dev/shm'
storage_dir = '/mnt/storage'

def is_nas_available ():
   # Figure out if we're connected to the NAS.
   code = os.system(f'mount | grep "{storage_dir}" > /dev/null 2>&1')
   if code >> 8 != 0:
      return False

   # Okay, mount says it's there, but is it *really*?
   if not os.path.exists(f'{storage_dir}/Steven'):
      return False

   # Must be!
   return True

def get_device_size (dev):
   # Find out how big the device is.
   command = 'lsblk -bpo KNAME,SIZE -J'
   result = subprocess.run(command, stdout = subprocess.PIPE, shell = True)
   data = json.loads(result.stdout.decode('utf-8'))

   for d in data['blockdevices']:
      if d['kname'] == dev:
         return int(d['size'])

   return -1

def create_disk_image (dev, dest):
   cmd = f'sudo dd if={dev} bs=8M status=progress | xz -z -T {config.get("compression_threads")} -e -9 -c - > {dest}'
   size = get_device_size(dev)
   proc = subprocess.Popen(
      cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE, bufsize = 0)
   progress = bytearray()

   while True:
      ch = proc.stderr.read(1)
      if not ch: break
      progress += ch

      if ch == b'\r' or ch == b'\n':
         try:
            parts = progress.decode('utf-8').strip().split()
            written = int(parts[0])
            speed = parts[-2] + ' ' + parts[-1]
            percent = (written / size) * 100.0
            draw_progress(False, percent, border = True, add_text = f'; {format_size(written, space = True)} read at {speed}.')
            progress.clear()
         except (TypeError, ValueError, IndexError):
            pass

   draw_progress(False, 0, border = True, clear = True)

def restore_disk_image (filename, dev):
   pass

def is_root_device (dev):
   # Find the root device's real name
   text = open('/proc/cmdline', 'r').read()
   start = text.find('root=')
   end = text.find(' ', start)
   uuid = text[start+10:end].lower()

   command = 'lsblk -o KNAME,UUID -J'
   result = subprocess.run(command, stdout = subprocess.PIPE, shell = True)
   data = json.loads(result.stdout.decode('utf-8'))
   root_dev = None

   for device in data['blockdevices']:
      if device['uuid'] is not None and device['uuid'].lower() == uuid:
         # This is the root device.
         root_dev = device['kname']
         break

   if root_dev is not None:
      # Ditch the number on the end.
      root_dev = root_dev[:-1]

      if root_dev in dev:
         # It's the root device or another device on the same disk.
         return True

   # Probably not a root device.
   return False

def add_child (parent, tag, data = None, attrs = None):
   sub = xml.SubElement(parent, tag)

   if data is not None:
      if not isinstance(data, str): data = str(data)
      sub.text = data

   if attrs:
      for name, value in attrs.items():
         sub.set(name, value)

   return sub

def save_xml (node, dest):
   rough = xml.tostring(node)

   try:
      reparse = dom.parseString(rough)
      pretty = reparse.toprettyxml(indent = (' ' * 3))
   except (TypeError, ValueError, xml.ParseError):
      pretty = rough

   try:
      with open(dest, 'w') as f:
         f.write(pretty)
      return True
   except (IOError, OSError, PermissionError):
      return False

def format_size (num, suffix = 'B', space = False):
   space = ' ' if space else ''
   for unit in ['','K','M','G','T','P','E','Z']:
      if abs(num) < 1024.0:
         return "%3.1f%s%s%s" % (num, space, unit, suffix)
      num /= 1024.0
   return "%.1f%s%s%s" % (num, space, 'Y', suffix)

def copy_tree (src, dst, ignore = None, callback = None):
   if not os.path.exists(src):
      raise FileNotFoundError(f'{src} does not exist.')

   if not os.path.exists(dst):
      os.mkdir(dst)

   for f in os.scandir(src):
      skip = False
      
      if ignore is not None:
         for item in ignore:
            if fnmatch.fnmatch(f.name, item):
               skip = True

      if skip: continue

      if f.is_dir():
         copy_tree(f.path, dst.rstrip('/') + '/' + f.name)
      else:
         if callable(callback):
            callback(f.path, dst.rstrip('/') + '/' + f.name)
         shutil.copy(f.path, dst.rstrip('/') + '/' + f.name)

def sub_find_files (data, where, name, compare):
   # Only decide the comparison type once.
   if not callable(compare):
      if compare is None: 
         compare = lambda x: x.lower() == name.lower()
      elif compare == 'endswith': 
         compare = lambda x: x.lower().endswith(name.lower())
      elif compare == 'startswith':
         compare = lambda x: x.lower().startswith(name.lower())
      elif compare == 'contains':
         compare = lambda x: x.lower() in name.lower()

   if not os.path.isdir(where): return

   for entry in os.scandir(where):
      # Did we find a subdirectory to scan?
      if entry.is_dir():
         sub_find_files(data, entry.path, name, compare)

      elif compare(entry.name):
         stat = entry.stat()
         data.append({
            'name': entry.name,
            'path': entry.path,
            'dir': where,
            'size': stat.st_size,
            'size_str': format_size(stat.st_size),
            'date': datetime.datetime.fromtimestamp(stat.st_mtime),
            'timestamp': stat.st_mtime,
            'is_debounce': 'debounce' in entry.path.lower(),
            'is_bootloader': 'bootloader' in entry.path.lower(),
            'is_main': not any(('debounce' in where.lower(), 'bootloader' in where.lower())),
            'is_header': entry.path.endswith('.h')
         })

def find_files (where, name, compare = None):
   data = []
   sub_find_files(data, where, name, compare)
   return data

def combine_hexes (one, two, out = None):
   try:
      if out is None: out = f'{ramdisk}/combined.hex'

      if os.path.exists(out):
         os.remove(out)

      result = subprocess.run(
         f'srec_cat "{one}" -I "{two}" -I -o "{out}" -I',
         shell = True, 
         stdout = subprocess.DEVNULL,
         stderr = subprocess.DEVNULL)
      
      return (result.returncode == 0, out)
   except (IOError, OSError, PermissionError):
      return False

def draw_progress (is_write, percent, clear = False, border = True, places = 1, add_text = None):
   # Used by avrdude_command below to draw a default progress bar.
   if add_text is None: add_text = ''
   width = curses.COLS - 30
   col = curses.COLS // 2 - width // 2
   row = curses.LINES - 10

   # Clear the bar?
   if clear:
      if border: 
         width += 4
         col -= 2
         stdscr.addstr(row - 1, col, ' ' * width)
         stdscr.addstr(row + 2, col, ' ' * width)
      stdscr.addstr(row, col, ' ' * width)
      stdscr.addstr(row + 1, col, ' ' * width)
      stdscr.refresh()
      return

   # Just draw to stdscr; we'll be out of everyone's way.
   if border:
      draw.border(stdscr, row - 1, col - 2, width + 4, 4, colors = 4)

   stdscr.addstr(
      row, col,
      (f'Writing to device ({percent:.{places}f}%)' if is_write else f'Reading from device ({percent:.{places}f}%)') + add_text,
      curses.color_pair(4))

   blocks = int((percent / 100.0) * width)
   non_blocks = width - blocks

   stdscr.addstr(
      row + 1, col,
      blocks * gfx_chars.block,
      curses.color_pair(6) | curses.A_BOLD)

   stdscr.addstr(
      row + 1, col + blocks,
      non_blocks * ' ',
      curses.color_pair(6))

   stdscr.refresh()

def avrdude_command (device, target, data, run = False, speed = None, progress = True):
   # Craft an avrdude command that will program 'target' with
   # 'data'. If 'fuse' is in the target, handle that specially.

   logfile = f'{ramdisk}/avrdude.log'

   if target is None:
      # Likely a connectivity check.
      target = ''
      speed = '-B 128'
   elif 'fuse' in target:
      # Disable verification/safe mode to work around a bug in avrdude.
      data = int(data)
      target = f'-s -V -U {target}:w:0x{data:02X}:m'
      speed = '-B 128'
   else:
      target = f'-U {target}:w:{data}:i'
      speed = '-B 0.1' if speed is None else f'-B {speed}'

   import config
   port = config.data['port']
   command = f'avrdude -c stk500v2 -P {port} -p {device} {speed} {target}'

   if config.data['verbose']:
      result = draw.question('AVRdude command:\n\n' + command + '\n\nRun it?', default = 0, escape = 1)
      if result == 'N':
         return 0

   # Run it?
   if run:
      # Redirect stdout since avrdude uses stderr
      command = f'{command}'

      if not progress:
         # Just run it. No need to mess around.
         result = subprocess.run(
            command, shell = True,
            stdout = subprocess.DEVNULL,
            stderr = subprocess.DEVNULL)
         return result.returncode

      # They want to get progress feedback. We can do this by calling 'progress',
      # if it's callable, for each percentage change. If it's just True, draw our
      # own progress bar slightly lower than screen center.

      proc = subprocess.Popen(
         command, shell = True, 
         stdout = subprocess.PIPE, stderr = subprocess.PIPE,
         bufsize = 0)

      state_detect = bytearray()
      ok = False
      in_read = False
      in_write = False
      read_pct = 0
      write_pct = 0

      while True:
         ch = proc.stderr.read(1)
         if not ch: break

         # Store the last 20 characters we've read.
         state_detect += ch
         if len(state_detect) > 20:
            state_detect = state_detect[1:]

         # Have we passed the device signature stuff?
         if 'Device signature'.encode('ascii') in state_detect:
            ok = True

         if not ok: continue

         # We have. Detect a read or write.
         if 'Reading |'.encode('ascii') in state_detect:
            in_read = True
            in_write = False

         if 'Writing |'.encode('ascii') in state_detect:
            in_write = True
            in_read = False

         if in_read and ch == b'#':
            read_pct += 2
            if callable(progress):
               progress(False, read_pct)
            elif progress:
               draw_progress(False, read_pct)

         if in_write and ch == b'#':
            write_pct += 2
            if callable(progress):
               progress(True, write_pct)
            elif progress:
               draw_progress(True, write_pct)

      # end while
      proc.wait()

      # Clear the progress bar area if we need to.
      if not callable(progress) and progress:
         draw_progress(False, 0, clear = True)

      return 0 # TODO: proc.returncode

   # We didn't run it; maybe someone else will.
   return command

def trace_exception ():
   except_path = './exceptions'
   if not os.path.exists(except_path):
      os.mkdir(except_path)

   import traceback
   filename = datetime.datetime.now().strftime(f'{except_path}/%Y-%m-%d_%H-%M-%S.txt')
   text = traceback.format_exc()
   with open(filename, 'w') as f:
      f.write(text)
   
   text = f'\nThis text has been saved to disk.\nTell Steven about this.\n\n' + \
      gfx_chars.hline_thin * 80 + '\n\n' + text

   draw.viewer(text, 27, 84, colors = 10, attrs = curses.A_BOLD, title = 'Something Went Wrong!')

def avrdude_connect (device, message = None, allow_skip = False):
   choices = ('&OK', '&Cancel', '&Skip')

   if message:
      result = draw.question(message, choices = choices, default = 0, escape = 1)
      if result == 'C':
         return False
      if result == 'S':
         return 'skip'

   while True:
      # Check for the programmer.
      draw.begin_wait('Checking for programmer...')
      time.sleep(0.8)
      draw.end_wait()

      if not os.path.exists(config.data['port']):
         result = draw.question((
            f'No programmer was found at {config.data["port"]}.\n'
            '\n'
            'Search again?'),
            title = 'Missing Programmer')

         if result == 'N':
            return False

      else:
         # The programmer exists.
         break

   while True:
      draw.begin_wait('Checking for CPU...')
      time.sleep(0.8)
      ret = avrdude_command(device, None, None, run = True, progress = False)
      draw.end_wait()

      if ret != 0:
         result = draw.question((
            f'Unable to communicate with CPU ({device}).'
            '\n'
            'Try again?'),
            title = 'No Communication')

         if result == 'N':
            return False

      else:
         # Looks OK.
         break

   # All OK.
   return True

