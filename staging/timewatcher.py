# All-Line Equipment Company

import os
import sys
import datetime
import time
import stat

from logger import *
from pollsomething import Pollable
from eventlog import log_event

class TimeWatcher (Pollable):
   def __init__ (self, remote, ipc):
      Pollable.__init__(self, **{
         'poll_interval': 5.0
      })

      self.remote = remote
      self.ipc = ipc

      self.ipc.add_handler('set_date_and_time', self.ipc_set_date_and_time)
      self.ipc.add_handler('set_timezone', self.ipc_set_timezone)
      self.ipc.add_handler('set_ntp', self.ipc_set_ntp)

   def ipc_set_timezone (self, skt, data):
      zone_dir = '/usr/share/zoneinfo/uclibc'
      zone = data.get('timezone', None)
      tzfile = '/etc/TZ'

      if not zone:
         skt.error('No timezone provided.')
         return

      if not os.path.exists(zone_dir + '/' + zone):
         # This is not a valid timezone.
         skt.error('Invalid timezone: {}'.format(zone))
         return

      if os.path.exists(tzfile):
         os.remove(tzfile)

      os.symlink(zone_dir + '/' + zone, tzfile)
      log_info('Timezone was set to {}.'.format(zone))

      skt.send({
         'reply_to': data['request_type']
      })

   def ipc_set_ntp (self, skt, data):
      ntp_script = '/etc/init.d/S45ntpd'
      enable = data.get('enabled', None)

      if enable is None:
         skt.error('Missing argument.')
         return

      if not os.path.exists(ntp_script):
         log_error('NTP could not be disabled; the script, {}, is missing.'.format(
            ntp_script
         ))
         skt.error('Missing script.')
         return

      # Stop?
      if not enable:
         os.system(ntp_script + ' stop')
         os.system('killall ntpd')

      # We can configure the script now.
      perms = os.stat(ntp_script).st_mode
      exec_bits = (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

      if enable:
         perms |= exec_bits
      else:
         perms &= ~exec_bits

      os.chmod(ntp_script, perms)
      log_debug('{} NTP startup script.'.format('Enabled' if enable else 'Disabled'))

      # Start/stop?
      check = os.system('pidof ntpd > /dev/null')
      if check != 0:
         # Not running. Start?
         if enable:
            os.system(ntp_script + ' start')

      skt.send({
         'reply_to': data['request_type']
      })

   def ipc_set_date_and_time (self, skt, data):
      if 'iso' in data and '+' in data['iso']:
         # Set using the ISO time
         iso = data['iso']
         iso = iso[:-6]
         try:
            was = datetime.datetime.now()
            dt = datetime.datetime.strptime(iso, '%Y-%m-%dT%H:%M:%S')
            self.set_date_and_time(dt, 'set_local' in data)
            skt.send({
               'reply_to': data['request_type'],
               'time_was': was.strftime('%c'),
               'time_is_now': dt.strftime('%c')
            })
            return
         except ValueError:
            skt.error('Invalid date/time.')
            return

      if not all(k in data for k in ('year', 'month', 'day', 'hour', 'minute', 'second')):
         skt.error('Missing one or more parameters: year, month, day, hour, minute, second')
         return

      try:
         year, month, day, hour, minute, second = \
            data['year'], data['month'], data['day'], data['hour'], data['minute'], data['second']
         was = datetime.datetime.now()
         dt = datetime.datetime(year, month, day, hour, minute, second)
         self.set_date_and_time(dt)
         skt.send({
            'reply_to': data['request_type'],
            'time_was': was.strftime('%c'),
            'time_is_now': dt.strftime('%c')
         })
         return
      except ValueError:
         skt.error('Invalid date/time.')
         return

   def set_date_and_time (self, dt, set_local = False):
      # Change the system date?
      if set_local:
         cmd = ('date +%Y%m%d.%T -s {:04d}{:02d}{:02d}{:02d}{:02d}.{:02d} > /dev/null'.format(
            dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second
         ))
         os.system(cmd)
         log_info('Setting system date/time to {}.'.format(dt.strftime('%c')))

      # Change the mainboard date.
      self.remote.set_date_and_time(dt)

   def action (self):
      # Is the system set up for NTP? If so, set the "Read Only Clock" parameter.
      ntp_script = '/etc/init.d/S45ntpd'
      perms = os.stat(ntp_script).st_mode
      exec_bits = (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
      if (perms & exec_bits) == exec_bits:
         # All of the execute bits are set. NTP is enabled.
         # Tell the mainboard they can't change their time, if we haven't done it yet.
         is_set = self.remote.get_param_value('Read Only Clock')
         if not is_set:
            log_info('Telling the mainboard that it isn\'t allowed to change the date and time.')
            self.remote.set_param_value('Read Only Clock', True)

      else:
         # NTP is not enabled. The mainboard may request a time change on our end using the
         # "Force Clock" parameter.
         is_set = self.remote.get_param_value('Read Only Clock')
         if is_set:
            log_info('Telling the mainboard that it is now allowed to change the date and time.')
            self.remote.set_param_value('Read Only Clock', False)

         # Does the remote system have a new date/time for us?
         if self.remote.get_param_value('Force Clock'):
            # It does.
            log_info('The mainboard insists that its date and time are correct.')
            dt = self.remote.get_date_and_time()
            self.set_date_and_time(dt, set_local = True)

            # Now reset their force parameter and quit.
            self.remote.set_param_value('Force Clock', False)
            return

      # Regular old clock skew check.
      dt = self.remote.get_date_and_time()
      local_dt = datetime.datetime.now()
      one_minute = datetime.timedelta(0, 0, 0, 0, 1)

      if local_dt < dt - one_minute or local_dt > dt + one_minute:
         # Our clock doesn't match closely. Correct it.
         log_debug('System time does not match mainboard time very closely.')

         # Set the time, but don't try to set the local time; it's correct.
         self.set_date_and_time(local_dt, set_local = False)

