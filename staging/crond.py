# All-Line Equipment Company

import os
import getpass
import sys
import json

from utils import get_path

class CronJob:
   def __init__ (self):
      pass

class CronHelper:
   def __init__ (self):
      self.cron_dir = get_path() + 'cron'
      self.cron_user = getpass.getuser()

      self.entries = {}

      raise NotImplementedError('CronHelper is incomplete; Feb 28 2018 SGH')

   def collect (self):
      '''Reads the cron file and parses the comments.'''
      pass

