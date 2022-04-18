import json
import os
import curses
import subprocess

import draw
import utils
import gfx_chars
from menu import menu, make_columns
from text_input import text_input
from __main__ import crumb, del_crumb, stdscr

config_file = 'config.json'
data = {}
defaults = {
   'port': '/dev/ttyACM0',
   'sd_card_device': '/dev/mmcblk0',
   'buildroot_version': 'buildroot-2021.08.13-pi2-tmp',
   'compiler_threads': 16,
   'compression_threads': 16,
   'verbose': False
}

def get (key, default = None):
   return data.get(key, default)

def load ():
   global data
   if not os.path.exists(f'./{config_file}'):
      data = dict(defaults)
      save()

   data = json.loads(open(f'./{config_file}', 'r').read())

   # Do we have all the settings?
   do_save = False
   for setting in defaults:
      if setting not in data:
         data[setting] = defaults[setting]
         do_save = True

   # Re-save?
   if do_save: save()

def save ():
   with open(f'./{config_file}', 'w') as f:
      f.write(json.dumps(data))

def do_config ():
   crumb('Configure this Program')
   ret = 0
   while True:
      ret = menu([
         ('-Setting                     Value'),
         (f'Programming Port            {data["port"]}', 'port'),
         (f'SD Card Device              {data["sd_card_device"]}', 'device'),
         (f'Buildroot Version           {data["buildroot_version"]}', 'buildroot'),
         (f'Compilation Threads         {data["compiler_threads"]}', 'threads'),
         (f'Image Compression Threads   {data["compression_threads"]}', 'comp_threads'),
         (f'Verbose avrdude Commands    {data["verbose"]}', 'verbose'),
         '-',
         (f'Back to Main Menu', 'quit')
      ], title = 'Options', pre_select = ret)

      if ret == 'quit' or ret == -1:
         break

      elif ret == 'port':
         new_port = do_port()
         if new_port is not None:
            data['port'] = new_port

      elif ret == 'device':
         new_device = do_device()
         if new_device is not None:
            data['sd_card_device'] = new_device

      elif ret == 'buildroot':
         choices = [make_columns((24, 14), ('-Version', 'Status'))]
         for ver in os.listdir('./buildroot'):
            text = ver.ljust(23)
            if ver == data['buildroot_version']:
               text += 'In Use'
            else:
               text += '-'
            choices.append((text, ver))
         sel = menu(choices, title = 'Buildroot Version')

         if sel != -1:
            data['buildroot_version'] = sel

      elif ret == 'verbose':
         data['verbose'] = not data['verbose']

      elif ret == 'threads':
         new_threads = text_input(
            prompt = 'How many threads should be used for compilation?',
            max_len = 2,
            match_range = (1, 64))

         if new_threads is not None:
            data['compiler_threads'] = int(new_threads)

      elif ret == 'comp_threads':
         new_threads = text_input(
            prompt = 'How many threads should be used for disk image compression?',
            max_len = 2,
            match_range = (1, 64))

         if new_threads is not None:
            data['compression_threads'] = int(new_threads)

   save()
   del_crumb()

def do_port ():
   all_ports = [(f'/dev/{n}', f'/dev/{n}') for n in os.listdir('/dev') if 'tty' in n]
   items = [
      ('Nevermind, go back.', 'quit'),
      '-'] + all_ports

   ret = menu(items, title = 'Select a Port')

   if ret == 'quit' or ret == -1:
      return None

   return ret

def do_device ():
   proc = subprocess.run(
      f'lsblk -Jpo KNAME,HOTPLUG,SUBSYSTEMS,VENDOR,MODEL,SIZE',
      shell = True,
      stdout = subprocess.PIPE)

   error_message = 'Something went wrong when scanning for devices.\n\nTalk to Steven'
   if proc.returncode != 0:
      draw.message(error_message + '.', colors = 10)
      return None

   try:
      data = json.loads(proc.stdout.decode('utf-8'))['blockdevices']
   except (KeyError, TypeError, ValueError, json.decoder.JSONDecodeError) as e:
      draw.message(error_message + f' and tell him this:\n\n{e}', colors = 10)
      return None

   # Filter the list down to only those that make sense
   devs = []
   for dev in data:
      if dev['hotplug'] == '1' or dev['hotplug'] == True:
         if 'usb' in dev['subsystems']:
            if dev['model'] is not None and any(model in dev['model'].lower() for model in ['sd', 'transcend']):
               devs.append(dev)

   sizes = (20, 20, 24, 12)
   align = ('ljust', 'ljust', 'ljust', 'rjust')
   cols  = ('Device File', 'Vendor', 'Model', 'Size')
   items = [('Nevermind, go back.', 'quit'), '-',
      make_columns(sizes, cols, align = align, header = True)]

   for dev in devs:
      kname = dev['kname']
      vendor = dev['vendor'] if dev['vendor'] else 'Unknown'
      model = dev['model'] if dev['model'] else 'Unknown'
      size = dev['size'] if dev['size'] else 'Unknown'
      items.append((make_columns(sizes, (kname, vendor, model, size), align = align), kname))

   while True:
      ret = menu(items, title = 'Select a Device')
      if isinstance(ret, str) and utils.is_root_device(ret):
         draw.message(('That\'s probably not a good option.\n'
            'It looks like it\'s part of your boot drive.'), colors = 10)
         continue
      break

   if ret == 'quit' or ret == -1:
      return None

   return ret
