import os
import sys
import time
import shlex
import subprocess
import threading

class ProcessWatcher:
   def __init__ (self, command, line_callback):
      self.command = command
      self.split_command = shlex.split(command)
      self.callback = line_callback
      self.thread = None
      self.proc = None

   def _reader_thread (self, proc):
      for line in iter(proc.stdout.readline, ''):
         self.callback(line)

   def run (self, timeout = 30.0):
      self.proc = subprocess.Popen(
         self.split_command,
         stdout = subprocess.PIPE,
         stderr = subprocess.STDOUT
      )

      self.thread = threading.Thread(
         target = self._reader_thread,
         args = (self.proc,)
      )

      self.thread.start()

   def stop (self):
      if self.thread:
         self.proc.terminate()
         self.thread.join()

