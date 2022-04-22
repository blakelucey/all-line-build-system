import os
import time
import json
import xml.etree.ElementTree as xml
import shutil
import hashlib
import curses

import draw
import colors
import utils
import compiler
import config
import programmer
import sd_card
from network import set_network
from text_input import text_input, ip_address_regex
from menu import menu
from __main__ import stdscr, crumb, del_crumb

from logger import log_debug

def make_display_file (data, dest):
   display = {
      "scale": not data['full_screen'],
      "scale_x": 140,
      "scale_y": 103,
      "scale_width": 530,
      "scale_height": 279,
      "device": "/dev/fb0",
      "driver": "fbcon"
   }
   with open(f'{dest}/display.json', "w") as outfile:
      json.dump(display, outfile)
   return True

def make_options_file (data, dest):
   options = {
      "owner": data['owner'],
      "address": data['location'],
      "address_2": "",
      "name": data['nickname'],
      "record_all_flow": False,
      "unit": data['unit'] == 'Liters',
      "keypad_password": 0,
      "schedule_enabled": False,
      "brightness": 50,
      "input_timeout": 120,
      "screensaver_timeout": 360,
      "days": [
         {
            "open": True,
            "begins": "00:00",
            "ends": "00:00",
            "all_day": True
         },
         {
            "open": True,
            "begins": "00:00",
            "ends": "00:00",
            "all_day": True
         },
         {
            "open": True,
            "begins": "00:00",
            "ends": "00:00",
            "all_day": True
         },
         {
            "open": True,
            "begins": "00:00",
            "ends": "00:00",
            "all_day": True
         },
         {
            "open": True,
            "begins": "00:00",
            "ends": "00:00",
            "all_day": True
         },
         {
            "open": True,
            "begins": "00:00",
            "ends": "00:00",
            "all_day": True
         },
         {
            "open": True,
            "begins": "00:00",
            "ends": "00:00",
            "all_day": True
         }
      ]
   }
   with open(f'{dest}/options.json', "w") as outfile:
      json.dump(options, outfile)
   return True

def make_system_options_file (data, dest):
   system_options = {
      "serial": data['serial'],
      "activated": True,
      "expires_on": None,
      "warn": False,
      "num_products": data['num_products'],
      "capabilities": []
   }
   with open(f'{dest}/system_options.json', "w") as outfile:
      json.dump(system_options, outfile)
   return True

def make_accounts_file (data, dest):
   if data['testing_account']:
      accounts = {
         "groups": [
            {
               "id": "07049fbd7af765a3",
               "enabled": True,
               "permissions": [1, 2, 3, 4, 5, 6, 7, 8],
               "name": "All-Line"
            }
         ],
         "accounts": [
            {
               "id": "6144",
               "group_id": "07049fbd7af765a3",
               "enabled": True,
               "locked": False,
               "pin": False,
               "permissions": [1, 2, 3, 4, 5, 6, 7, 8],
               "card_data": "",
               "auto_assign": False,
               "limit": "0",
               "name": "Testing Account"
            }
         ]
      }
      with open(f'{dest}/accounts.json', "w") as outfile:
         json.dump(accounts, outfile)
   perms = ','.join([str(n+1) for n in range(int(data['num_products']))])
   log_debug(f'PERMS {perms}')
   return True

def make_tanks_file (data, dest):
   tanks = {
      "emulation": data['tls_emu'],
      "poll_period": "3.0",
      "history_period": "60.0",
      "relax_time": "120.0",
      "required_change": "20.0",
      "tanks": []
   }
   for i in range(8):
      tank = {
         "present": (i < int(data['num_tanks'])),
         "name": f"Tank {i+1}",
         "channel_id": i,
         "offset": "0",
         "shape": "box",
         "dimensions": {
            "width": 50.0,
            "height": 50.0,
            "depth": 50.0,
            "diameter": 0.0
         },
         "max_level": "0",
         "probe_type": "active",
         "enabled": False,
         "low_level": "0",
         "match_products": [],
         "triggers": []
      }
      tanks['tanks'].append(tank)

   with open(f'{dest}/tanks.json', "w") as outfile:
      json.dump(tanks, outfile)

   return True

def make_manager_file (data, dest):
   managers = {
      "users": [
         {
               "real_name": "All-Line Equipment",
               "username": "all-line",
               "enabled": True,
               "permissions": {
                  "web": "super admin",
                  "groups": []
               },
               "last_activity": 0,
               "last_ip": "",
               "password_hash": "bcdde72f8ffad157876b170249033f34e83b55b7"
         },
         {
               "real_name": "User",
               "username": data['admin'],
               "enabled": True,
               "permissions": {
                  "web": "super admin",
                  "groups": []
               },
               "last_activity": 0,
               "last_ip": "",
               "password_hash": hashlib.sha1(data['password'].encode('ascii')).hexdigest()
         }
      ]
   }
   with open(f'{dest}/managers.json', "w") as outfile:
      json.dump(managers, outfile)

   return True

def make_config_files (data):
   dest = f'{data["staging_dir"]}'

   # Change to the config directory.
   dest = f'{dest}/config'
   try:
      os.mkdir(dest)
   except FileExistsError:
      draw.message(('Unable to create/clear the configuration directory. '
         'You\'ll probably want to tell Steven about this.'),
         colors = colors.error)
      return False

   errors = []

   if not make_display_file(data, dest):
      errors.append('display file')

   if not make_options_file(data, dest):
      errors.append('options file')

   if not make_system_options_file(data, dest):
      errors.append('system configuration file')

   if not make_accounts_file(data, dest):
      errors.append('accounts file')

   if not make_tanks_file(data, dest):
      errors.append('tanks file')

   if not make_manager_file(data, dest):
      errors.append('web interface users file')

   if len(errors):
      text = 'The following errors occurred:\n\n'
      for error in errors:
         text += f'Unable to generate {error}.\n'
      text += '\nYou might need to talk to Steven.'
      draw.message(text, colors = colors.error, center = False)
      return False

   return True

def make_sd_card (data):
   card = sd_card.SDCardBuilder('buildroot-fb-TNG', 'all_line_pi4')
   if not card.build():
      return False

   # Clear existing program data.
   if len(card.prog_path) > 1:
      os.system(f'sudo rm -fr {card.prog_path}/*')

   # Copy the program data.
   try:
      utils.copy_tree(data['staging_dir'], card.prog_path)
      utils.copy_tree(f"{data['staging_dir']}/config/", card.conf_path)
   except (IOError, OSError, PermissionError, FileNotFoundError) as e:
      draw.message((f'Unable to copy Fuel Boss software to {card.prog_path}.\n'
         '\n'
         f'Python says: {e}'),
         colors = 10)
      return False

   # Now change ownership and permissions.
   os.system(f'sudo chown -R root:root {card.prog_path}/*')
   os.system(f'sudo chmod -R 755 {card.prog_path}/*')

   # Copy our configuration to the config partition.
   with open(card.conf_path + '/build.cfg', 'w') as f:
      f.write(json.dumps(data))

   # Again, change ownership and permissions.
   os.system(f'sudo chown -R root:root {card.conf_path}/*')
   os.system(f'sudo chmod -R 777 {card.conf_path}/*')

   # Set up the network.
   network = {
      'address': data['ip'],
      'netmask': data['netmask'],
      'gateway': data['gateway'],
      'dns': data['dns']
   }

   set_network(card.root_path, network, card.conf_path)

   # Last thing we're going to do is disable the reverse ssh startup script which originated inside rootfs.tar.gz
   os.system(f'sudo chmod -R 644 {card.root_path}/etc/init.d/S90rssh')

   # Unmount everything.
   if not card.cleanup():
      draw.message(('Could not unmount SD card partitions.\n\nYou\'ll probably need Steven.'), colors = 10)
      return False

   # Success!
   draw.begin_wait('The SD card was successfully created!', colors = 11)
   time.sleep(3.0)
   draw.end_wait()

   # Save this?
   where_dir = f'{utils.storage_dir}/Fuel-Boss-Images'
   if not os.path.exists(where_dir):
      os.mkdir(where_dir)
   where = f'{where_dir}/{data["serial"]}.img.xz'
   result = draw.question((
      'Create an image of the system you\'ve just built?\n'
      '\n'
      f'It will be placed at:\n{where}'),
      default = 0, escape = 1)

   if result == 'Y':
      utils.create_disk_image(config.get('sd_card_device'), where)

   return True

def create_staging_dir (data):
   dest = data['staging_dir']
   log_debug('creating {}'.format(dest))
   if os.path.exists(dest):
      log_debug('trashing files in {}'.format(dest))
      # Remove the existing data.
      shutil.rmtree(dest, ignore_errors = True)
      os.mkdir(dest)
      os.mkdir(f'{dest}/firmware')
   else:
      log_debug('dir DNE: {}'.format(dest))
      os.mkdir(dest)
      os.mkdir(f'{dest}/firmware')

def program_main_board (data):
   # The mainboard code changes depending on selected features.
   # These are stored in inc/features.h
   # We'll use the DefinitionEditor to modify these.
   comp = compiler.Compiler(f'{data["dir"]}/io_controller')
   dest = comp.get_path()
   defs = compiler.DefinitionEditor(f'{dest}/inc/features.h')

   if data['card_reader'] == 'Magnetic':
      defs.define('CAP_MAGNETIC_CARD')
      defs.remove_define('MAGCARD_MAGTEK')
      defs.define('MAGCARD_BRUSH')
   elif data['card_reader'] == 'Proximity':
      defs.remove_define('CAP_MAGNETIC_CARD')
      defs.remove_define('MAGCARD_MAGTEK')
      defs.remove_define('CAP_HID_CARD_2')
      defs.define('CAP_HID_CARD')
   else:
      defs.remove_define('CAP_MAGNETIC_CARD')
      defs.remove_define('CAP_HID_CARD_2')
      defs.remove_define('CAP_HID_CARD')

   if data['tank_monitor'] == 'None':
      defs.remove_define('CAP_TANK_GAUGES')
      defs.remove_define('CAP_DFM')
      defs.remove_define('CAP_DFM_READING')
      defs.remove_define('SENSORS_AS_TANKS')
   elif data['tank_monitor'] == 'Serial':
      defs.define('CAP_TANK_GAUGES')
      defs.define('CAP_DFM')
      defs.remove_define('SENSORS_AS_TANKS')
      defs.remove_define('CAP_DFM_READING')
   elif data['tank_monitor'] == 'Sensors':
      defs.define('CAP_TANK_GAUGES')
      defs.define('CAP_DFM')
      defs.define('SENSORS_AS_TANKS')
      defs.remove_define('CAP_DFM_READING')

   defs.save()

   if not comp.compile():
      draw.message('Something went wrong during compilation.\n\nTalk to Steven.', colors = 10)
      return False

   message = ('Power the Fuel Boss on with no SD card inserted.\n'
      '\n'
      'Then, connect the programmer to the main header on the edge of the board, '
      'with the white triangle pointing to the red wire.\n'
      '\n'
      'Press ENTER when ready, to ESCAPE to cancel.\n'
      'You can also press S to skip this step.')

   prog = programmer.BoardProgrammer()
   prog.add_target('atmega640',
      message = message,
      title = 'Program IO Controller',
      fuses = (0xFF, 0xD0, 0xFD),
      hex_file = f'{comp.get_path()}/main.hex',
      can_skip = True,
      speed = 2,
      copy_to = f'{data["staging_dir"]}/firmware',
      copy_name = 'io')

   if not prog.program():
      return False

   return True

def program_debounce (data):
   # The debounce code never really changes. Just upload the binary.
   message = ('Power the Fuel Boss on with no SD card inserted.\n'
      '\n'
      'Then, connect the programmer to the debounce header near the '
      'PULSERS label on the board, with the white triangle pointing to the red wire.\n'
      '\n'
      'Press ENTER when ready, or ESCAPE to cancel.\n'
      'You can also press S to skip this step.')

   prog = programmer.BoardProgrammer()
   prog.add_target('attiny2313',
      message = message,
      title = 'Program Debounce Chip',
      fuses = (0xFF, 0xD1, 0xFE),
      hex_file = f'{data["dir"]}/debounce/main.hex',
      can_skip = True,
      speed = 16,
      copy_to = f'{data["staging_dir"]}/firmware',
      copy_name = 'debounce')

   if not prog.program():
      return False

   return True

def program_dfm_board (data):
   # As with the debounce, the DFM code never really changes.
   message = ('Power the Fuel Boss on with no SD card inserted.\n'
      'Ensure that the tank gauge/DFM board is connected.\n'
      '\n'
      'Then, connect the programmer to the tank gauge/DFM board such that '
      'the white triangle on the board points to the red wire.\n'
      '\n'
      'Press ENTER when ready, or ESCAPE to cancel.\n'
      'You can also press S to skip this step.')

   prog = programmer.BoardProgrammer()
   prog.add_target('atmega328pb',
      message = message,
      title = 'Program Tank Gauge/DFM Board',
      fuses = (0xFF, 0xD0, 0xFC),
      hex_file = f'{data["dir"]}/dfm/main.hex',
      can_skip = True,
      speed = 16,
      copy_to = f'{data["staging_dir"]}/firmware',
      copy_name = 'dfm')

   if not prog.program():
      return False

   return True

def copy_program (data):
   # Copy the software from the program directory into the staging
   # directory, ignoring files we don't want.

   draw.begin_output(title = 'Copying Files', rows = 24, cols = 130)
   src = f'{data["dir"]}/raspberry_pi'
   dest = data["staging_dir"]
   ignore = [
      '*.pyc', '*.bat', 'finalize.sh', 'integrated_finalize.sh',
      'make_update.sh', 'new_finalize.sh', 'remote_update.sh',
      'tags', 'todo.txt', 'testing_cycle.sh', 'staging', 'unused']
   def copy_func (s, d):
      nonlocal ignore
      draw.write_output(f'Copying {s}...')
      time.sleep(0.01)
      #return shutil.copy2(s, d)

   try:
      utils.copy_tree(
         src, dest, ignore = ignore, callback = copy_func)
   except (IOError, OSError, shutil.Error) as error:
      draw.message(str(error), colors = 10)
      draw.end_output()
      return False

   # Everything must have gone okay.
   draw.end_output()
   return True

def build (info):
   crumb('Stable, FB2.0 on Pi 4')

   data = {
      # Data about where things are
      'staging_dir': info['staging_dir'],
      'dir': info['dir'],
      'buildroot_version': 'pi4',

      # Data about the Fuel Boss
      'serial': 'FB100000',
      'num_products': 4,
      'card_reader': 'Magnetic',
      'tank_monitor': 'None',
      'num_tanks': '0',
      'tls_emu': False,
      'full_screen': False,
      #'wex': False,
      #'enterprise': False,
      'testing_account': True,
      'owner': '',
      'location': '',
      'nickname': 'Fuel-Boss',
      'unit': 'Gallons',
      'keypad': 'None',
      'admin': 'user',
      'password': '',
      'ip': '192.168.1.4',
      'netmask': '255.255.255.0',
      'gateway': '192.168.1.1',
      'dns': '8.8.8.8',
      'dhcp': False
   }

   ret = 0
   q = '"'
   while True:
      items = [
         (f'Serial Number           {data["serial"]}', 'serial'),
         (f'Number of Products      {data["num_products"]}', 'num_products'),
         (f'Card Reader             {data["card_reader"]}', 'card_reader'),
         (f'Tank Monitor Board      {data["tank_monitor"]}', 'tank_monitor'),
         (f'Number of Tanks         {data["num_tanks"]}', 'num_tanks'),
         (f'Do TLS Emulation?       {data["tls_emu"]}', 'tls_emu'),
         (f'Full Screen             {data["full_screen"]}', 'full_screen'),
         #(f'Report to WEX?          {data["wex"]}', 'wex'),
         #(f'Enterprise\'s WEX?      {data["enterprise"]}', 'enterprise'),
         (f'Enable Test Account     {data["testing_account"]}', 'testing_account'),
         (f'System Owner            {data["owner"] if len(data["owner"]) else "(not yet set)"}', 'owner'),
         (f'Location                {data["location"] if len(data["location"]) else "(not yet set)"}', 'location'),
         (f'Nickname                {data["nickname"] if len(data["nickname"]) else "(not yet set)"}', 'nickname'),
         (f'System Unit             {data["unit"]}', 'unit'),
         (f'Keypad Password         {data["keypad"]}', 'keypad'),
         ('-'),
         (f'Default Admin Username  "{data["admin"]}"', 'admin'),
         (f'Default Admin Password  {q+data["password"]+q if len(data["password"]) else "(empty)"}', 'password'),
         ('-'),
         (f'Auto-Setup for Source Cellular Modems', 'auto')]

      if data['dhcp']:
         items += [
            (f'IP Address              Auto'),
            (f'Subnet Mask             Auto'),
            (f'Default Gateway         Auto'),
            (f'DNS                     Auto'),
            (f'Use DHCP                True', 'dhcp')]
      else:
         items += [
            (f'IP Address              {data["ip"]}', 'ip'),
            (f'Subnet Mask             {data["netmask"]}', 'netmask'),
            (f'Default Gateway         {data["gateway"]}', 'gateway'),
            (f'DNS                     {data["dns"]}', 'dns'),
            (f'Use DHCP                False', 'dhcp')]

      items += [
         ('-'),
         (f'I\'m done setting this up. Proceed to build the whole unit.', 'done'),
         (f'I\'m done setting this up. Only build an SD card.', 'sd_card')]

      ret = menu(items, title = 'Standard Fuel Boss 2.0 Configuration, Pi 4', pre_select = ret)

      if ret == 'serial':
         new_serial = text_input(
            data['serial'][2:],
            prompt = 'Enter a serial number:',
            prefix = 'FB',
            force_width = 30,
            max_len = 8,
            match = '^FB[0-9]{6}$')

         if new_serial is not None:
            data['serial'] = new_serial

      elif ret == 'num_products':
         new_num = menu([
            ('Single product', 1), ('2 products', 2), ('3 products', 3), ('4 products', 4),
            ('6 products', 6), ('8 products', 8)])

         if new_num != -1:
            data['num_products'] = new_num

      elif ret == 'card_reader':
         new_reader = menu([
            ('No card reader support', 'None'),
            ('Magnetic (Brush)', 'Magnetic'),
            ('HID/Proximity', 'Proximity')])

         if new_reader != -1:
            data['card_reader'] = new_reader

      elif ret == 'tank_monitor':
         new_tank = menu([
            ('No Tank Monitor', 'None'),
            ('External Tank Board', 'Serial'),
            ('Sensors as Tank Board', 'Sensors')])

         if new_tank != -1:
            data['tank_monitor'] = new_tank

      elif ret == 'num_tanks':
         num_tanks = text_input(
            data['num_tanks'],
            prompt = 'Enter a the numebr of tanks this sytem will use:',
            max_len = 1,
            force_width = 40,
            match = '^[0-8]')
         if num_tanks is not None and len(num_tanks):
            data['num_tanks'] = num_tanks

      elif ret == 'wex':
         data['wex'] = not data['wex']

      elif ret == 'enterprise':
         data['enterprise'] = not data['enterprise']

      elif ret == 'tls_emu':
         data['tls_emu'] = not data['tls_emu']

      elif ret == 'full_screen':
         data['full_screen'] = not data['full_screen']

      elif ret == 'testing_account':
         data['testing_account'] = not data['testing_account']

      elif ret == 'owner':
         new_owner = text_input(
            data['owner'],
            prompt = 'Enter an owner:',
            max_len = 24,
            force_width = 40)

         if new_owner is not None and len(new_owner):
            data['owner'] = new_owner

      elif ret == 'location':
         new_location = text_input(
            data['location'],
            prompt = 'Enter a location:',
            max_len = 24,
            force_width = 40)

         if new_location is not None and len(new_location):
            data['location'] = new_location

      elif ret == 'nickname':
         new_nickname = text_input(
            data['nickname'],
            prompt = 'Enter a nickname:',
            max_len = 24,
            force_width = 40)

         if new_nickname is not None and len(new_nickname):
            data['nickname'] = new_nickname

      elif ret == 'unit':
         data['unit'] = 'Gallons' if data['unit'][0] == 'L' else 'Liters'

      elif ret == 'keypad':
         new_password = text_input(
            data['keypad'] if data['keypad'] != 'None' else '',
            prompt = 'Enter a password, or leave blank:',
            max_len = 8,
            force_width = 40,
            match = '^[0-9]{0,8}$')

         if new_password is not None:
            if not len(new_password):
               data['keypad'] = 'None'
            else:
               data['keypad'] = new_password

      elif ret == 'admin':
         new_username = text_input(
            data['admin'],
            prompt = 'Enter a web interface username:',
            max_len = 30,
            force_width = 50)

         if new_username is not None and len(new_username):
            data['admin'] = new_username

      elif ret == 'password':
         new_password = text_input(
            data['password'],
            prompt = 'Enter a web interface password:',
            max_len = 30,
            force_width = 50)

         if new_password is not None:
            data['password'] = new_password

      elif ret == 'ip':
         new_ip = text_input(
            data['ip'],
            prompt = 'Enter an IP address:',
            max_len = 15,
            force_width = 35,
            match = ip_address_regex)

         if new_ip is not None and len(new_ip):
            data['ip'] = new_ip

      elif ret == 'netmask':
         new_netmask = text_input(
            data['netmask'],
            prompt = 'Enter a subnet mask:',
            max_len = 15,
            force_width = 35,
            match = ip_address_regex)

         if new_netmask is not None and len(new_netmask):
            data['netmask'] = new_netmask

      elif ret == 'gateway':
         new_gateway = text_input(
            data['gateway'],
            prompt = 'Enter a default gateway:',
            max_len = 15,
            force_width = 35,
            match = ip_address_regex)

         if new_gateway is not None and len(new_gateway):
            data['gateway'] = new_gateway

      elif ret == 'dns':
         new_dns = text_input(
            data['dns'],
            prompt = 'Enter a DNS server:',
            max_len = 15,
            force_width = 35,
            match = ip_address_regex)

         if new_dns is not None and len(new_dns):
            data['dns'] = new_dns

      elif ret == 'auto':
         result = draw.question(('Do you want to set the IP, subnet mask, '
            'gateway and DNS to the correct values for use with a Source '
            'cellular modem?'))

         if result == 'Y':
            data['ip'] = '192.168.13.100'
            data['netmask'] = '255.255.255.0'
            data['gateway'] = '192.168.13.31'
            data['dns'] = '8.8.8.8'

      elif ret == 'dhcp':
         data['dhcp'] = not data['dhcp']

      elif ret == 'done':
         errors = []
         create_staging_dir(data)
         if not program_debounce(data):
            errors.append('- Unable to program debounce chip')

         if not program_main_board(data):
            errors.append('- Unable to program IO chip')

         if data['tank_monitor'] == 'Serial':
            if not program_dfm_board(data):
               errors.append('- Unable to program DFM board')

         if not copy_program(data):
            errors.append('- Unable to copy Pi software to staging directory')

         if not make_config_files(data):
            errors.append('- Unable to generate Fuel Boss configuration files')

         if not make_sd_card(data):
            errors.append('- Unable to build an SD card')

         if len(errors):
            errors = 'The following errors occurred:\n\n' + '\n'.join(errors)
            viewer = draw.viewer(
               errors,
               rows = 34, cols = 120,
               title = 'Something Went Wrong',
               colors = 10, attrs = curses.A_BOLD)

      elif ret == 'sd_card':
         create_staging_dir(data)
         if not copy_program(data):
            errors.append('- Unable to copy Pi software to staging directory')

         if not make_config_files(data):
            errors.append('- Unable to generate Fuel Boss configuration files')

         if not make_sd_card(data):
            draw.message('Unable to complete the SD card build process.', colors = 10)

      elif ret == -1:
         result = draw.question(('Cancel this Fuel Boss build?'),
            default = 1, escape = 0)

         if result == 'Y':
            break

   stdscr.touchwin()
   stdscr.refresh()
   del_crumb()

