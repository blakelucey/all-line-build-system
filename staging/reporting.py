# All-Line Equipment Company

import os
import sys
import json
import atexit
import datetime

import validators

from emailmaker import EmailMaker
from shutil import copy2, rmtree
from utils import get_path, generate_email_path
from logger import *
from eventlog import log_event
from configurable import Configurable
from pollsomething import Pollable

class Reporting (Configurable, Pollable):
   def __init__ (self, remote, storage, ipc):
      Configurable.__init__(self, **{
         'file': 'reporting.cfg',
         'context': 'Reporting',
         'key': 'reporting',
         'defaults': {
            'enabled': False,
            'when': '23:55',
            'recipients': [],
            'limit': False,
            'text': 'Daily report is attached.'
         },
         'validators': {
            'when': validators.validate_time,
            'recipients': {
               'function': validators.validate_emails,
               'arguments': {'limit': 6}
            }
         }
      })

      Pollable.__init__(self, **{
         'poll_interval': 30.0
      })

      self.make_discoverable(ipc)

      self.remote = remote
      self.storage = storage
      self.ipc = ipc

      self.cron_file = get_path('cron') + 'root'

      # Register an exit function to stop crond
      atexit.register(self.stop_cron)

      self.load()
      self.ipc.add_handler('reload_reporting', self.ipc_reload_reporting)
      self.ipc.add_handler('make_report', self.ipc_make_report)

   def __del__ (self):
      self.stop_cron()

   def post_save (self):
      self.post_load()

   def post_load (self):
      if ':' not in self.config['when']:
         self.config['when'] = self.defaults['when']

      hour, minute = [int(str(x)) for x in self.config['when'].split(':')]
      log_info('Writing cron file {}.'.format(self.cron_file))

      # Build the crontab file, or clear it
      if self.config['enabled']:
         log_info('Report will trigger at {:02d}:{:02d} every day.'.format(hour, minute))
         with open(self.cron_file, 'w') as f:
            f.write(self.create_cron_line(hour, minute))
            f.flush()
      else:
         log_info('Reporting is disabled.')
         with open(self.cron_file, 'w') as f:
            f.flush()

      # Restart BusyBox' crond
      self.restart_cron()

   def stop_cron (self):
      log_info('Stopping crond.')
      os.system('pidof crond >/dev/null 2>&1 && /etc/init.d/S30crond stop > /dev/null')

   def restart_cron (self):
      log_debug('Restarting crond.')
      if os.path.exists('/usr/sbin/crond') and os.path.exists('/etc/init.d/S30crond'):
         os.system('/etc/init.d/S30crond restart > /dev/null')

   def ipc_make_report (self, skt, data):
      '''Creates and uploads/emails a report using the submission system.'''
      if not self.config['enabled']:
         log_info('Report requested, but reporting is disabled.')
         skt.error('Reporting is disabled.')
         return

      log_info('Creating and sending report.')
      log_event('Reporting', 'Creating and sending report on schedule.')

      # Make a new email
      eml = EmailMaker(self.config_file)
      empty = True

      if self.config['limit']:
         # Find only records from today.
         records = self.storage.get_records_from_today()
         filename = get_path('temp') + records['time'].strftime('%b_%d_%Y').upper() + '.CSV'
         if len(records['records']):
            with open(filename, 'w') as f:
               f.write(records['header'] + '\r\n')
               for record in records['records']:
                  f.write(record + '\r\n')
               f.flush()
            copy2(filename, eml.get_dir())
            log_info('Attaching only today\'s records to report ({} records).'.format(len(records['records'])))
            empty = False
         else:
            log_info('Attaching only today\'s records, but there aren\'t any.')
      else:
         # Find the current month, if it exists.
         storage_path = self.storage.get_file_path()
         filename = self.storage.get_current_record_file()
         if os.path.exists(storage_path + filename):
            log_info('Attaching {} to report.'.format(filename))
            eml.attach(storage_path + filename)
            empty = False
         else:
            log_info('No records found for current month.')

      # Create the email information file.
      site_name = self.remote.get_param_value('Site Name')
      product_name = self.remote.get_param_value('Product Name')
      serial_number = 'A{}'.format(self.remote.get_param_value('Serial Number'))
      eml.add_recipient(self.config['recipients'])
      eml.set_from('{} <notifier@equipment-notifications.com>'.format(product_name))
      eml.set_subject('Report from {} ({})'.format(site_name, serial_number))

      now = datetime.datetime.now()
      eml.add_body('This is a report from the All-Line Equipment {}, serial number {}.<br />'.format(product_name, serial_number))
      eml.add_body('Site name is {}.<br />'.format(site_name))
      eml.add_body('Generated {}.<br /><br />'.format(now.strftime('%c')))
      eml.add_body(self.config['text'])

      if empty:
         eml.add_body('<br /><br />No data to attach. There are no records from {}.'.format(
            'today' if self.config['limit'] else 'the current month'
         ))

      # Send the email and a response over IPC.
      eml.send()
      skt.send({
         'reply_to': data['request_type']
      })

   def ipc_reload_reporting (self, skt, data):
      log_debug('Reporting configuration was reloaded by remote request.')
      self.load()
      skt.send({
         'reply_to': data['request_type']
      })

   def create_cron_line (self, hour, minute):
      # hour, minute get flipped in crontab
      return '{} {} * * * /program/tools/ipc_request.sh make_report'.format(
         minute, hour
      )

   def action (self):
      result = os.system('pidof crond >/dev/null 2>&1')
      if result != 0:
         # crond is not running; restart it.
         log_debug('crond was not running; it has been restarted.')
         self.restart_cron()

