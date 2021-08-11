# All-Line Equipment Company

import os
import sys
import json
import time
import datetime

import ansi

from utils import get_path
from logger import *

class EventLog:
   '''Maintains a list of events in a global event log.'''

   instance = None

   def __init__ (self, ipc):
      self.ipc = ipc
      self.event_file = get_path('config') + 'events.cfg'

      if not os.path.exists(self.event_file):
         open(self.event_file, 'w').close()
         os.chmod(self.event_file, 0777)

      EventLog.instance = self
      self.ipc.add_handler('clear_event_log', self.ipc_clear_event_log)
      self.ipc.add_handler('log_event', self.ipc_log_event)

   def ipc_log_event (self, skt, data):
      if 'kind' not in data or 'text' not in data:
         skt.error('Missing kind or text.')
         return

      self.event(data['kind'], data['text'])
      skt.send({
         'reply_to': data['request_type']
      })

   def ipc_clear_event_log (self, skt, data):
      with open(self.event_file, 'w') as f:
         f.flush()
         f.close()

      who = ''
      if 'user' in data:
         who = ' by {}'.format(data['user'])

      self.event('System', 'The event log was cleared{}.'.format(who))
      skt.send({
         'reply_to': data['request_type']
      })

   def event (self, kind, text):
      evt = {
         'time': datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
         'kind': str(kind),
         'text': str(text)
      }

      with open(self.event_file, 'a') as f:
         f.write(json.dumps(evt).strip() + '\r\n')
         f.flush()
         f.close()

      # Return this in case someone wants to use it
      return evt

# There's only one instance of the event logger.
def log_event (kind, text):
   if EventLog.instance is None:
      return
   EventLog.instance.event(kind, text)
   log_custom('{}: {}'.format(kind, text), 'EVENT', ansi.br_blue, ansi.reset)

