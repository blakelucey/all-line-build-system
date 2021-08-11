# All-Line Equipment Company
# Simple User-mode GPIO
# Requires GPIO support in sysfs in the kernel.

import os

from logger import *

class Gpio:
   input = 0
   output = 1
   low = 0
   high = 1

   def __init__ (self):
      pass

   def set_direction (self, d):
      pass

   def set_value (self, v):
      pass

   def get_direction (self):
      pass

   def get_value (self):
      pass

   def set_high (self):
      pass

   def set_low (self):
      pass

class GpioException (Exception):
   pass

class GpioUsingSysfs:
   def __init__ (self, pin, direction = None, initvalue = None):
      self.prefix = '/sys/class/gpio'
      with open(self.prefix + '/export', 'w') as f:
         f.write('%d' % pin)
      if not os.path.exists(self.prefix + ('/gpio%d' % pin)):
         raise GpioException()
      self.pin = pin
      if direction is not None:
         self.set_direction(direction)
      if initvalue is not None:
         self.set_value(initvalue)

   def set_direction (self, d):
      with open(self.prefix + ('/gpio%d/direction' % self.pin), 'w') as f:
         f.write('in' if not d else 'out')

   def set_value (self, v):
      with open(self.prefix + ('/gpio%d/value' % self.pin), 'w') as f:
         f.write('0' if not v else '1')

   def set_low (self):
      self.set_value(Gpio.low)

   def set_high (self):
      self.set_value(Gpio.high)

   def get_direction (self):
      ret = Gpio.input
      with open(self.prefix + ('/gpio%d/direction' % self.pin), 'r') as f:
         ret = Gpio.input if f.read().strip() == 'in' else Gpio.output
      return ret

   def get_value (self):
      ret = Gpio.low
      with open(self.prefix + ('/gpio%d/value' % self.pin), 'r') as f:
         ret = Gpio.low if f.read().strip() == '0' else Gpio.high
      return ret


