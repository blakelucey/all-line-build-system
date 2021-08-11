# All-Line Equipment Company

# Currently unused.
# Will become a USB scanner for localized firmware updates in the future.

import os
import sys
import time
import shlex
import subprocess

from logger import *

class UsbWatcher:
   def __init__ (self):
      self.poll_time = 0.0
      self.poll_interval = 10.0

   def poll (self):
      pass

