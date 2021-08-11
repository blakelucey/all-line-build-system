# All-Line Equipment Company

import os
import sys
import json
import time
import datetime

from emailmaker import EmailMaker
from utils import get_path
from logger import *
from eventlog import log_event
from pollsomething import Pollable
from configurable import Configurable

class AlertWatcher (Configurable, Pollable):
   def __init__ (self, remote, ipc, display):
      Configurable.__init__(self, **{
         'file': 'reporting.cfg',
         'context': 'Alerts',
         'key': 'alert',
         'defaults': {
            'enabled': False,
            'recipients': [],
            'text': ''
         }
      })

      self.make_discoverable(ipc)

      Pollable.__init__(self, **{
         'poll_interval': 5.0
      })

      self.remote = remote
      self.ipc = ipc
      self.display = display

      self.did_alarm = False

      self.load()
      self.ipc.add_handler('dismiss_alert', self.ipc_dismiss_alert)
      self.ipc.add_handler('reload_alert', self.ipc_reload_alert)

   def ipc_reload_alert (self, skt, data):
      self.load()
      log_info('Alerting configuration was reloaded.')
      skt.send({
         'reply_to': data['request_type']
      })

   def ipc_dismiss_alert (self, skt, data):
      is_alarm = self.remote.get_param_value('Alarm State') > 0
      if not is_alarm:
         skt.error('System is not in alarm.')
         return

      # Override the alarm using the override parameter.
      self.remote.set_param_value('Alarm Override', 1)

      skt.send({
         'reply_to': data['request_type']
      })

   def make_alert_report (self, custom_text = None):
      if custom_text is None: custom_text = ''

      '''Creates an alert report and sends it off.'''
      if not self.config['enabled']:
         log_info('Alert occurred, but alert emails are disabled.')
         log_event('Alert', 'Alert occurred, but alert emails are disabled.')
         return

      log_info('Creating and sending alert.')

      # Make a new email
      eml = EmailMaker(self.config_file)

      site_name = self.remote.get_param_value('Site Name')
      product_name = self.remote.get_param_value('Product Name')
      serial_number = 'A{}'.format(self.remote.get_param_value('Serial Number'))
      eml.add_recipient(self.config['recipients'])
      eml.set_from('{} <notifier@equipment-notifications.com>'.format(product_name))
      eml.set_subject('Alert from {} ({})'.format(site_name, serial_number))

      now = datetime.datetime.now()
      eml.add_body('This is an <b>alert</b> from the All-Line Equipment {}, serial number {}.<br />'.format(product_name, serial_number))
      eml.add_body('Site name is {}.<br />'.format(site_name))
      external_ip = self.get_external_ip_address()
      if external_ip is not None:
         eml.add_body('IP Address: <a href="http://{}:6144">{}</a><br />'.format(external_ip,external_ip))
      eml.add_body('Generated {}.<br /><br />'.format(now.strftime('%c')))

      alert_text = ''
      if custom_text == '':
         alert_text = self.remote.get_param_value('Alarm Text')
      else:
         alert_text = custom_text
      alert_display = self.display.get_saved_screenshot()
      eml.add_body('<b>Alert message:</b><br />{}<br /><br />'.format(alert_text))
      eml.add_body('<b>Display before alert (tank gauges not shown):</b><br /><pre>{}</pre><br /><br />'.format(alert_display))
      eml.add_body(self.config['text'])

      # Send the email
      eml.send()

   def get_external_ip_address(self):
      import requests
      try:
         ip = requests.get('https://checkip.amazonaws.com',timeout=7).text.strip()
         return ip
      except:
         return None

   def action (self):
      # Check to see if the system is in alarm.
      # If so, prepare an alarm report.
      is_alarm = self.remote.get_param_value('Alarm State') > 0
      if is_alarm:
         if not self.did_alarm:
            self.make_alert_report()
            self.did_alarm = True
      else:
         self.did_alarm = False

