import time
import os
import sys
import shutil
import datetime

import draw
import utils
import programmer
import compiler
import sd_card
from network import set_network
from text_input import text_input, ip_address_regex
from menu import menu, make_columns
from __main__ import stdscr, crumb, del_crumb

bioblender_dir = './data/bioblender'

class Bioblender:
   def __init__ (self):
      self.version_dir = None
      self.injector_board_dir = None
      self.python_dir = None
      self.dir = bioblender_dir

      self.network = {
         'dhcp':    False, 
         'address': '192.168.1.4',
         'netmask': '255.255.255.0',
         'gateway': '192.168.1.1',
         'dns':     '8.8.8.8'
      }

   def select_version (self):
      # Find out if there are C source files in a given directory.
      def contains_c_sources (where):
         for entry in os.scandir(where):
            if entry.is_dir():
               if contains_c_sources(entry.path):
                  return True
            else:
               if entry.name.endswith('.c'):
                  # We've found at least one C file.
                  return True

         return False

      # Find all of the bioblender source directories.
      dirs = []
      for entry in os.scandir(bioblender_dir):
         if entry.is_dir() and contains_c_sources(entry.path):
            # This is probably alright.
            dirs.append((entry.name, entry.path))

      # None?
      if not len(dirs):
         draw.message((
            'No valid Bioblender source code has been found.\n'
            '\n'
            'You might consider mentioning this to Steven.'),
            colors = 10)
         return False

      # We've found one or more. Show a menu.
      ret = menu(dirs, title = 'Select a Version')

      if ret == -1:
         return False

      # Must have selected a version.
      self.version_dir = ret
      self.injector_board_dir = os.path.join(self.version_dir, 'InjectorBoard')
      self.python_dir = os.path.join(self.version_dir, 'RaspberryPi')

      # Does the injector board directory exist?
      boards = None
      if not os.path.exists(self.injector_board_dir):
         boards = 'injector board'

      if not os.path.exists(self.python_dir):
         boards = (boards + ' and Raspberry Pi') if boards is not None else 'Raspberry Pi'

      if boards is not None:
         draw.message((
            'This looks like a valid Bioblender source code directory, '
            f'but I can\'t seem to find the code for the {boards}.\n'
            '\n'
            'My capabilities are thus hindered. I defer to Steven.'),
            colors = 10)
         return False

      # Looks like we've got it.
      return True

   def program_debounce (self):
      debounce_dir = os.path.join(self.injector_board_dir, 'debounce')
      debounce_hex = os.path.join(debounce_dir, 'main.hex')
      message = ('Plug the programmer into the debounce header (right).\n'
         '\n'
         'Press ENTER when ready, or ESCAPE to cancel.')

      if not os.path.exists(debounce_hex):
         draw.message(('Missing debounce firmware.\n'
            '\n'
            'Talk to Steven.'), colors = 10)
         return False

      prog = programmer.BoardProgrammer()
      prog.add_target(
         'atmega88',
         message = message, title = 'Program Debounce Chip',
         fuses = (0xFF, 0xD0, 0xFC),
         hex_file = debounce_hex,
         can_skip = True,
         speed = 128)

      if not prog.program():
         draw.message('Something went wrong while programming the debounce chip.', colors = 10)
         return False

      return True

   def program_main (self):
      boot_dir = os.path.join(self.injector_board_dir, 'boot')
      boot_hex = os.path.join(boot_dir, 'bootloader.hex')
      main_hex = os.path.join(self.injector_board_dir, 'main.hex')

      result, filename = utils.combine_hexes(main_hex, boot_hex)
      if not result:
         draw.message((
            'I tried really hard, but something went wrong combining the main firmware '
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

      return True

   def copy_python_code (self):
      # Copy everything into the staging directory.
      staging_dir = './staging'
      if os.path.exists(staging_dir):
         shutil.rmtree(staging_dir, ignore_errors = True)
         os.mkdir(staging_dir)

      ignore = ['*.pyc', 'finalize.sh', 'install.sh', 'testing_cycle.sh',
         'old', 'buildroot']

      def copy_func (s, d):
         draw.write_output(f'Copying {s}...')
         time.sleep(0.01)

      draw.begin_output('Copying Files', rows = 24, cols = 130)

      try:
         utils.copy_tree(
            self.python_dir, staging_dir, ignore = ignore, callback = copy_func)
      except (IOError, OSError, shutil.Error) as error:
         draw.message(str(error), colors = 10)
         draw.end_output()
         return False

      # Looks OK.
      draw.end_output()
      return True

   def make_sd_card (self):
      card = sd_card.SDCardBuilder()
      if not card.build():
         return False

      # Copy the program data from the staging directory.
      try:
         utils.copy_tree('./staging', card.prog_path)
      except (IOError, OSError, PermissionError, FileNotFoundError) as e:
         draw.message((f'Unable to copy the Bioblender software to {card.prog_path}.\n'
            '\n'
            f'Python says: {e}\n\n'
            'Steven says "You should probably show me this."'),
            colors = 10)
         return False

      # Change ownership and permissions.
      os.system(f'sudo chown -R root:root {card.prog_path}/*')
      os.system(f'sudo chmod -R 755 {card.prog_path}/*')

      # Again, change ownership and permissions.
      os.system(f'sudo chown -R root:root {card.conf_path}/*')
      os.system(f'sudo chmod -R 777 {card.conf_path}/*')

      # Set up the network.
      set_network(card.root_path, self.network)

      # Unmount everything.
      if not card.cleanup():
         draw.message(('Could not unmount SD card partitions.\n\nYou\'ll probably need Steven.'), colors = 10)
         return False

      # Success!
      draw.begin_wait('The SD card was successfully created!', colors = 11)
      time.sleep(3.0)
      draw.end_wait()

      # Skip the disk image creation for now.
      return True

      # TODO
      # Save this?
      #where_dir = f'{utils.storage_dir}/Fuel-Boss-Images'
      #if not os.path.exists(where_dir):
      #   os.mkdir(where_dir)
      #where = f'{where_dir}/{data["serial"]}.img.xz'
      #result = draw.question((
      #   'Create an image of the system you\'ve just built?\n'
      #   '\n'
      #   f'It will be placed at:\n{where}'),
      #   default = 0, escape = 1)

      #if result == 'Y':
      #   utils.create_disk_image(config.get('sd_card_device'), where)

      return True

   def setup_network (self):
      ret = 0

      while True:
         items = [
            (f'Use DHCP?         {"Yes" if self.network["dhcp"] else "No"}', 'dhcp')]

         if not self.network['dhcp']:
            items += [
               (f'IP Address        {self.network["address"]}', 'address'),
               (f'Subnet Mask       {self.network["netmask"]}', 'netmask'),
               (f'Default Gateway   {self.network["gateway"]}', 'gateway'),
               (f'DNS Server        {self.network["dns"]}', 'dns')]

         ret = menu(items + ['-',
            ('Done, continue the programming process.', 'quit')],
            title = 'Network Configuration',
            pre_select = ret)

         if ret == -1:
            return False

         elif ret == 'quit':
            # Looks OK.
            return True

         elif ret == 'dhcp':
            self.network["dhcp"] = not self.network["dhcp"]

         elif ret == 'address':
            new_ip = text_input(
               self.network['address'],
               prompt = 'Enter an IP address:',
               max_len = 15,
               force_width = 35,
               match = ip_address_regex)

            if new_ip is not None and len(new_ip):
               self.network['address'] = new_ip

         elif ret == 'netmask':
            new_netmask = text_input(
               self.network['netmask'],
               prompt = 'Enter a subnet mask:',
               max_len = 15,
               force_width = 35,
               match = ip_address_regex)

            if new_netmask is not None and len(new_netmask):
               self.network['netmask'] = new_netmask

         elif ret == 'gateway':
            new_gateway = text_input(
               self.network['gateway'],
               prompt = 'Enter a default gateway:',
               max_len = 15,
               force_width = 35,
               match = ip_address_regex)

            if new_gateway is not None and len(new_gateway):
               self.network['gateway'] = new_gateway

         elif ret == 'dns':
            new_dns = text_input(
               self.network['dns'],
               prompt = 'Enter a DNS server:',
               max_len = 15,
               force_width = 35,
               match = ip_address_regex)

            if new_dns is not None and len(new_dns):
               self.network['dns'] = new_dns

   def program (self):
      if not self.select_version():
         return False

      # Ask them about setting an IP address.
      if not self.setup_network():
         return False

      # We've got the version selected; program the mainboard.
      if not self.program_debounce():
         return False

      if not self.program_main():
         return False

      # Now an SD card.
      if not self.copy_python_code():
         return False

      if not self.make_sd_card():
         return False

      return True

def do_bioblender ():
   crumb('Program a Bioblender')

   prog = Bioblender()

   if not prog.program():
      draw.message(('Bioblender programming was aborted.'), colors = 10)
      del_crumb()
      return False

   del_crumb()
   return True

