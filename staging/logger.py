# All-Line Equipment Company

import os
import time
import datetime

import ansi

_log_file = '/dev/shm/log.txt'
_log_handle = None

def make_log_text (text, leader_type, leader_color = '', text_color = ansi.reset):
   when = time.strftime('%Y-%m-%d %H:%M:%S')
   return leader_color + when + ' <' + leader_type + '> ' + text_color + ': ' + text + ansi.reset

def log_custom (text, leader_type, leader_color, text_color):
   text = make_log_text(text, leader_type.ljust(5), leader_color, text_color)
   print text
   _log_handle.write(text)
   _log_handle.write('\r\n')
   _log_handle.flush()

def log_info (text):
   # 'INFO ' is padded with a space for neat alignment
   text = make_log_text(text, 'INFO ', ansi.br_green)
   print text
   _log_handle.write(text)
   _log_handle.write('\r\n')
   _log_handle.flush()

def log_error (text):
   text = make_log_text(text, 'ERROR', ansi.br_red, ansi.br_red)
   print text
   _log_handle.write(text)
   _log_handle.write('\r\n')
   _log_handle.flush()

if 'DEBUG' in os.environ or os.path.exists('/config/debug'):
   def log_debug (text):
      text = make_log_text(text, 'DEBUG', ansi.br_yellow)
      print text
      _log_handle.write(text)
      _log_handle.write('\r\n')
      _log_handle.flush()
else:
   def log_debug (text):
      pass

# Initialize the logging system
if _log_handle is None:
   _log_handle = open(_log_file, 'a')
   log_info('- - - New Output Starts Here - - -')

