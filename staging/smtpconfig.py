# All-Line Equipment Company
# SMTP Configuration Manager

import validators

from configurable import Configurable

class SmtpConfig (Configurable):
   def __init__ (self, ipc):
      Configurable.__init__(self, **{
         'context': 'SMTP Configuration',
         'file': 'reporting.cfg',
         'key': 'smtp',
         'defaults': {
            'server': '',
            'port': 0,
            'username': '',
            'password': '',
            'all_line_smtp': True
         },
         'validators': {
            'server': validators.validate_hostname,
            'port': validators.validate_int
         }
      })

      self.make_discoverable(ipc)

      self.load()

   def pre_validate (self, config):
      # If they haven't entered anything, don't continue with validation
      # since there isn't anything to validate.
      server = config['server'].strip()
      username = config['username'].strip()
      password = config['password'].strip()
      try:
         port = int(config['port'])
      except ValueError:
         # Continue validation; let them know this is wrong.
         return True

      if (len(server) or len(username)) and port != 0:
         return True

      # Nothing was really entered; let them get by
      return False

