import os
import shutil
import datetime
import subprocess
import curses
import time

import config
import draw
import utils
import programmer
import compiler
import usb_scan
from menu import menu, make_columns
from text_input import text_input
from __main__ import crumb, del_crumb, stdscr

from logger import log_debug
# These reference the most common systems we make.
# If those systems have their software updated, these references may need
# to change.

injector_data = './data/injector'
default_fuses = {
   'hfuse': '0xD0',
   'lfuse': '0xFF',
   'efuse': '0xF5'
}

left_col = 22
predefined = [
   {'name': 'Single Injector', 'model': 'TM-1M1A-RT', 'id': 'single', 'serial': 'A1001576'},
   {'name': 'Double Injector', 'model': 'TM-1M2A-RT', 'id': 'double', 'serial': 'A1001649'},
   {'name': 'Triple Injector', 'model': 'TM-2M1A1M1A-RT', 'id': 'triple', 'serial': 'A1001635'},
   {'name': 'Brown\'s Oil', 'model': 'TM-2M1A-RTSBDS', 'id': 'browns', 'serial': 'A1001548'},
   {'name': 'Jugfill Only (2 Lanes)', 'model': 'BP-2A-PRESET', 'id': 'jugfill', 'serial': 'A1001652'},
   #{'name': '4-point Transport', 'model': 'TM-1A4P', 'id': '4pt', 'serial': 'A1001567'},
   #{'name': '5-point Transport', 'model': 'TM-1A5P', 'id': '5pt', 'serial': 'A1001567'},
   #{'name': '6-point Transport', 'model': 'TM-1A6P', 'id': '6pt', 'serial': 'A1001567'},
   #{'name': '6-point Hybrid', 'model': 'TM-1M1A6P', 'id': 'hybrid', 'serial': 'A1001567'}
]

class InjectorProgrammer:
   def __init__ (self, serial, custom_title = None):
      self.serial = serial
      self.path = f'{injector_data}/{serial}'
      self.version_path = None
      self.desc_file = f'{self.path}/desc.txt'
      self.title = custom_title if custom_title else f'Viewing {serial}'
      self.main_fuses = (0xFF, 0xD0, 0xFC)
      self.debounce_fuses = (0xFF, 0xD0, 0xFC)
      self.main_hex = None
      self.debounce_hex = None
      self.boot_hex = None
      self.main_files = None
      self.debounce_files = None
      self.boot_files = None
      self.vdip_firmware = './data/vdip/ftrfb.ftd'

   def edit_header_file (self, defs):
      sizes = (28, 30, 40, 20, 9)
      cols  = ('Symbol', 'Args', 'Value', 'Type', 'Line No.')
      align = (None, None, None, None, 'rjust')

      crumb(os.path.basename(defs.filename))

      # Create a copy of the original data
      originals = defs.items[:]

      while True:
         menu_items = [
            ('I\'m done making changes.', 'ok'), 
            ('Cancel changes and go back.', 'quit'),
            '-',
            make_columns(sizes, cols, align = align, header = True)
         ]

         for item in defs.items:
            sym = item['symbol']
            if item['is_define']:
               if not len(item['value']):
                  value = 'True'
               else:
                  value = item['value'].lstrip()
            else:
               value = 'N/A'

            args = item['args'] if len(item['args']) else 'None'

            kind = ('#define' if item['is_define'] else '#undef')
            if item['comment']: kind += ' (Disabled)'
            line_no = str(int(item['line_no']))

            item_cols = (sym, args, value, kind, line_no)
            menu_items.append((
               make_columns(sizes, item_cols, align = align),
               item))

         ret = menu(menu_items)

         if ret == -1 or ret == 'quit':
            defs.items.clear()
            defs.items = originals[:]
            break

         elif ret == 'ok':
            defs.save()
            break

         elif isinstance(ret, dict):
            while True:
               edited_line = defs.get_single_line(ret)

               message = (
                  'Current line:\n'
                  f'{edited_line}\n\n'
                  'Press C to comment/uncomment this statement.\n'
                  'Press D to turn a #define into an #undef, or vice versa.\n'
                  'Press E to edit a symbol\'s value.\n'
                  '\n'
                  'Press ENTER when finished.')

               result = draw.question(
                  message, choices = ('(Un)&Comment', '(Un)&Define', '&Edit Value', '&Return'),
                  choice_w = 18,
                  default = 3, center = False,
                  title = f'Modify Symbol {ret["symbol"]}')

               if result == 'C':
                  ret['comment'] = not ret['comment']
               elif result == 'D':
                  if ret['is_undef']:
                     ret['is_undef'] = False
                     ret['is_define'] = True
                  elif ret['is_define']:
                     ret['is_undef'] = True
                     ret['is_define'] = False
               elif result == 'E' and ret['is_define']:
                  new_value = text_input(
                     ret['value'], title = f'New Value for ret["symbol"]',
                     prompt = 'Enter a value for this symbol, or leave blank:')

                  if new_value is not None:
                     ret['value'] = new_value
               elif result == 'R':
                  break
      
      del_crumb()

   def edit_header_files (self):
      crumb('Advanced Compile')

      while True:
         draw.begin_wait('Loading data...')

         # Get all possible header definitions
         all_defs = {}
         header_files = utils.find_files(f'./compile', '.h', 'endswith')
         for header in header_files:
            defs = compiler.DefinitionEditor(header['path'])
            all_defs[defs.filename] = defs

         draw.end_wait()

         sizes = (74, 24)
         items = [
            ('I\'m ready to compile this software.', 'quit'), 
            '-',
            '-File Path'.ljust(sizes[0] + 1) + 'Number of Definitions'.rjust(sizes[1])]

         for filename, defs in all_defs.items():
            items.append((filename.ljust(sizes[0]) + str(len(defs.items)).rjust(sizes[1]), defs))

         ret = menu(items, title = 'All Source Code Definitions')

         if ret == 'quit' or ret == -1:
            break

         elif isinstance(ret, compiler.DefinitionEditor):
            draw.message(f'Full file path: {ret.filename}')
            self.edit_header_file(ret)

      del_crumb()

   def select_version (self):
      # Find out which version of the software they'd like to use,
      # if there's more than one.
      items = []
      for entry in os.scandir(self.path):
         if entry.is_dir():
            items.append(entry.path)

      if len(items) == 0:
         self.version_path = self.path
         return True

      if len(items) == 1:
         # There's only one version of the software.
         # Assume that's the one.
         self.version_path = items[0]
         return True

      # There's more than one.
      crumb('Select a Version')
      sel = menu([(item, item) for item in items], title = 'Select a Version')
      if sel == -1:
         del_crumb()
         return False

      del_crumb()
      self.version_path = sel
      return True

   def select_hex_file (self, files, title):
      # Is there just one file?
      if len(files) == 1: return files[0]['path']
      sizes = (60, 18)
      cols  = ('Hex File', 'Size')
      items = [make_columns(sizes, cols, header = True)]
      for f in files:
         path = f['path']
         if path.startswith(self.version_path):
            path = path[len(self.version_path):]
         items.append((make_columns(sizes, (path, f['size_str'])), f['path']))
      sel = menu(items, title = title)
      if sel == -1: return False
      return sel

   def read_description (self):
      crumb('Read Description')
      draw.viewer(open(self.desc_file, 'r').read(),
         title = f'Description File for {self.serial}',
         rows = 22,
         cols = 90)
      del_crumb()

   def view (self):
      crumb(self.title)
      
      if not self.select_version():
         return False

      # Show a menu until they're done.
      while True:
         items = [
            ('Program this System', 'program'),
            ('Recompile Software',  'recompile'),
            ('Advanced Recompile',  'advanced')]

         if os.path.exists(self.desc_file):
            items.append(('Read Description File', 'read'))

         sel = menu(items, title = self.title)

         if sel == -1:
            del_crumb()
            break

         elif sel == 'read':
            self.read_description()

         elif sel == 'program':
            if self.can_program():
               self.program()
            else:
               draw.message(('There is no final binary (main.hex) for this system.\n\n'
                  'Please choose the "Recompile Software" option first.'))

         elif sel == 'recompile':
            self.compile()

         elif sel == 'advanced':
            self.edit_header_files()
            self.compile()

   def can_program (self):
      # We need to find main.hex and the debounce main.hex at minimum.
      # If we don't find the bootloader, that's okay, but the user will
      # get a warning a bit later.
      draw.message(f'Version path is {self.version_path}.')
      files = utils.find_files(self.version_path, '.hex', compare = 'endswith')
      self.main_files = [e for e in files if e['is_main'] and 'main' in e['name']]
      self.debounce_files = [e for e in files if e['is_debounce']]
      self.boot_files = [e for e in files if e['is_bootloader']]

      if not len(self.main_files) or not len(self.debounce_files):
         return False

      if len(self.main_files) >= 1 and len(self.debounce_files) >= 1:
         return True

   def compile (self):
      draw.begin_wait('Compiling...')
      comp = compiler.Compiler(self.version_path, in_place = True)
      if not comp.compile():
         draw.end_wait()
         return False
      draw.end_wait()
      return True

   def program (self):
      # We've got the version picked, and the hex files have been
      # scanned for, but let's actually pick the hex files.
      self.main_hex = self.select_hex_file(self.main_files, 'Select Main Program')
      if not self.main_hex: return False

      self.debounce_hex = self.select_hex_file(self.debounce_files, 'Select Debounce Program')
      if not self.debounce_hex: return False

      skip_boot = False
      self.boot_hex = self.select_hex_file(self.boot_files, 'Select Bootloader')
      if not self.boot_hex:
         result = draw.question(('This system does not have a bootloader.\n\nProgram anyway?'))
         if result == 'N':
            return False
         skip_boot = True

      if self.boot_hex is None: skip_boot = True
      if self.boot_hex == False: return False

      if not self.program_flash_drive(): return False
      if not self.program_debounce(): return False
      if not self.program_main(skip_boot): return False

      # Everything must have gone OK.
      return True

   def program_debounce (self):
      message = ('Plug the programmer into the debounce header (right).\n'
         '\n'
         'Press ENTER when ready, or ESCAPE to cancel.')

      prog = programmer.BoardProgrammer()
      prog.add_target(
         'atmega88',
         message = message, title = 'Program Debounce Chip',
         fuses = (0xFF, 0xD0, 0xFC),
         hex_file = self.debounce_hex,
         can_skip = True,
         speed = 128)

      if not prog.program():
         return False

      return True

   def program_main (self, skip_boot):
      # If we're skipping the bootloader, use the main hex file.
      if skip_boot:
         filename = self.main_hex
      else:
         # Combine the bootloader and the main hex file.
         result, filename = utils.combine_hexes(self.main_hex, self.boot_hex)
         if not result:
            draw.message((
               'Something went wrong combining the main firmware '
               'and the bootloader.\n'
               '\n'
               f'Main HEX file: {self.main_hex}\n'
               f'Boot HEX file: {self.boot_hex}\n'
               '\n'
               f'Talk to Steven.'), colors = 10)
            return False

      message = ('Plug the programmer into the main header (left).\n'
         '\n'
         'Press ENTER when ready, or ESCAPE to cancel.\n'
         'You can also press S to skip this step.')

      prog = programmer.BoardProgrammer()
      prog.add_target(
         'atmega2560',
         message = message, title = 'Programming CPU',
         fuses = (0xFF, 0xD0, 0xFC),
         hex_file = filename,
         can_skip = True,
         speed = 1)

      if not prog.program():
         draw.message('Something went wrong while programming the CPU.', colors = 10)
         return False

      # Announce success.
      draw.begin_wait('Success! System is programmed.', colors = 11)
      time.sleep(3.0)
      draw.end_wait()

      return True

   def program_flash_drive (self):
      result = draw.question((
         'Plug in a USB Flash drive.\n'
         '\n'
         'Press ENTER when ready, or S to skip this step.'),
         default = 0,
         choices = ('&OK', '&Skip'))

      if result == 'S':
         draw.begin_wait('Skipping USB Flash drive setup.')
         time.sleep(2.0)
         draw.end_wait()
         return True

      result = usb_scan.select_device()

      if result == False:
         # They canceled.
         return False

      if result == True:
         # They'd like to skip.
         return True

      draw.begin_wait('Mounting USB Flash drive...')

      # They'd like to continue. Mount the device.
      while not usb_scan.mount_device(result):
         again = draw.question('Could not mount USB Flash drive.\n\nTry again?')
         if again == 'N':
            # They'd like to cancel.
            return False

      time.sleep(0.8)
      draw.end_wait()

      # Copy the firmware file and our local copy of the VDIP firmware.
      draw.begin_wait('Copying files...')
      shutil.copy(self.main_hex, f'{usb_scan.mount_dir}/firmware.bin')
      shutil.copy(self.vdip_firmware, f'{usb_scan.mount_dir}/ftrfb.ftd')
      time.sleep(0.8)
      draw.end_wait()

      # Unmount.
      draw.begin_wait('Unmounting USB Flash drive...')
      usb_scan.unmount_device(result)
      time.sleep(0.8)
      draw.end_wait()

      draw.begin_wait('You can now remove the USB Flash drive.', colors = 11)
      time.sleep(3.0)
      draw.end_wait()

      # Success, probably.
      return True

def gather_descriptions ():
   descs = {}
   nondescs = 0

   for entry in os.scandir(injector_data):
      # Skip?
      if not entry.is_dir(): continue
      if not os.path.exists(f'{entry.path}/desc.txt'): 
         nondescs += 1
         continue

      # It has it.
      descs[entry.name] = open(f'{entry.path}/desc.txt', 'r').read().lower()

   return descs, nondescs

def search_descriptions ():
   crumb('Search All Descriptions')

   draw.begin_wait('Gathering descriptions...')
   descs, nondescs = gather_descriptions()
   draw.end_wait()

   win = draw.newwin(20, 60, title = 'Search Descriptions', text =
      ('This will allow you to search the description files for all injection systems.\n'
       '\n'
       'Some older systems may not have a description file and cannot be searched, '
       'contradicting my previous sentence.\n'
       '\n'
       f'I have found {len(descs)} systems with description files. Cross your fingers that it\'s '
       f'one of those! That means there are {nondescs} systems without description files.\n'
       '\n'
       '\n'
       '\n'
       'Type a search term and hit Enter, or hit Escape to go back.'))

   draw.separator(win, 11)
   win.refresh()

   win_h, win_w = win.getmaxyx()

   ret = text_input(
      can_escape = True, border = False, relative_to = win,
      coords = (16, 1, 2, win_w - 2))

   # Escape?
   if ret == -1:
      del win
      stdscr.touchwin()
      stdscr.refresh()
      return False

   # Search away!
   ret = ret.lower()
   matches = []
   for desc in descs:
      if ret in descs[desc]:
         matches.append((desc, desc))

   if len(matches):
      draw.message((
         f'I found {len(matches)} systems that include that term in their description file.\n'
         '\n'
         'Press Enter to see the list.'),
         title = 'Matches Found')

      sel = 0
      while True:
         sel = menu(matches, title = 'Matching Systems', pre_select = sel)

         if sel == -1:
            break

         else:
            # It's a serial as a key
            prog = InjectorProgrammer(sel)
            prog.view()

   else:
      draw.message(('I did not find any system description files containing your search term.\n'
         '\n'
         'Press Enter to return.'),
         title = 'No Matches Found')

   # Clean up
   del win
   stdscr.touchwin()
   stdscr.refresh()
   del_crumb()

def show_all_injectors (recent_first = False):
   title = 'All Serial Numbers'
   serials = [(serial, serial) for serial in sorted(os.listdir(injector_data))]
   ret = 0

   crumb(title)

   while True:
      ret = menu(serials, title = title, pre_select = ret)

      if ret == -1:
         break

      else:
         prog = InjectorProgrammer(ret)
         prog.view()

   del_crumb()

def do_injector ():
   crumb('Build an Injector')
   ret = 0

   while True:
      # Build the menu.
      items = ['-Name'.ljust(left_col + 1) + 'Model']
      for item in predefined:
         items.append((item['name'].ljust(left_col) + item['model'], item['serial']))

      items.append('-')
      items.append(('See All Serial Numbers', 'serial'))
      items.append(('Search Descriptions', 'desc'))

      ret = menu(items, title = 'Build an Injector', pre_select = ret)

      if ret == 'serial':
         show_all_injectors()

      elif ret == 'desc':
         search_descriptions()

      elif isinstance(ret, str) and ret.startswith('A'):
         # This is a predefined system, use a custom title.
         title = [pre['name'] + ' - ' + pre['model'] for pre in predefined if pre['serial'] == ret][0]
         title += f' ({ret})'

         prog = InjectorProgrammer(ret)
         prog.view()

      elif ret == -1:
         del_crumb()
         break

