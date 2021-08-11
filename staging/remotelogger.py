# All-Line Equipment Company
# Watches the logging buffer on the mainboard and saves its contents
# to the regular log file.

import os
import sys
import time
import datetime

from logger import *
from pollsomething import Pollable

class LogWatcher (Pollable):
   def __init__ (self, remote):
      Pollable.__init__(self, **{
         'poll_interval': 2.0
      })

      self.remote = remote

   def action (self):
      # Is there anything in the log buffer? If so, get those items.
      # They'll be in reverse order.
      count = self.remote.get_param_value('Number of Log Items')
      text = []

      while count:
         text.append(self.remote.get_param_value('Logging', 1))
         count -= 1

      for item in text[::-1]:
         log_info('Mainboard: {}'.format(item))

