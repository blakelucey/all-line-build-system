# All-Line Equipment Company

import os
import sys
import time
import re
import shutil
import subprocess
import shlex

from utils import get_path
from logger import *

class RebootException (Exception):
   pass

class RebootWatcher (object):
   def __init__ (self, ipc):
      self.ipc = ipc
      self.ipc.add_handler('reboot_self', self.ipc_reboot_self)

   def ipc_reboot_self (self, skt, data):
      # Reply early.
      skt.send({
         'reply_to': data['request_type'],
         'error': False
      })

      # Make an attempt to reboot by throwing an exception.
      raise RebootException()

