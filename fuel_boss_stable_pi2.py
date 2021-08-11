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

def make_service_file (data, dest):
   cfg = f'{dest}/service.xml'

   root = xml.Element('service')
   utils.add_child(root, 'serial-number', data['serial'])
   utils.add_child(root, 'number-of-products', data['num_products'])

   act = utils.add_child(root, 'activation')
   utils.add_child(act, 'state', 'activated')
   utils.add_child(act, 'expires-on', 'never')
   utils.add_child(act, 'warn-on-use', 'false')

   rep = utils.add_child(root, 'reporting')
   utils.add_child(rep, 'active', 'false')
   utils.add_child(rep, 'report-to', 'http://www.fuel-boss.com/reporting/')
   utils.add_child(rep, 'attach-transactions', 'true')

   return utils.save_xml(root, cfg)

def make_system_file (data, dest):
   cfg = f'{dest}/system.xml'

   root = xml.Element('config')
   utils.add_child(root, 'owner', data['owner'])
   utils.add_child(root, 'location', data['location'])
   utils.add_child(root, 'name', data['nickname'])
   utils.add_child(root, 'mode', 'regular')
   utils.add_child(root, 'master-address', '127.0.0.1')
   utils.add_child(root, 'unit', data['unit'].lower())
   utils.add_child(root, 'password', '0' if data['keypad'] == 'None' else data['keypad'])
   utils.add_child(root, 'brightness', '15')
   utils.add_child(root, 'authentication-type', 'keypad')

   to = utils.add_child(root, 'timeouts')
   utils.add_child(to, 'input', '120')
   utils.add_child(to, 'screensaver', '300')

   sched = utils.add_child(root, 'schedule', attrs = {'enabled': 'false'})
   utils.add_child(sched, 'day-begins', '08:00')
   utils.add_child(sched, 'day-ends', '17:00')

   store = utils.add_child(root, 'storage')
   utils.add_child(store, 'required', 'true')
   utils.add_child(store, 'sync-to-cloud', 'false')

   return utils.save_xml(root, cfg)

def make_accounts_file (data, dest):
   cfg = f'{dest}/accounts.xml'
   perms = ','.join([str(n) for n in range(int(data['num_products']))])

   root = xml.Element('groups')

   group = utils.add_child(root, 'group', attrs = {
      'enabled': 'true', 'id': '1', 'name': 'All-Line Equipment'})
   utils.add_child(group, 'permissions', perms)

   accounts = utils.add_child(group, 'accounts')
   account = utils.add_child(accounts, 'account', attrs = {
      'enabled': 'true', 'id': '1234', 'locked': 'false', 'name': 'Testing Account'})

   utils.add_child(account, 'pin', 'none')
   utils.add_child(account, 'permissions', perms)
   utils.add_child(account, 'limit', '0.0')

   auth = utils.add_child(account, 'authentication')
   utils.add_child(auth, 'card')

   return utils.save_xml(root, cfg)

def make_products_file (data, dest):
   cfg = f'{dest}/products.xml'

   root = xml.Element('products')

   for pid in range(int(data['num_products'])):
      prod = utils.add_child(root, 'product', attrs = {
         'id': f'{pid + 1}', 'name': f'Product {pid + 1}', 'enabled': 'true'})

      utils.add_child(prod, 'pulses-per-unit', '10.0')
      utils.add_child(prod, 'price', '$0.0')

      to = utils.add_child(prod, 'timeouts')
      utils.add_child(to, 'authorized', f'{60 * 2}')
      utils.add_child(to, 'first-pulse', '60')
      utils.add_child(to, 'missing-pulse', f'{60 * 2}')

   return utils.save_xml(root, cfg)

def make_prompts_file (data, dest):
   cfg = f'{dest}/prompts.xml'
   root = xml.Element('prompts')
   return utils.save_xml(root, cfg)

def make_tanks_file (data, dest):
   # Set up reporting parameters if we're building an Enterprise system.
   if data['enterprise']:
      reporting = {
         'hide': False,
         'enabled': False,
         'host': 'data.telapoint.com',
         'port': 21,
         'directory': 'IDSData',
         'site_id': '0000',
         'account_id': '100453',
         'interval': 720,
         'username': 'Enterprise_100453',
         'password': 'e27365ztat'
      }
   else:
      reporting = {
         'hide': True,
         'enabled': False,
         'host': '',
         'port': 21,
         'directory': '',
         'site_id': '',
         'account_id': '',
         'interval': 720,
         'username': '',
         'password': ''
      }

   # Generate triggers.
   triggers = [{
      'enabled': False,
      'level': 0,
      'direction': 0,
      'send_on_trigger': False,
      'send_on_no_trigger': False,
      'text': '',
      'log': True
   }]

   triggers *= 3

   # Generate the tank gauge inputs.
   tanks = []
   for tid in range(8):
      tank = {
         'id': tid,
         'enabled': False,
         'name': f'Tank {tid + 1}',
         'alt_name': '',
         'shape': 0,
         'width': 24.0,
         'height': 24.0,
         'depth': 24.0,
         'diameter': 0.0,
         'probe_type': 0,
         'offset': 0.0,
         'low_level': 0.0,
         'low_level_product_id': 0,
         'triggers': triggers
      }

      tanks.append(tank)

   tank_config = {
      'mode': 'internal',
      'tls350_emulation': True,
      'delivery_detection': {
         'required_change': 2,
         'relax_time': 30
      },
      'internal_update_interval': 1,
      'external_update_interval': 60,
      'max_level': 95,
      'tank_monitor': {
         'host': '0.0.0.0',
         'port': 80
      },
      'reporting': reporting,
      'tanks': tanks
   }

   cfg = f'{dest}/tanks.cfg'
   with open(cfg, 'w') as f:
      f.write(json.dumps(tank_config, indent = 3))

   return True

def make_deliveries_file (data, dest):
   cfg = f'{dest}/deliveries.cfg'
   with open(cfg, 'w') as f:
      f.write('')
      f.flush()

   return True

def make_smtp_file (data, dest):
   cfg = f'{dest}/smtp.cfg'

   smtp = {
      'server': 'smtp.gmail.com',
      'port': 587,
      'username': 'notifier@equipment-notifications.com',
      'password': 'thisisaverycomplexpassword'
   }
   
   with open(cfg, 'w') as f:
      f.write(json.dumps(smtp, indent = 3))

   return True

def make_web_user_file (data, dest):
   cfg = f'{dest}/web-users.cfg'
   hash = hashlib.sha1(data['password'].encode('ascii')).hexdigest()

   users = [
      {
         'real_name': 'All-Line Equipment',
         'username': 'all-line',
         'password_hash': 'bcdde72f8ffad157876b170249033f34e83b55b7',
         'permissions': ['update', 'admin']
      },
      {
         'real_name': 'User',
         'username': data['admin'],
         'password_hash': hash,
         'permissions': ['admin']
      }
   ]

   with open(cfg, 'w') as f:
      f.write(json.dumps(users, indent = 3))

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

   if not make_service_file(data, dest):
      errors.append('service file')

   if not make_system_file(data, dest):
      errors.append('system configuration file')

   if not make_accounts_file(data, dest):
      errors.append('accounts file')

   if not make_products_file(data, dest):
      errors.append('products file')

   if not make_prompts_file(data, dest):
      errors.append('prompts file')

   if not make_tanks_file(data, dest):
      errors.append('tanks file')

   if not make_deliveries_file(data, dest):
      errors.append('empty deliveries file')

   if not make_smtp_file(data, dest):
      errors.append('SMTP file')

   if not make_web_user_file(data, dest):
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
   card = sd_card.SDCardBuilder()
   if not card.build():
      return False

   # Clear existing program data.
   if len(card.prog_path) > 1:
      os.system(f'sudo rm -fr {card.prog_path}/*')

   # Copy the program data.
   try:
      utils.copy_tree(data['staging_dir'], card.prog_path)
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

   set_network(card.root_path, network)

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
   if os.path.exists(dest):
      # Remove the existing data.
      shutil.rmtree(dest, ignore_errors = True)
      os.mkdir(dest)
      os.mkdir(f'{dest}/firmware')
   else:
      os.mkdir(dest)
      os.mkdir(f'{dest}/firmware')

def program_main_board (data):
   # The mainboard code changes depending on selected features.
   # These are stored in inc/features.h
   # We'll use the DefinitionEditor to modify these.
   comp = compiler.Compiler(f'{data["dir"]}/new_fb_io_controller')
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

   if data['tank_monitor']:
      defs.define('CAP_TANK_GAUGES')
      defs.define('CAP_DFM')
      defs.remove_define('CAP_DFM_READING')
   else:
      defs.remove_define('CAP_TANK_GAUGES')
      defs.remove_define('CAP_DFM')
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
      hex_file = f'{data["dir"]}/new_dfm_controller/main.hex',
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
   src = f'{data["dir"]}/arm'
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
   crumb('Stable, Pi 2')

   data = {
      # Data about where things are
      'staging_dir': info['staging_dir'],
      'dir': info['dir'],
      'buildroot_version': 'pi2',

      # Data about the Fuel Boss
      'serial': 'FB100000',
      'num_products': 4,
      'card_reader': 'Magnetic',
      'tank_monitor': False,
      'wex': False,
      'enterprise': False,
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
      'gateway': '8.8.8.8',
      'dns': '192.168.1.1',
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
         (f'Report to WEX?          {data["wex"]}', 'wex'),
         (f'Enterprise\'s WEX?       {data["enterprise"]}', 'enterprise'),
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

      ret = menu(items, title = 'Standard V1 Fuel Boss Configuration, Pi 2', pre_select = ret)

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
         data['tank_monitor'] = not data['tank_monitor']

      elif ret == 'wex':
         data['wex'] = not data['wex']

      elif ret == 'enterprise':
         data['enterprise'] = not data['enterprise']

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

