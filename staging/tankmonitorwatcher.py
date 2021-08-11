# All-Line Equipment Company

import os
import sys
import datetime
import time
import json

import validators

from logger import *
from eventlog import log_event
from tankmonitor import TankMonitor
from utils import get_path
from configurable import Configurable

class TankMonitorWatcher (Configurable):
   def __init__ (self, remote, ipc):
      Configurable.__init__(self, **{
         'file': 'tank_monitor.cfg',
         'context': 'Tank Monitor',
         'key': 'tank_monitor',
         'defaults': {
            'enabled': False,
            'host': '',
            'port': 10001,
            'tank_id': 0,
            'low_level': 0,
            'save_history': False
         },
         'types': {
            'port': int,
            'tank_id': int,
            'low_level': int
         },
         'validators': {
            'host': validators.validate_hostname,
            'port': {
               'function': validators.validate_int,
               'arguments': {'minimum': 1, 'maximum': 65535}
            },
            'low_level': {
               'function': validators.validate_int,
               'arguments': {'minimum': 1, 'maximum': 10000}
            }
         }
      })

      self.make_discoverable(ipc)

      self.remote = remote
      self.ipc = ipc

      self.poll_time = 0.0
      self.poll_interval = 60.0 * 15.0
      self.is_low_level = False
      self.comm_failures = 0
      self.cached_tanks = []
      self.cached_reading = -1.0
      self.remote.set_param_value('Force Low Level', 0)
      self.remote.set_param_value('Remote Tank Height', -1.0)

      self.load()
      self.ipc.add_handler('reload_tank_monitor', self.ipc_reload_tank_monitor)
      self.ipc.add_handler('get_tank_monitor_tanks', self.ipc_get_tank_monitor_tanks)
      self.ipc.add_handler('can_connect_to_tank_monitor', self.ipc_can_connect_to_tank_monitor)
      self.ipc.add_handler('get_recent_tank_reading', self.ipc_get_recent_tank_reading)

   def ipc_can_connect_to_tank_monitor (self, skt, data):
      if self.did_connect:
         skt.send({
            'reply_to': data['request_type'],
            'can_connect': True
         })
      else:
         skt.send({
            'reply_to': data['request_type'],
            'can_connect': False
         })

   def ipc_get_recent_tank_reading (self, skt, data):
      skt.send({
         'reply_to': data['request_type'],
         'height': self.cached_reading
      })

   def connect (self):
      '''Connect to the tank monitor, returning a TankMonitor, or None.'''
      if self.config['host'].isspace():
         return None

      if not self.config['enabled']:
         return None

      log_debug('About to talk to the tank monitor at {}:{}.'.format(
         self.config['host'], self.config['port']))

      try:
         tm = TankMonitor(self.config['host'], self.config['port'])
         if tm.socket is None:
            self.comm_failures += 1
            return None
      except ValueError:
         self.comm_failures += 1
         return None

      # Looks OK.
      self.comm_failures = 0
      return tm

   def ipc_get_tank_monitor_tanks (self, skt, data):
      # Return the tanks we most recently knew about.

      skt.send({
         'reply_to': data['request_type'],
         'num_tanks': len(self.cached_tanks),
         'tanks': self.cached_tanks
      })

   def ipc_reload_tank_monitor (self, skt, data):
      skt.send({
         'reply_to': data['request_type']
      })

      self.load()

   def pre_validate (self, config):
      # Don't validate if they haven't entered all of the information.
      try:
         if not len(config['host']) or not len(config['port']):
            return False
      except (KeyError, TypeError):
         return False

      return True

   def post_save (self):
      self.post_load()

      # Reset the polling time so we poll the tank monitor immediately after saving.
      self.poll_time = 0.0

   def post_load (self):
      # Reset the poll time and the connected flag
      self.poll_time = 0.0
      self.did_connect = False
      self.cached_reading = 0.0
      self.remote.set_param_value('Remote Tank Height', -1.0)

   def apply_low_level (self, is_low):
      # Set the "remote low level" variable
      if self.is_low_level:
         if not is_low:
            self.remote.set_param_value('Force Low Level', 0)
            log_info('Clearing remotely-forced low level condition.')
            log_event('Tank Monitor', 'The product has dropped below {} inches.'.format(self.config['low_level']))
            self.is_low_level = False
      else:
         if is_low:
            self.remote.set_param_value('Force Low Level', 1)
            log_info('Setting remotely-forced low level condition.')
            log_event('Tank Monitor', 'The product has risen above {} inches.'.format(self.config['low_level']))
            self.is_low_level = True

   def action (self):
      # Are we enabled? If not, don't do anything.
      if not self.config['enabled']:
         if self.is_low_level:
            self.apply_low_level(False)
         self.did_connect = False
         self.remote.set_param_value('Remote Tank Height', -1.0)
         return

      tm = self.connect()
      if not tm or not tm.ok():
         # Couldn't connect to the tank monitor.
         self.did_connect = False
         self.remote.set_param_value('Remote Tank Height', -1.0)
         return

      # Check the tank they've asked us to check.
      tank_id = self.config['tank_id']
      tank, tanks = None, None

      try:
         tanks = tm.get_tank_data()

         show = not len(self.cached_tanks)

         self.cached_tanks = tanks

         # TLS-350 tanks are 1-based, but the list() of tanks is 0-based.
         tank = tanks[tank_id - 1]

         # Show the tanks we got.
         if show:
            for i, t in enumerate(tanks):
               log_debug('   - Found tank {}: {}'.format(i + 1, t['name']))

         log_debug('Checked tank {}.'.format(tank_id))
      except (ValueError, IndexError):
         # Something went wrong when talking to the tank monitor.
         # If it's been a really long time, discard our cached values.
         # In the short term, don't.
         if self.comm_failures > 3:
            self.cached_tanks = []

         self.is_low_level = False
         self.apply_low_level(False)

      if not tank:
         log_debug('Check failed; could not communicate with tank monitor.')
         self.did_connect = False
         self.remote.set_param_value('Remote Tank Height', -1.0)
         return

      self.apply_low_level(tank['height'] < self.config['low_level'])

      self.did_connect = True
      self.cached_reading = tank['height']

      # Send the tank height in inches to the mainboard
      self.remote.set_param_value('Remote Tank Height', tank['height'])

      log_debug('Check complete; tank {} height is {:.1f}.'.format(tank_id, tank['height']))

   def poll (self):
      if time.time() - self.poll_time < self.poll_interval:
         return

      self.action()

      self.poll_time = time.time()

