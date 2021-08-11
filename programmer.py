import subprocess
import os
import curses
import time
import shutil

import config
import draw
import utils
from __main__ import stdscr, crumb, del_crumb

class ChipTarget:
   def __init__ (
      self,
      device,
      fuses = None,
      main_hex = None,
      can_skip = False,
      require_prompt = True,      
      message = None,
      speed = None,
      title = None,
      eeprom_hex = None,
      copy_to = None,
      copy_name = None):

      if speed is None: speed = '0.1'
      self.device = device
      self.fuses = {
         'lfuse': fuses[0],
         'hfuse': fuses[1],
         'efuse': fuses[2]}
      for key in self.fuses:
         if not isinstance(self.fuses[key], int):
            self.fuses[key] = int(self.fuses[key], 16)
      self.eeprom_hex = eeprom_hex
      self.hex_file = main_hex
      self.speed = speed
      self.message = message
      self.title = title
      self.can_skip = can_skip
      self.require_prompt = require_prompt
      self.copy_to = copy_to
      self.copy_name = copy_name
      if self.copy_name is not None and self.copy_name.endswith('.hex'):
         self.copy_name = self.copy_name[:-4]

class BoardProgrammer:
   def __init__ (self):
      self.targets = []

   def add_target (
      self,      
      device,      
      message = None,      
      title = None,      
      fuses = None,      
      hex_file = None,      
      can_skip = False,      
      require_prompt = True,      
      speed = None,      
      eeprom_hex = None,
      copy_to = None,
      copy_name = None):

      if fuses is None: return False
      self.targets.append(ChipTarget(
         device, message = message, title = title,
         fuses = fuses, main_hex = hex_file, eeprom_hex = eeprom_hex,
         can_skip = can_skip, require_prompt = require_prompt, speed = speed, copy_to = copy_to, copy_name = copy_name))

   def programmer_check (self):
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
            return True

   def program (self):
      # Check for the programmer presence.
      if not self.programmer_check():
         return False

      # Do each target, unless the user can skip them.
      for target in self.targets:
         do_del = False

         if target.title:
            crumb(target.title)
            do_del = True

         if target.can_skip:
            choices = ('&OK', '&Cancel', '&Skip')
         else:
            choices = ('&OK', '&Cancel')

         if target.message is None:
            # Bland default message.
            message = (
               'Plug the programmer into the programming header on the circuit board.\n'
               '\n'
               'Press ENTER when ready, or ESCAPE to cancel.')
            if target.can_skip:
               message += '\nYou can also press S to skip this step.'
         else:
            message = target.message

         if require_prompt:   
            result = draw.question(message, choices = choices, default = 0, escape = 1, title = target.title)
         else:
            result = 'Y'

         if result == 'S':
            # They want to skip this target.
            if do_del: del_crumb()
            continue

         elif result == 'C':
            # They want to cancel everything.
            if do_del: del_crumb()
            return False

         else:
            # Must be OK!
            if not self.program_target(target):
               if do_del: del_crumb()
               return False
            if do_del: del_crumb()   

      # Looks like it worked.
      return True

   def program_target (self, target):
      if not self.program_fuses(target):
         return False

      if target.hex_file:
         if not self.program_main(target):
            return False

      if target.eeprom_hex:
         if not self.program_eeprom(target):
            return False

      if target.copy_to is not None and target.copy_name is not None:
         if target.hex_file:
            shutil.copy(target.hex_file, f'{target.copy_to}/{target.copy_name}.hex')
         if target.eeprom_hex:
            shutil.copy(target.eeprom_hex, f'{target.copy_to}/{target.copy_name}_eeprom.hex')

         with open(f'{target.copy_to}/{target.copy_name}_fuses.txt', 'w') as f:
            f.write(f'lfuse: {target.fuses["lfuse"]}\n')
            f.write(f'hfuse: {target.fuses["hfuse"]}\n')
            f.write(f'efuse: {target.fuses["efuse"]}\n')

      return True

   def program_eeprom (self, target):
      draw.begin_wait(f'Programming target EEPROM ({target.device})...')
      ret = utils.avrdude_command(
         target.device, 'eeprom', target.eeprom_hex, run = True, progress = True, speed = target.speed)
      time.sleep(0.5)
      draw.end_wait()

      if ret != 0:
         draw.message(f'Unable to program EEPROM ({target.device}).\n\nCheck your connections.', colors = 10)
         return False

      return True

   def program_main (self, target):
      draw.begin_wait(f'Programming target CPU ({target.device})...')
      ret = utils.avrdude_command(
         target.device, 'flash', target.hex_file, run = True, progress = True, speed = target.speed)
      time.sleep(0.5)
      draw.end_wait()

      if ret != 0:
         draw.message(f'Unable to program CPU ({target.device}).\n\nCheck your connections.', colors = 10)
         return False

      return True

   def program_fuses (self, target):
      for fuse, value in target.fuses.items():
         draw.begin_wait(f'Programming {fuse.upper()} to {value:02X}...')
         ret = utils.avrdude_command(
            target.device, fuse, value, run = True, progress = False)
         time.sleep(0.25)
         draw.end_wait()

         if ret != 0:
            draw.message(f'Unable to program {fuse.upper()}.\n\nIs the value {value:02X} right?', colors = 10)
            return False

      return True
      

