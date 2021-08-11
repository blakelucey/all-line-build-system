# All-Line Equipment Company

import os
import sys
import datetime
import time

from logger import *
from eventlog import log_event

class Pollable:
   def __init__ (self, **kwargs):
      self.poll_time = 0.0
      self.poll_interval = kwargs.get('poll_interval', None)

   def poll_reset (self):
      self.poll_time = 0.0

   def change_poll_interval (self, interval, reset = True):
      self.poll_interval = interval
      self.poll_reset()

   def poll (self):
      if not self.poll_interval:
         return

      if time.time() - self.poll_time < self.poll_interval and time.time() > self.poll_interval:
         return

      if getattr(self, 'action'):
         self.action()
      else:
         log_info('Poll attached to {} was attempted but something went wrong.'.format(
            self.__class__.__name__))

      self.poll_time = time.time()

