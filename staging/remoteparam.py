# All-Line Equipment Company
# Remote Parameter Object

from remotecommands import RemoteCommands
from logger import *

class RemoteParam:
   types = {
      'invalid': 0,
      'int': 1,
      'float': 2,
      'string': 3,
      'bytes': 4
   }

   type_strings = {
      0: 'N/A',
      1: 'Int32',
      2: 'Float',
      3: 'String',
      4: 'Bytes'
   }

   flagbits = {
      'string_in_rom': 0x01,
      'disabled': 0x02,
      'atomic': 0x04,
      'const': 0x08,
      'function': 0x10,
      'array': 0x20
   }

   flagbit_strings = {
      0x01: 'ROM data',
      0x02: 'disabled',
      0x04: 'atomic',
      0x08: 'const',
      0x10: 'callback',
      0x20: 'array'
   }

   def __init__ (self, remote, name):
      self.remote = remote
      self.link = remote.link

      self.id = -1
      self.value = None
      self.name = name
      self.description = 'This parameter has not yet been populated.'
      self.type = self.types['invalid']
      self.type_string = 'invalid'
      self.flags = 0
      self.flags_string = 'none'
      self.minimum = 0
      self.maximum = 0
      self.precision = 0

      # Initial population
      self.collect()

   def collect (self):
      '''Retrieves all of the metadata for a parameter.'''
      self.link.write_bytes(RemoteCommands['lookup']['char'])
      self.link.write_string(self.name)

      param_id = self.link.get_int(8)

      # Is this not an actual parameter?
      if param_id < 0 or param_id == 0xff:
         # No, the remote system doesn't know what this is.
         return False

      self.id = param_id

      # Now grab some information about the parameter.
      self.link.write_bytes(RemoteCommands['get']['char'] + chr(self.id) + chr(0))
      self.type = self.link.get_int(8)
      self.flags = self.link.get_int(8)
      self.flags_string = ''

      flags = []
      for bit in self.flagbits:
         if self.flags & self.flagbits[bit]:
            flags.append(self.flagbit_strings[self.flagbits[bit]])
      self.flags_string = ', '.join(flags) if len(flags) else 'none'

      if self.type == self.types['int']:
         self.type_string = 'int'
         self.minimum = self.link.get_int(32)
         self.maximum = self.link.get_int(32)
         self.link.get_int(32)
      elif self.type == self.types['float']:
         self.type_string = 'float'
         self.minimum = self.link.get_float()
         self.maximum = self.link.get_float()
         self.precision = self.link.get_int(8)
         self.link.get_float()
      elif self.type == self.types['string']:
         self.type_string = 'string'
         self.minimum = self.link.get_int(32)
         self.maximum = self.link.get_int(32)
         self.link.get_string()
      elif self.type == self.types['bytes']:
         self.type_string = 'bytes'
         self.minimum = 0
         self.maximum = self.link.get_int(16)
         self.link.get_bytes(self.maximum)
      else:
         return False

      # Try to get a description of this parameter
      self.link.write_bytes(RemoteCommands['getdesc']['char'] + chr(self.id) + chr(0))
      self.description = self.link.get_string()

      return True

   def is_array (self):
      return (self.flags & self.flagbits['array']) != 0

   def is_constant (self):
      return (self.flags & self.flagbits['const']) != 0

   def is_int (self):
      return (self.type == self.types['int'])

   def is_float (self):
      return (self.type == self.types['float'])

   def is_string (self):
      return (self.type == self.types['string'])

   def get (self, sub_id = 0):
      '''Gets the current value for this parameter; optionally, for arrays, a sub-ID can be provided.'''

      # If this isn't an array, sub_id > 0 isn't really a valid request.
      if not self.is_array() and sub_id > 0:
         sub_id = 0

      self.link.write_bytes(RemoteCommands['getvalue']['char'] + chr(self.id) + chr(sub_id))

      if self.type == self.types['int']:
         self.value = self.link.get_int(32)
      elif self.type == self.types['float']:
         self.value = self.link.get_float()
      elif self.type == self.types['string']:
         self.value = self.link.get_string()
      elif self.type == self.types['bytes']:
         self.maximum = self.link.get_int(16)
         self.value = self.link.get_bytes(self.maximum)

      return self.value

   def set (self, value, sub_id = 0):
      '''Sets a new value for this parameter; optionally, for arrays, a sub-ID can be provided. Returns False on failure.'''

      if not self.is_array() and sub_id > 0:
         return False

      self.link.write_bytes(RemoteCommands['set']['char'] + chr(self.id) + chr(sub_id))

      if self.type == self.types['int']:
         self.link.write_int(int(value), 32)
      elif self.type == self.types['float']:
         self.link.write_float(float(value))
      elif self.type == self.types['string']:
         self.link.write_string(str(value))

      # If we get 0xFF back, it worked. Save our new value.
      result = self.link.get_int(8)
      if result < 0 or result == 0xff:
         # Looks OK.
         log_debug('Setting parameter {} value to {}.'.format(self.name, value))
         self.value = value
         return True
      else:
         return False

