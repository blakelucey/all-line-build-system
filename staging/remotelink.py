# All-Line Equipment Company
# Remote Link Object

import serial
import struct
import os
import time
import random

from remotecommands import RemoteCommands

class RemoteLinkError (Exception):
   '''Raised when the remote link has broken and can't be recovered. Catching this exception should restart the software.'''
   def __init__ (self, message = ''):
      super(RemoteLinkError, self).__init__(message)

class RemoteLink:
   '''A wrapper around a serial link that implements common operations and synchronization.'''

   sync_lock_file = '/dev/shm/sync-lock' if os.name == 'posix' else './sync-lock'

   def __init__ (self, port = '/dev/ttyAMA0', baud = 115200, timeout = 2.0):
      self.port = port
      self.baud = baud
      self.timeout = timeout

      self.open()

   def open (self):
      self.ser = serial.Serial(
         self.port,
         self.baud,
         timeout = self.timeout,
         rtscts = False,
         dsrdtr = False
      )

   def close (self):
      self.ser.flush()
      self.ser.close()

   def _read (self, code = None, count = 1):
      '''Reads 'count' bytes, intercepting any errors. Converts data to 'code' if supplied.'''

      # TODO Create request method that handles all errors involved in communication.
      # TODO Use a string of expected incoming values to replay commands. Should work.

      try:
         data = self.ser.read(count)
         if len(data) == count:
            # Automatically convert data?
            if code is None:
               return data
            else:
               return struct.unpack('=' + code, data)[0]
         else:
            raise RemoteLinkError('Did not receive {} bytes from controller.'.format(count))
      except (struct.error, RemoteLinkError):
         log_info('Remote link error; trying to re-establish a connection.')
         self.flush()
         self.sync_and_challenge()
         time.sleep(0.05)
         return 0

   def sync_lock (self):
      '''Indicates to other software that we are not synchronized.'''
      with open(self.sync_lock_file, 'w') as f:
         pass

   def sync_unlock (self):
      '''Indicates to other software that we are correctly synchronized.'''
      if os.path.exists(self.sync_lock_file):
         os.remove(self.sync_lock_file)

   def flush (self):
      '''Flushes the input and output buffer completely.'''
      self.ser.reset_input_buffer()
      self.ser.reset_output_buffer()

   def sync (self):
      '''Synchronize data streams with the remote system.'''
      # Issue sync requests until the most recent 8 bytes we have matches AA 55 DE AD BE EF 55 AA.
      recent = ''

      self.sync_lock()

      self.flush()
      self.ser.write(RemoteCommands['sync']['char'])

      sync_began = time.time()

      while True:
         # Read in one byte at a time.
         ch = self.ser.read(1)

         if time.time() - sync_began > 10.0:
            # Ten seconds is way too long.
            raise RemoteLinkError('Took too long to synchronize.')

         if not len(ch):
            # Timed out; retry.
            self.flush()
            self.ser.write(RemoteCommands['sync']['char'])
            recent = ''
         else:
            # We got some data. Append it and see if we've synced up.
            recent = (recent[:-1] if len(recent) > 8 else recent) + ch

            if recent == '\xAA\x55\xDE\xAD\xBE\xEF\x55\xAA':
               # We're done.
               break
            else:
               # We're not there yet.
               continue

   def challenge (self):
      '''Challenge the remote system to complete some simple math. This makes sure they're listening correctly.'''
      retry = False
      fails = 0
      num = random.randint(0, 120)
      self.ser.write(RemoteCommands['hello']['char'])
      self.ser.write(chr(num))
      syncs = 0
      ch = ''
      while syncs < 10 and fails < 50:
         if not retry:
            ch = self.ser.read(1)

         if not len(ch) or retry:
            # We didn't get any reply at all. Reset and try again.
            self.flush()
            num = random.randint(0, 120)
            self.ser.write(RemoteCommands['hello']['char'])
            self.ser.write(chr(num))
            retry = False
         else:
            # We are expecting num + 1.
            if ord(ch) == num + 1:
               syncs += 1
               retry = True
            else:
               failes += 1
               retry = True

      success = fails < 50 and syncs >= 10
      if not success:
         raise RemoteLinkError('Too many failures when challenging controller.')

      self.sync_unlock()

   def sync_and_challenge (self):
      self.sync()
      self.challenge()

   def write_bytes (self, data):
      return self.ser.write(data)

   def write_int (self, num, bits = 32):
      '''Write a singed number, either 8, 16 or 32 bits.'''
      chars = {8: 'b', 16: 'h', 32: 'l'}
      if bits not in chars: return
      self.ser.write(struct.pack('<' + chars[bits], num))

   def write_float (self, num):
      '''Write an IEEE-754 floating point number.'''
      self.ser.write(struct.pack('<f', float(num)))

   def write_string (self, data):
      '''Write a null-terminated string.'''
      self.ser.write(data)
      self.ser.write(chr(0))

   def get_bytes (self, count = 1):
      '''Read an arbitrary number of bytes. Automatically resyncs and challenges on failure.'''
      data = self.ser.read(count)
      if not data or len(data) != count:
         # We did not get everything we asked for. That means we're out of sync.
         self.sync_and_challenge()
      return data

   def get_float (self):
      '''Read an IEEE-754 floating point number; single-precision, always 32 bits.'''
      try:
         return struct.unpack('<f', self.get_bytes(4))[0]
      except (struct.error, ValueError, TypeError):
         raise RemoteLinkError()

   def get_int (self, bits = 32):
      '''Read a signed number, either 8, 16 or 32 bits.'''
      try:
         chars = {8: 'b', 16: 'h', 32: 'l'}
         if bits not in chars: return 0
         return struct.unpack('<' + chars[bits], self.get_bytes(bits / 8))[0]
      except (struct.error, ValueError, TypeError) as e:
         raise RemoteLinkError('Unable to read {} bytes from controller; error was {}.'.format(bits // 8, e))

   def get_string (self):
      '''Read a null-terminated string.'''
      ret = ''
      while True:
         ch = ord(self.get_bytes(1))
         if ch == 0:
            # This is the end of the string.
            break
         else:
            ret += chr(ch)
      return ret

