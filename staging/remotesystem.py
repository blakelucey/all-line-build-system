# All-Line Equipment Company
# Remote System Object

import datetime
import time
import os
from pprint import pprint
import shutil
import ast

from remotecommands import RemoteCommands
from remoteparam import RemoteParam
from gpio import Gpio, GpioUsingSysfs
from logger import *

class RemoteSystem:
   def __init__ (self, link, ipc):
      self.link = link
      self.params = {}
      self.ids_to_names = []
      self.ipc = ipc

      self.reset_line = GpioUsingSysfs(4, Gpio.output, Gpio.low)

      log_debug('Sending reset signal to mainboard...')
      #self.force_reboot()
      log_debug('Waiting for mainboard to reply...')
      time.sleep(1.0)

      self.collect_params()
      self.register_callbacks()

   def register_callbacks (self):
      # Set up callbacks related to the remote system.
      self.ipc.add_handler('get_param', self.ipc_get_param)
      self.ipc.add_handler('get_param_safe', self.ipc_get_param_safe)
      self.ipc.add_handler('set_param', self.ipc_set_param)
      self.ipc.add_handler('query_param', self.ipc_query_param)
      self.ipc.add_handler('reboot', self.ipc_reboot)
      self.ipc.add_handler('list_params', self.ipc_list_params)
      self.ipc.add_handler('list_params_values', self.ipc_list_params_values)
      self.ipc.add_handler('list_blender_settings_params', self.ipc_list_blender_settings_params)
      self.ipc.add_handler('save_params', self.ipc_save)
      self.ipc.add_handler('push_key', self.ipc_push_key)
      self.ipc.add_handler('pause', self.ipc_pause)
      self.ipc.add_handler('play', self.ipc_play)

   def ipc_pause (self, skt, data):
      self.pause()
      skt.send({
         'reply_to': data['request_type'],
         'error': False
      })

   def ipc_play (self, skt, data):
      self.play()
      skt.send({
         'reply_to': data['request_type'],
         'error': False
      })

   def ipc_push_key (self, skt, data):
      if 'key' not in data:
         skt.error('Missing keypress.')
         return

      key = data['key']
      if len(key) > 1: key = key[0]

      self.push_key(key)
      skt.send({
         'reply_to': data['request_type'],
         'error': False
      })

   def ipc_save (self, skt, data):
      success = self.save_params()

      skt.send({
         'reply_to': data['request_type'],
         'error': success == False
      })

   def ipc_list_params (self, skt, data):
      skt.send({
         'reply_to': data['request_type'],
         'names': self.params.keys()
      })
   
   def ipc_list_params_values (self, skt, data):      
      param_keys = self.params.keys()
      param_values = {}
      for key in param_keys:
         if str(key) == 'Display Mapping':
            log_debug('tossing: {}'.format(key))
            continue
         try:
            sub_id = 0 if 'index' not in data else int(data['index'])
         except ValueError:
            sub_id = 0
         param_values[key] = str(self.params[key].get(sub_id))

      #log_debug('NAMES AND VALUES: {}'.format(param_values))
      skt.send({
         'reply_to': data['request_type'],
         'params': param_values
      })

   def ipc_list_blender_settings_params (self, skt, data):
      param_keys = self.params.keys()
      param_values = {}
      
      blender_settings = ['Blend Percentage','Main PPU','Additive PPU','Additive Calibration Rate','Main Product',
      'Additive Product','Maximum Behind','Maximum Ahead','Behind Tolerance','Ahead Tolerance','Maximum Speed',
      'Record Interval','Minimum Valve Time','Minimum Main Rate','Totalizing Meter','VFD Check','Adjusted K-Factor']
      # fix names so they are all right aligned
      for key in param_keys:
         if key in blender_settings:
            try:
               sub_id = 0 if 'index' not in data else int(data['index'])
            except ValueError:
               sub_id = 0
            blender_settings[blender_settings.index(key)] = str(key.rjust(25))+": "+str(self.params[key].get(sub_id))
            param_values[key] = self.params[key].get(sub_id)

      reply_dict = {
         'params': blender_settings
      }

      # save the output to a file
      file_path = '/config/backup_parameters.txt'


      if os.path.exists(file_path):
         #only create the .old if the file is different than the one about to be created
         with open(file_path) as rf:
            rf_data = rf.read()

         d = ast.literal_eval(rf_data)

         if d!=reply_dict:
            if os.path.exists(file_path+'.old'):
               shutil.copy(file_path+'.old', file_path+'.older')   
            shutil.copy(file_path, file_path+'.old')

      with open(file_path, 'wt') as f:
         pprint(reply_dict, stream=f)

      reply_dict['reply_to'] = data['request_type']

      skt.send(reply_dict)

   def ipc_reboot (self, skt, data):
      skt.send({
         'reply_to': data['request_type'],
         'error': False
      })

      self.reboot()

      # Wait 5 seconds for the mainboard to come back up
      self.link.close()
      self.ipc.busy([])
      time.sleep(0.05)

      start = time.time()
      while time.time() - start < 5.0:
         self.ipc.poll()
         time.sleep(0.05)

      self.link.open()
      self.ipc.not_busy()

   def ipc_query_param (self, skt, data):
      if 'param_name' not in data:
         skt.error('query_param is missing a name.')
         return

      name = data['param_name']
      if name not in self.params:
         skt.error('query_param asked for unknown parameter {}.'.format(name))
         return

      param = self.params[name]

      skt.send({
         'reply_to': data['request_type'],
         'param_name': name,
         'param_value': param.value,
         'minimum_value': param.minimum,
         'maximum_value': param.maximum,
         'precision': param.precision,
         'type': param.type,
         'type_string': param.type_string,
         'flags': param.flags,
         'description': param.description
      })

   def ipc_get_param_safe (self, skt, data):
      if 'default_value' not in data:
         # An empty string is a reasonable default when they don't provide one
         data['default_value'] = ''

      send = {
         'reply_to': data['request_type'],
         'param_value': data['default_value']
      }

      if 'param_name' not in data:
         skt.send(send)
         return

      name = data['param_name']
      if name not in self.params:
         skt.send(send)
         return

      try:
         sub_id = 0 if 'index' not in data else int(data['index'])
      except ValueError:
         sub_id = 0

      try:
         value = self.params[name].get(sub_id)
      except RemoteLinkError:
         value = data['default_value']

      skt.send({
         'reply_to': data['request_type'],
         'param_name': name,
         'index': sub_id,
         'param_value': value
      })

   def ipc_get_param (self, skt, data):
      if 'param_name' not in data:
         skt.error('get_param is missing a name.')
         return

      name = data['param_name']
      if name not in self.params:
         skt.error('get_param asked for an unknown parameter.')
         return

      try:
         sub_id = 0 if 'index' not in data else int(data['index'])
      except ValueError:
         sub_id = 0

      skt.send({
         'reply_to': data['request_type'],
         'param_name': name,
         'index': sub_id,
         'param_value': self.params[name].get(sub_id)
      })

   def ipc_set_param (self, skt, data):
      if 'param_name' not in data:
         skt.error('set_param is missing a name.')
         return

      if 'param_value' not in data:
         skt.error('set_param is missing a value.')
         return

      name = data['param_name']
      if name not in self.params:
         skt.error('set_param asked to set an unknown parameter.')
         return

      try:
         sub_id = 0 if 'index' not in data else int(data['index'])
      except ValueError:
         sub_id = 0

      value = data['param_value']
      success = self.params[name].set(value, sub_id)

      skt.send({
         'reply_to': data['request_type'],
         'param_name': name,
         'new_value': value,
         'index': sub_id,
         'error': success == False
      })

   def save_params (self):
      '''Sends a save request to the remote system.'''
      self.link.write_bytes(RemoteCommands['save']['char'])
      result = self.link.get_int(8)
      log_info('Saved all parameters.')
      return result < 0 or result == 0xff

   def collect_params (self):
      '''Collects the entire list of supported parameters, their types and flags, and their initial values.'''
      if len(self.params):
         # We have already done this.
         return

      self.link.write_bytes(RemoteCommands['list']['char'])
      self.params = {}
      self.ids_to_names = []
      param_names = []

      count = self.link.get_int(8)
      self.ids_to_names = [None for n in xrange(count)]

      for i in xrange(count):
         name = self.link.get_string()
         param_names.append(name)

      # We've collected their names. Now try to get more information.
      for name in param_names:
         self.params[name] = RemoteParam(self, name)
         self.ids_to_names[self.params[name].id] = name

         log_debug('Collected parameter {} ({}, {}).'.format(
            name,
            self.params[name].type_string,
            self.params[name].flags_string
         ))

   def get_names (self):
      return self.ids_to_names

   def get_name_from_id (self, param_id):
      return self.ids_to_names[param_id]

   def get_names_and_ids (self):
      ret = [{'id': n, 'name': ''} for n in xrange(len(self.params))]
      for name in self.params:
         ret[self.params[name].id]['name'] = name
      return ret

   def get_all_params (self):
      return self.params

   def get_param (self, name):
      # Bad name?
      if not len(name):
         return None

      # Is this an ID number?
      if name[0] in '0123456789':
         name = int(name)
         if name < 0 or name >= len(self.ids_to_names):
            return None

         name = self.ids_to_names[int(name)]

      # Not a parameter
      if name not in self.params:
         return None

      return self.params[name]

   def get_param_value (self, name, sub_id = 0, defval = None):
      if name not in self.params:
         return defval

      return self.params[name].get(sub_id)

   def set_param_value (self, name, value, sub_id = 0):
      if name not in self.params:
         return False

      return self.params[name].set(value, sub_id)

   def set_date_and_time (self, dt):
      '''Formats 'dt' appropriately and tries to set the mainboard's date/time.'''
      fmt = dt.strftime('%Y-%m-%dT%H:%M:%S') + '+00:00'
      self.set_param_value('Clock', fmt)
      log_debug('Setting mainboard date/time to {}.'.format(dt.strftime('%c')))

   def get_date_and_time (self):
      '''Queries the injector for its date and time. Returns an instance of datetime.'''
      dt = self.get_param_value('Clock')
      try:
         # Strip the timezone information.
         dt = dt[:-6]
         return datetime.datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S')
      except ValueError:
         # Is this the standard "the clock has no idea" string?
         no_idea = '2000-01-01T00:00:80'

         if dt.startswith(no_idea):
            # Return a very wrong date so that the system corrects us.
            return datetime.datetime(2000, 1, 1, 0, 0, 0)

         return datetime.datetime.now()

   def push_key (self, ch):
      '''Simulate a keypress.'''
      self.set_param_value('Remote Keypress', ord(ch))

   def pause (self):
      '''Sends a pause request to the remote system.'''
      self.link.write_bytes(RemoteCommands['pause']['char'])

   def play (self):
      '''Sends a unpause/play request to the remote system.'''
      self.link.write_bytes(RemoteCommands['play']['char'])

   def reboot (self, mode = None):
      # If there's a mode to request, do that first.
      if mode is not None:
         self.link.write_bytes(RemoteCommands['bootmode']['char'] + chr(mode))

      # Send the reboot command 10 times
      self.link.write_bytes(RemoteCommands['reboot']['char'] * 10)

   def force_reboot (self):
      # Drive the microcontroller's reset line low to force a reboot
      # The GPIO is tied to the gate of a transistor, so setting the GPIO
      # line high pulls the reset line low.
      self.reset_line.set_high()
      time.sleep(0.1)
      self.reset_line.set_low()

   def poll (self):
      pass

