# All-Line Equipment Company
# User-configurable options implementation

import json

from utils import get_path
from logger import *

class Configurable (object):
   def __init__ (self, **kwargs):
      self.config_context = kwargs.get('context', 'Unknown')
      self.config_file = kwargs.get('file', None)
      self.defaults = kwargs.get('defaults', {})
      self.limits = kwargs.get('limits', {})
      self.validators = kwargs.get('validators', {})
      self.config_types = kwargs.get('types', {})
      self.config_key = kwargs.get('key', None)
      self.config = self.defaults.copy()

      if self.config_file:
         self.config_file = get_path('config') + self.config_file

   def add_validator (self, key, func):
      self.validators[key] = func

   def run_validator (self, key, value):
      if key not in self.validators:
         return (True, '')

      func = self.validators[key]
      if isinstance(func, dict):
         # There's some custom properties.
         props = func
         func = props['function']
         message = props.get('message', None)
         args = props.get('arguments', {})
         ok, func_message = func(key, value, args)

         # Not a custom message? Use the one returned.
         if not message:
            message = func_message

         return (ok, message)
      else:
         # Use the error generated by the validator function.
         return func(key, value)

   def make_discoverable (self, ipc):
      if not self.config_key:
         log_error('Configurations must have a key to be discoverable via IPC.')
         raise RuntimeError('Configuration cannot be made discoverable.')

      ipc.add_handler('get_{}_config'.format(self.config_key), self.ipc_get_config_info)
      ipc.add_handler('reload_{}_config'.format(self.config_key), self.ipc_reload_config_info)
      ipc.add_handler('save_{}_config'.format(self.config_key), self.ipc_save_config_info)
      ipc.add_handler('validate_{}_config'.format(self.config_key), self.ipc_validate_config_info)
      log_info('Made {} discoverable via IPC.'.format(self.get_description()))

   def ipc_reload_config_info (self, skt, data):
      self.load()
      skt.send({
         'reply_to': data['request_type'],
         'key': self.config_key,
         'description': self.get_description(),
         'defaults': self.defaults,
         'config': self.config,
         'limits': self.limits
      })

   def ipc_validate_config_info (self, skt, data):
      # Check the incoming data against any validators.
      if 'config' not in data:
         skt.error('No configuration provided to validate against.')
         return

      invalid = self.validate(data['config'])

      skt.send({
         'reply_to': data['request_type'],
         'config': data['config'],
         'invalid': invalid,
         'errors': len(invalid)
      })

   def ipc_save_config_info (self, skt, data):
      # Match up the data with our configuration.
      # Fields missing are set to the defaults.
      # Extraneous fields are not used and raise no exception.

      if 'config' not in data:
         data = self.defaults

      config = data['config']
      prev = self.config.copy()

      for key in self.defaults:
         if key in config:
            if key in self.validators:
               # We can use a validator.
               ok, _ = self.run_validator(key, config[key])
               if not ok:
                  # Not okay; use the default.
                  self.config[key] = self.defaults[key]
               else:
                  self.config[key] = config[key]
            else:
               self.config[key] = config[key]
         else:
            self.config = self.defaults[key]

      self.save()
      skt.send({
         'reply_to': data['request_type'],
         'key': self.config_key,
         'description': self.get_description(),
         'defaults': self.defaults,
         'previous': prev,
         'config': self.config
      })

   def ipc_get_config_info (self, skt, data):
      skt.send({
         'reply_to': data['request_type'],
         'key': self.config_key,
         'description': self.get_description(),
         'defaults': self.defaults,
         'config': self.config,
         'limits': self.limits
      })

   def pre_validate (self, config):
      '''Pre-validation function. Return False if validation should be skipped.'''
      return True

   def post_validate (self, config, invalid):
      pass

   def validate (self, config):
      if not self.pre_validate(config):
         return {}

      invalid = {}
      
      for key in self.defaults:
         if key in config and key in self.validators:
            ok, message = self.run_validator(key, config[key])
            if not ok:
               invalid[key] = message

      self.post_validate(config, invalid)

      return invalid

   def get_description (self):
      return '{} ({}{})'.format(
         self.config_context,
         self.config_file,
         ':' + self.config_key if self.config_key else ''
      )

   def pre_load (self):
      pass

   def post_load (self):
      pass

   def pre_save (self):
      pass

   def post_save (self):
      pass

   def save (self):
      '''Saves configuration data.'''

      if not self.config_file:
         log_info('Save attempted without a configuration file defined.')
         raise RuntimeError('config_file not defined.')

      # Go through each element and check its type against self.config_types.
      for key in self.defaults:
         if key in self.config_types:
            if isinstance(self.config[key], list):
               self.config[key] = map(self.config_types[key], self.config[key])
            else:
               try:
                  self.config[key] = self.config_types[key](self.config[key])
               except ValueError:
                  # We need to use the default value here.
                  self.config[key] = self.config_types[key](self.defaults[key])

      self.pre_save()

      # The fun part here is that the configurations can be separate, but still
      # saved into the same file. This requires us to load the file, modify only
      # our configuration key, and then save it.

      try:
         if not os.path.exists(self.config_file):
            # Start with a blank file.
            data = {}
         else:
            data = json.loads(open(self.config_file, 'r').read())

         if self.config_key:
            data[self.config_key] = self.config
         else:
            data = self.config

         with open(self.config_file, 'w') as fh:
            fh.write(json.dumps(data, indent = 3))

         log_info('{} was saved.'.format(self.get_description()))
      except (KeyError, IOError, OSError, ValueError):
         log_error('{} could not be saved.'.format(self.get_description()))

      self.post_save()

   def load (self):
      '''Loads configuration data, applying defaults where necessary.'''

      if not self.config_file:
         log_info('Load attempted without a configuration file defined.')
         raise RuntimeError('config_file not defined.')

      self.pre_load()

      # If there are any issues loading the configuration, when we're finished,
      # make sure to write back completely valid data.
      write_back = False

      try:
         data = json.loads(open(self.config_file, 'r').read())
         if self.config_key:
            data = data[self.config_key]
         log_info('{} was loaded.'.format(self.get_description()))
      except (KeyError, ValueError, OSError, IOError):
         log_error('{} could not be loaded; applying defaults.'.format(self.get_description()))
         data = self.defaults
         write_back = True

      # Go through each of the keys and try to pull in the data from the loaded
      # data. Also match types.
      for key in self.defaults:
         if key in data:
            # This looks okay.
            self.config[key] = data[key]
         else:
            # Not okay; use a default.
            write_back = True
            self.config[key] = self.defaults[key]
            log_debug('Setting {} in {} was missing or invalid. The default was applied.'.format(
               key,
               self.get_description()
            ))

      if write_back:
         self.save()

      self.post_load()

