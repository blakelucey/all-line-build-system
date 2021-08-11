# All-Line Equipment Company

# Not even remotely compatible with Python 3.

import os
import sys
import datetime
import time
import socket
import struct

from logger import *

class TLSValueStreamer:
   '''Decodes values from TLS-350 data streams.'''

   def __init__ (self, data):
      self.data = data.strip('\x01\x03')
      self.ptr = 0
      self.limit = len(data)

      # Attempt to validate the data against its provided checksum.
      # Throw an exception if it's no good; it'll propagate up.
      self.checksum()

   def checksum (self):
      '''Performs a checksum and throws ValueError if there's a mismatch.'''

      # TLS-350 responses have a &&ABCD part, where ABCD is the checksum in
      # ASCII hex characters.
      if '&&' not in self.data:
         log_error('TLS-350 sent us invalid data; missing checksum.')
         raise ValueError()

      # Convert the hex characters to an int; this is the checksum we should
      # get when we do the math ourselves.
      pos = self.data.index('&&')
      got_sum = int(self.data[pos + 2 : pos + 6], 16)

      # Calculate our own.
      check = (-ord('\x01')) & 0xFFFF
      for n in self.data[:pos + 2]:
         check = ((check - ord(n)) & 0xFFFF)

      # Any good?
      if check != got_sum:
         log_error('TLS-350 sent us invalid data; checksum mismatch.')
         raise ValueError()

      # Strip off the checksum part.
      self.data = self.data[:pos+1]
      self.limit = len(self.data)

   def is_available (self, num):
      '''Checks if 'num' characters are available for reading from the response.'''
      return not (self.ptr + num >= self.limit)

   def advance (self, num):
      '''Gets the next 'num' bytes of the response.'''
      part = self.data[self.ptr : self.ptr + num]
      self.ptr += num
      return part

   def get_command (self):
      '''Get the command part of a TLS-350 response; it's 6 bytes.'''
      if not self.is_available(6):
         log_error('TLS-350 should have sent 6 bytes by now, but did not.')
         raise ValueError()

      return str(self.advance(6))

   def get_date_time (self):
      '''Gets a date and time from the response; returns a DateTime.'''
      y, m, d, hh, mm = [self.get_decimal(2) for _ in range(5)]
      y += 2000
      return datetime.datetime(y, m, d, hh, mm, 0)

   def get_char (self):
      if not self.is_available(1):
         log_error('TLS-350 should have sent 1 byte by now, but did not.')
         raise ValueError()
      return self.advance(1)

   def get_string (self, size):
      if not self.is_available(size):
         log_error('TLS-350 should have sent {} bytes by now, but did not.'.format(size))
         raise ValueError()
      return self.advance(size).strip()

   def get_byte (self):
      if not self.is_available(2):
         log_error('TLS-350 should have sent 2 bytes by now, but did not.')
         raise ValueError()
      return int(self.advance(2), 16)

   def get_decimal (self, size):
      if not self.is_available(size):
         log_error('TLS-350 should have sent {} bytes by now, but did not.'.format(size))
         raise ValueError()
      return int(self.advance(size))

   def get_float (self):
      if not self.is_available(8):
         log_error('TLS-350 should have sent 8 bytes by now, but did not.')
         raise ValueError()
      return struct.unpack('>f', self.advance(8).decode('hex'))[0]

class TankMonitor ():
   '''Implements a connection to a TLS-350 compatible tank monitor.'''

   def __init__ (self, ip, port):
      self.ip = ip
      self.port = port
      self.timeout = 2.0

      try:
         # Two-second timeout since this is a blocking function
         self.socket = socket.create_connection((ip, port), 2.0)
         self.socket.setblocking(0)
         self.socket.settimeout(self.timeout)
      except socket.timeout:
         log_error('Unable to connect to the tank monitor. Timed out after {:.2f} seconds.'.format(self.timeout))
         self.socket = None
      except socket.error:
         log_error('Unable to connect to the tank monitor. Connection was refused.')
         self.socket = None

   def ok (self):
      return self.socket != None

   def get_tank_data (self, specific_tank = None):
      tanks = []
      tank_code = '00' if specific_tank is None else str(specific_tank).rjust(2, '0')

      # Query tank, with 'tank' set to zero for 'all tanks'
      v = self.query('i201{}'.format(tank_code))

      # Skip the command and timestamp
      v.get_command()
      v.get_date_time()

      # Loop until we've counted all of the tanks
      count = 0
      while v.is_available(1):
         # Add this tank
         tanks.append({
            'name': '',
            'height': 0.0,
            'volume': 0.0,
            'temperature': 0.0,
            'delivery_in_progress': 0
         })

         # Get the tank number
         v.get_decimal(2)

         # The product code
         v.get_char()

         # The status bits (16 bits, so 4 hex characters)
         tanks[count]['delivery_in_progress'] = v.get_char()
         v.get_char()
         v.get_char()
         v.get_char()

         # How many fields follow? We have to get each one.
         fields = v.get_byte()

         for n in xrange(fields):
            # Grab a float
            value = v.get_float()

            # Is this the volume? The docs say that the volume is always the
            # first field.
            if n == 0:
               tanks[count]['volume'] = value

            # Is this the height? The docs say that the height is always the
            # fourth field.
            if n == 3:
               tanks[count]['height'] = value

            # Is this the temperature? The docs say that the temperature is always the
            # sixth field.
            if n == 5:
               tanks[count]['temperature'] = value

         # This tank is done; continue for the next one.
         count += 1

      # We have counted the tanks.
      # Now get their names.
      v = self.query('i602{}'.format(tank_code))
      v.get_command()
      v.get_date_time()

      for n in xrange(count):
         # Get the tank number
         v.get_decimal(2)

         # And now a 20-character tank name
         # (See the docs; it says it's always 20 characters, space padded)
         tanks[n]['name'] = v.get_string(20)

      # Return the name list; len(result) is how many tanks
      return tanks if specific_tank is None else tanks[0]

   def query (self, command):
      if not self.socket:
         return None

      # Send a command and wait for a valid response.
      self.send(command)

      response = ''
      timeout = time.time()
      while response[-6:-4] != '&&':
         try:
            response += self.socket.recv(1)
         except socket.timeout as e:
            log_error('Communications with the tank monitor have hit a snag: {}'.format(e))
            raise ValueError()

         if time.time() - timeout > self.timeout:
            log_error('Did not get a timely response from the tank monitor. It took more than {:.2f} seconds.'.format(self.timeout))
            raise ValueError()

         # Strip extraneous characters.
         response = response.strip('\x01\x03')

      return TLSValueStreamer(response)

   def send (self, command):
      if not self.socket:
         return

      # Commands start with <SOH>, ASCII 01
      cmd = '\x01{}\n'.format(command)
      self.socket.send(cmd)

   def close (self):
      try:
         if self.socket:
            self.socket.close()
      except socket.error:
         return

