# All-Line Equipment Company

import os
import sys
import time
import datetime
import csv
from collections import OrderedDict
from tempfile import NamedTemporaryFile
import shutil
import traceback

import validators

from logger import *
from eventlog import log_event
from utils import *
from pollsomething import Pollable
from configurable import Configurable

class RecordStorage (Configurable, Pollable):
   PeekRecord = 0
   PopRecord = 1
   EraseRecord = 2
   ClearAllRecords = 3

   def __init__ (self, remote, tank_monitor, alert_watcher, ipc):
      #maaaaaaaan this is gross
      Configurable.__init__(self, **{
         'file': 'reporting.cfg',
         'context': 'Statistics',
         'key': 'statistics',
         'defaults': {
            "min_bio_tank_reading": 10.0,
            "min_bio_tank_reading_stats": 10.0,
            "bio_error_ignore": 0.2,
            "bio_error_warn": 0.1,
            "max_bad_bio_records": 3,
            "min_dsl_tank_reading": 10.0,
            "min_dsl_tank_reading_stats": 10.0,
            "dsl_error_ignore": 0.2,
            "dsl_error_warn": 0.1,
            "max_bad_dsl_records": 3,
            "min_blend_tank_reading": 10.0,
            "min_blend_tank_reading_stats": 10.0,
            "blend_error_ignore": 0.2,
            "blend_error_warn": 0.1,
            "max_bad_blend_records": 3,
            "diesel_tanks": []
         },
         'types': {
               "min_bio_tank_reading": float,
               "min_bio_tank_reading_stats": float,
               "bio_error_ignore": float,
               "bio_error_warn": float,
               "max_bad_bio_records": int,
               "min_dsl_tank_reading": float,
               "min_dsl_tank_reading_stats": float,
               "dsl_error_ignore": float,
               "dsl_error_warn": float,
               "max_bad_dsl_records": int,
               "min_blend_tank_reading": float,
               "min_blend_tank_reading_stats": float,
               "blend_error_ignore": float,
               "blend_error_warn": float,
               "max_bad_blend_records": int
         },
         'validators': {
            'min_bio_tank_reading': {
               'function': validators.validate_float,
               'arguments': {'minimum': 0, 'maximum': 1000}
            },
            'min_bio_tank_reading_stats': {
               'function': validators.validate_float,
               'arguments': {'minimum': 0, 'maximum': 1000}
            },
            'bio_error_ignore': {
               'function': validators.validate_float,
               'arguments': {'minimum': 0, 'maximum': 1}
            },
            'bio_error_warn': {
               'function': validators.validate_float,
               'arguments': {'minimum': 0, 'maximum': 1}
            },
            'max_bad_bio_records': {
               'function': validators.validate_int,
               'arguments': {'minimum': 1, 'maximum': 1000}
            },
            'min_dsl_tank_reading': {
               'function': validators.validate_float,
               'arguments': {'minimum': 0, 'maximum': 1000}
            },
            'min_dsl_tank_reading_stats': {
               'function': validators.validate_float,
               'arguments': {'minimum': 0, 'maximum': 1000}
            },
            'dsl_error_ignore': {
               'function': validators.validate_float,
               'arguments': {'minimum': 0, 'maximum': 1}
            },
            'dsl_error_warn': {
               'function': validators.validate_float,
               'arguments': {'minimum': 0, 'maximum': 1}
            },
            'max_bad_dsl_records': {
               'function': validators.validate_int,
               'arguments': {'minimum': 1, 'maximum': 1000}
            },
            'min_blend_tank_reading': {
               'function': validators.validate_float,
               'arguments': {'minimum': 0, 'maximum': 1000}
            },
            'min_blend_tank_reading_stats': {
               'function': validators.validate_float,
               'arguments': {'minimum': 0, 'maximum': 1000}
            },
            'blend_error_ignore': {
               'function': validators.validate_float,
               'arguments': {'minimum': 0, 'maximum': 1}
            },
            'blend_error_warn': {
               'function': validators.validate_float,
               'arguments': {'minimum': 0, 'maximum': 1}
            },
            'max_bad_blend_records': {
               'function': validators.validate_int,
               'arguments': {'minimum': 1, 'maximum': 1000}
            },
            'diesel_tanks': {
               'function': validators.validate_ints
            }
         }
      })

      self.make_discoverable(ipc)

      Pollable.__init__(self, **{
         'poll_interval': 2.5
      })

      self.remote = remote
      self.tank_monitor = tank_monitor
      self.alert_watcher = alert_watcher
      self.ipc = ipc

      self.fields = []
      self.header = ''

      self.num_tank_fields = 16
      self.tank_fields = []
      self.tank_names = []

      self.collect()

      #calibration record stuff
      #self.cal_collect()
      self.cal_headers = []
      self.cal_values = []
      self.cal_tank_fields_first = []
      self.cal_tank_names_first = []
      self.cal_tank_fields_before = []
      self.cal_tank_names_before = []
      self.cal_tank_fields_after = []
      self.cal_tank_names_after = []

      #stat bio tank stuff
      self.number_of_stat_tanks = 3
      self.prev_tank_levels = [-1]*self.number_of_stat_tanks
      self.curr_tank_levels = [-1]*self.number_of_stat_tanks
      self.bad_record_counter = [0]*self.number_of_stat_tanks

      self.load()

      self.ipc.add_handler('get_record_fields', self.ipc_get_record_fields)
      self.ipc.add_handler('delete_record_file', self.ipc_delete_record_file)

   def ipc_delete_record_file (self, skt, data):
      filename = data.get('file', None)
      month = data.get('month', None)
      year = data.get('year', None)
      who = data.get('user', None)
      if None in (filename, month, year, who):
         skt.error('Missing filename, month, year or user.')
         return

      if '/' in filename:
         skt.error('Filename must not contain path separators.')
         return

      # Build the real filename
      real_path = self.get_file_path() + filename
      if not os.path.exists(real_path):
         skt.error('File does not exist: {}'.format(real_path))
         return

      # Looks OK. Try to delete it.
      os.remove(real_path)

      # Report OK and log it.
      log_info('User requested deletion of {}.'.format(real_path))
      log_event('Records', 'Records from {} of {} were deleted by {}.'.format(
         month, year, who
      ))
      skt.send({
         'reply_to': data['request_type'],
         'error': False
      })

   def ipc_get_record_fields (self, skt, data):
      skt.send({
         'reply_to': data['request_type'],
         'fields': self.fields
      })

   def collect (self):
      '''Collect information about the record fields, their types, and their descriptions.'''
      num_fields = self.remote.get_param_value('Number of Fields')
      self.fields = []

      for f in xrange(num_fields):
         name = self.remote.get_param_value('Fields', f)
         field = {
            'name': name,
            'type': self.remote.get_param_value('Field Type Strings', f),
            'type_id': self.remote.get_param_value('Field Types', f),
            'description': self.remote.get_param_value('Field Descriptions', f)
         }

         log_debug('Collected field {} ({}, {}).'.format(field['name'], field['type'], field['description']))
         self.fields.append(field)

      # Also collect the header.
      self.header = self.remote.get_param_value('Record Headers')

   def cal_collect (self,final):
      '''Collect information about the record fields, their types, and their descriptions.'''
      num_fields = self.remote.get_param_value('Number of Calibration Headers')
      log_debug('CALIBRATION FIELDS {}.'.format(num_fields))
      self.cal_headers = []
      self.cal_values = []

      for f in xrange(num_fields):
         self.cal_headers.append(self.remote.get_param_value('Calibration Record Headers', f))
         self.cal_values.append(self.remote.get_param_value('Calibration Record Values', f))
         
         field = {
            'name': self.remote.get_param_value('Calibration Record Headers', f),
            'value': self.remote.get_param_value('Calibration Record Values', f)
         }
         log_debug('Calibration Collected field ({} , {}).'.format(field['name'], field['value']))

      log_debug('Calibration Headers: {} ... Values {}'.format(self.cal_headers,self.cal_values))

      for tank in xrange(len(self.cal_tank_names_after)):
         self.cal_headers.append(self.cal_tank_names_after[tank])
         if final:
            self.cal_values.append(self.cal_tank_fields_first[tank]+' -> '+self.cal_tank_fields_after[tank])
         else:
            self.cal_values.append(self.cal_tank_fields_before[tank]+' -> '+self.cal_tank_fields_after[tank])



   def find_field_by_type (self, ftype):
      for i in xrange(len(self.fields)):
         if self.fields[i]['type'] == ftype.upper():
            return i

      return -1

   def find_field (self, id, match_prefix = False):
      for i in xrange(len(self.fields)):
         if match_prefix:
            if self.fields[i]['name'].startswith(id.upper()):
               return i
         else:
            if self.fields[i]['name'] == id.upper():
               return i

      return -1

   def get_date_field_id (self):
      '''Look at the field information for the date and return the date field ID.'''
      return self.find_field_by_type('DATE')

   def get_time_field_id (self):
      '''Look at the field information for the date and return the time field ID.'''
      return self.find_field_by_type('TIME')

   def get_header_file_name (self):
      return get_path('config') + 'headers.txt'

   def get_file_name (self, record):
      '''Look at the field information for the date and build a file name from it.'''
      def_name = 'LOSTANDFOUND.CSV'
      date_field_num = self.get_date_field_id()
      time_field_num = self.get_time_field_id()
      invalid_date = '01/01/2000'
      invalid_time = '00:00'
      now = datetime.datetime.now()
      if date_field_num < 0:
         return def_name

      try:
         #fields = record.split(',')
         fields = [f for f in csv.reader([record])][0]
         m, d, y = (int(x) for x in fields[date_field_num].split('/'))

         # Are these the standard invalid date? If so, try and use our local date.
         # The save_single_record method does this as well.
         if fields[date_field_num] == invalid_date and fields[time_field_num] == invalid_time:
            fields[date_field_num] = now.strftime('%m/%d/%Y')
            fields[time_field_num] = now.strftime('%H:%M')
            m, d, y = now.month, now.day, now.year

         if y < 2000: y += 2000
         dt = datetime.date(y, m, d)
         return dt.strftime('%b_%Y').upper() + '.CSV'
      except (IndexError, ValueError):
         return def_name

   def get_current_record_file (self):
      '''Returns the filename of the record file that would be written to right now.'''
      dt = datetime.datetime.now()
      return dt.strftime('%b_%Y').upper() + '.CSV'

   def get_file_path (self):
      '''Returns the path for permanent record storage.'''
      return get_path('records')

   def register_callbacks (self):
      pass

   def set_tank_field (self, index, name, volume):
      self.tank_fields[index] = volume
      self.tank_names[index] = name

   def transform_record (self, record):
      '''Takes a record from the mainboard, fixes the date and time, and adds in extra fields.'''

      date_field        = 2
      time_field        = 3

      fields = [f for f in csv.reader([record.strip()])][0]
      log_debug('Field data: {}'.format(fields))

      # The last field is always the status.
      # What we'll do is replace the date and time with our own.
      # Then we'll stuff the extra fields in right before the status field.

      now = datetime.datetime.now()
      fields[date_field] = now.strftime('%m/%d/%Y')
      fields[time_field] = now.strftime('%H:%M')

      # Set up unpopulated tank fields.
      while len(self.tank_fields) < self.num_tank_fields:
         self.tank_fields.append('--')
         self.tank_names.append('--')

      # Combine with tank fields.
      fields = fields + self.tank_fields

      # Turn it back into a string.
      return ','.join(['"{}"'.format(f) for f in fields])

   def check_headers (self):
      '''Checks if the header data is in sync with the provided headers.'''

      # Headers from the mainboard.
      headers = [item for item in csv.reader([self.header.strip()])][0]

      # Plus our extra headers.
      headers = headers + self.tank_names

      filename = self.get_header_file_name()
      new = ','.join(['"{}"'.format(h) for h in headers])

      if os.path.exists(filename):
         current = open(filename, 'r').read()
      else:
         current = ''

      if new != current:
         # Save new headers.
         with open(filename, 'w') as f:
            f.write(new)
         log_info('Record headers were not in sync. They\'ve been updated.')

      else:
         log_info('Record headers are in sync.')

      check_mode(filename)

   def save_single_record (self, record):
      '''Saves the record to permanent storage; returns False on failure, True otherwise.'''
      # We are NOT going to use this directly from the mainboard.
      # We're going to split it into fields, use our own local date and time,
      # and insert extra data from the tank monitor.
      record = self.transform_record(record)

      # Don't record?
      if not record: return True

      # Generate a file name.
      filename = self.get_file_name(record)
      path = self.get_file_path()
      filename = path + filename

      # Save the data.
      with open(filename, 'a') as f:
         f.write(record.strip())
         f.write('\r\n')
         f.flush()

      # Check this file's permissions.
      check_mode(filename)

      # And the headers.
      self.check_headers()

      try:
         self.create_stats(record)
      except Exception as e:
         log_error('Something went wrong while creating the tank stats: {}'.format(traceback.format_exc()))
         log_info('System still running')

      # probably do the umm... bio tank statistics thing here

      return True

   def save_cal_record (self):
      path = '/config/records/calibration/'
      filename = 'CALIBRATION_REC.CSV'
      file_path = path+filename
      if not os.path.exists(path):
         os.makedirs(path)
      
      if not os.path.exists(file_path):
         with open(file_path, 'wb') as csvfile:
            writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_ALL)
            writer.writerow(self.cal_headers)
            writer.writerow(self.cal_values)
            csvfile.close()
      else:
         tempfile = NamedTemporaryFile('wb', delete=False)
         with open(file_path, 'r') as csvfile, tempfile:
            inputfile = csv.reader(csvfile, delimiter=',', quoting=csv.QUOTE_ALL)
            outputfile = csv.writer(tempfile, delimiter=',', quoting=csv.QUOTE_ALL)

            outputfile.writerow(self.cal_headers)
            next(inputfile)
            for row in inputfile:
                  outputfile.writerow(row)
            outputfile.writerow(self.cal_values)
            csvfile.close()
         #copy over the permissions from the original file before moving it or else php will yell at me
         shutil.copymode(file_path, tempfile.name)
         shutil.move(tempfile.name, file_path)

   def clear_records (self):
      self.remote.get_param_value('Record Storage', self.ClearAllRecords, '')

   def get_record_count (self):
      '''Ask the remote system how many records it has in storage yet to be retrieved.'''

      # Use a default value of 0 (the last argument)
      return self.remote.get_param_value('Number of Records', 0, 0)

   def get_single_record (self, erase = True):
      '''Ask the remote system for a single record from storage; optionally deletes it from storage if erase == True.'''

      sub_id = self.PeekRecord if not erase else self.PopRecord

      return self.remote.get_param_value('Record Storage', sub_id, '')

   def erase_single_record (self):
      '''Ask the remote system to delete a single record from storage.'''
      self.remote.get_param_value('Record Storage', self.EraseRecord)

   def get_records_from_today (self):
      '''Return a dict containing the headers and a list of records from today only.'''
      filename = self.get_file_path() + self.get_current_record_file()
      date_field_num = self.get_date_field_id()
      result = {
         'time': datetime.datetime.now(),
         'header': self.header,
         'filename': filename,
         'records': []
      }

      if not os.path.exists(filename):
         return result

      with open(filename, 'r') as f:
         for lineno, record in enumerate(f):
            if record.startswith(self.header):
               # This is the header.
               continue

            try:
               fields = record.split(',')
               m, d, y = (int(x) for x in fields[date_field_num].split('/'))
               if y < 2000: y += 2000
               dt = datetime.date(y, m, d)

               # Is this today?
               if dt == datetime.datetime.today().date():
                  result['records'].append(record.strip())
            except (IndexError, ValueError):
               # Skip this record, it's weird.
               log_info('Found a noncompliant record at line {} in {}.'.format(lineno, filename))
               continue

      return result

   def mix_in_tank_data (self, ordinal, rec="nothing"):
      # Try to grab tank information.
      tm = self.tank_monitor.connect()

      #self.tank_fields = []
      #self.tank_names = []
      tank_fields = []
      tank_names = []

      if tm and tm.socket:
         tanks = tm.get_tank_data()

         try:
            for tank in tanks:
               tank_names.append('TANK: ' + tank['name'].upper() + " (Vol)")
               tank_fields.append('{:.2f}'.format(tank['volume']))
               tank_names.append('TANK: ' + tank['name'].upper() + " (Temp)")
               tank_fields.append('{:.2f}'.format(tank['temperature']))
            if (ordinal==0):
               self.tank_fields = tank_fields
               self.tank_names = tank_names
            if (ordinal==1):
               self.cal_tank_fields_first = tank_fields
               self.cal_tank_names_first = tank_names
            if (ordinal==2 or ordinal==1):
               self.cal_tank_fields_before = tank_fields
               self.cal_tank_names_before = tank_names
            if (ordinal==3):
               self.cal_tank_fields_after = tank_fields
               self.cal_tank_names_after = tank_names
         except AttributeError:
            log_error('Attribute error while checking tank data.')

   def create_stats(self, record):
      path = '/config/records/stats/'
      filename = self.get_current_record_file()

      log_debug('config: {}'.format(self.config))

      tank_config = self.tank_monitor.config
      if not tank_config.get('enabled', False):
         return

      # gather the tank level data (even though they were probably just asked about it for the records...)
      try:
         tm = self.tank_monitor.connect()
      except:
         log_error('An error occured when trying to connect ot the tank monitor for statistics!... {}'.format(traceback.format_exc()))
         return

      try:
         fields = [f for f in csv.reader([record.strip()])][0]
         bio_meter_total = float(fields[self.find_field('total bio meter')])
         dsl_meter_total = float(fields[self.find_field('total main meter')])
         #the three below are used for the blend calculation
         bio_total = float(fields[self.find_field('total bio')])
         dsl_total = float(fields[self.find_field('total main')])
         blend_result_str = fields[self.find_field('result')]
         blend_result = 0
         if blend_result_str != '':
            blend_result = float(blend_result_str)
         any_delivery = 0
         totalizing_meter = self.remote.get_param_value('Totalizing Meter')
         if (totalizing_meter):
            dsl_meter_total = dsl_meter_total - bio_meter_total
            dsl_total = dsl_total - bio_total
         record_date = fields[self.get_date_field_id()]
         record_time = fields[self.get_time_field_id()]
         incoming_line = [record_date,record_time]
         log_debug('BMT: {} DMT: {} BT: {} DT: {} BR: {} RD: {} RT: {} TM: {}'.format(bio_meter_total,dsl_meter_total,bio_total,dsl_total,blend_result,record_date,record_time,totalizing_meter))

      except:
         log_error('Could not locate the total bio/diesel meter, record date, or record time value/s... {}'.format(traceback.format_exc()))
         return
      
      # start for loop here
      for i in range(self.number_of_stat_tanks):
         meter_total = 0
         if i == 0: 
            config_name = 'bio'
            config_name_long = 'bio'
            meter_total = bio_meter_total
         if i == 1:
            config_name = 'dsl'
            config_name_long = 'diesel'
            meter_total = dsl_meter_total
         if i == 2:
            config_name = 'blend'
            if (bio_total+dsl_total)!=0:
               meter_total = bio_total/(bio_total+dsl_total)

         minimum_tank_range = self.config['min_'+config_name+'_tank_reading']
         minimum_tank_range_stats = self.config['min_'+config_name+'_tank_reading_stats']
         minimum_error_range_for_ignoring = self.config[config_name+'_error_ignore']
         minimum_error_range_for_warning = self.config[config_name+'_error_warn']
         max_bad_records = self.config['max_bad_'+config_name+'_records']
         tank_names = ''
         delivery_in_progress = 0
         tank_volume_diff = 0
         threshold_tank_volume_diff = 0
         tank_error = 0
         record_tag = 'NULL'
         
         if tm and tm.socket and i!=2:
            try:
               self.prev_tank_levels[i] = self.curr_tank_levels[i]
               self.curr_tank_levels[i] = 0
               if i==0:
                  the_tank = tm.get_tank_data(tank_config['tank_id'])
                  self.curr_tank_levels[i] += float(the_tank['volume'])
                  tank_names += the_tank['name']+'. '
                  delivery_in_progress = the_tank['delivery_in_progress']
                  any_delivery+=int(delivery_in_progress)
                  log_debug(config_name+' TANK {} volume: {} delivery?: {}'.format(the_tank['name'],the_tank['volume'],the_tank['delivery_in_progress']))
               elif i==1:
                  for tank in self.config['diesel_tanks']:
                     the_tank = tm.get_tank_data(tank)
                     self.curr_tank_levels[i] += float(the_tank['volume'])
                     tank_names += the_tank['name']+'. '
                     delivery_in_progress = the_tank['delivery_in_progress']
                     any_delivery+=int(delivery_in_progress)
                     log_debug(config_name+' TANK {} volume: {} delivery?: {}'.format(the_tank['name'],the_tank['volume'],the_tank['delivery_in_progress']))

               tank_volume_diff = self.prev_tank_levels[i] - self.curr_tank_levels[i]
               threshold_tank_volume_diff = tank_volume_diff
            except:
               log_error('An error occured when trying gather the tank volume/s!... {}'.format(traceback.format_exc()))
               return

         if (i==2):
            blend_tank = 0 # have the blend threshold tank stuff go off of the bio tank
            self.prev_tank_levels[i] = self.prev_tank_levels[blend_tank]
            self.curr_tank_levels[i] = self.curr_tank_levels[blend_tank]
            threshold_tank_volume_diff = self.prev_tank_levels[i] - self.curr_tank_levels[i]
            try:
               tank_volume_diff = (self.prev_tank_levels[0] - self.curr_tank_levels[0])/((self.prev_tank_levels[0] - self.curr_tank_levels[0])+((self.prev_tank_levels[1] - self.curr_tank_levels[1])))
            except ZeroDivisionError:
               tank_volume_diff = 1
            delivery_in_progress = any_delivery
            tank_names = 'Blend'

         '''
         if os.path.exists('/config/debug'):
            threshold_tank_volume_diff=12
            if(i==1):
               tank_volume_diff=48
            elif(i==2):
               tank_volume_diff=0.2
            else:
               tank_volume_diff=12
         '''

         log_debug('{} TANK PREV: {} TANK CURR: {}'.format(config_name.upper(),self.prev_tank_levels[i], self.curr_tank_levels[i]))
         # exit early if this is the first record (there should probably be other early exits if the system has been turned off for a period of time? maybe...)
            

         # go through and do the percent error based on the threshold stuff,
         # for blend, the tank_volume_diff is treated as blend in the tank and the
         # meter_total is treated as the blend of our unit
         if (tank_volume_diff==0): tank_volume_diff+=0.001
         if (threshold_tank_volume_diff < -1*minimum_tank_range or int(delivery_in_progress)>0):
            tank_error = (meter_total-tank_volume_diff)/tank_volume_diff
            record_tag = 'delivery('+str(delivery_in_progress)+')~'
            tank_volume_diff = abs(tank_volume_diff)*-1
            #self.track_bad_record(0)
            #delivery occured? (probably) toss into the bad_month_year.CSV file increment the bad_bio_record_counter only to the oldest bad record

         elif (threshold_tank_volume_diff > minimum_tank_range):
            tank_error = (meter_total-tank_volume_diff)/tank_volume_diff
            if tank_error > minimum_error_range_for_ignoring or tank_error < -1*minimum_error_range_for_ignoring:
               record_tag = 'unkown~'
               #this is a bad record, toss it into the bad record file and track it
            else:
               record_tag = 'good~'
               #this is a good enough record, toss it into the normal month_year.CSV file
            if tank_error > minimum_error_range_for_warning or tank_error < -1*minimum_error_range_for_warning:
               #magnitude=round(abs(bio_tank_error)/minimum_error_range_for_warning)*-1     #no longer care about the magnitude of the bad record
               # so yes... gross, but it works....
               if (i==2 and (self.prev_tank_levels[0]==-1 or self.prev_tank_levels[1]==-1)):
                  pass
               else:
                  self.track_bad_record(i,config_name)
            else:
               self.bad_record_counter[i] = 0

         else:
            record_tag = 'insufficient tank movement~'
            tank_error = (meter_total-tank_volume_diff)/tank_volume_diff
            #self.track_bad_record(0)
            #negligible record (bio tank level did not move much at all, so throw it into bad_month_year.CSV as negligible)
            # increment the bad_bio_record_counter to clear the oldest bad record

         #debugging stuff
         #if os.path.exists('/config/debug'):
         #  self.track_bad_record(-4)
            #record_tag=''
            #filename = self.get_current_record_file()
            #tank_error = meter_total/100
         
         # yeah this is gross, but it basically makes sure the front-end php code doesn't pick up on missing bio/diesel tank monitor records
         if (self.prev_tank_levels[i] == -1) or (i==2 and (self.prev_tank_levels[0]==-1 or self.prev_tank_levels[1]==-1)):
            tank_volume_diff = -1
            tank_error = -1
         
         record_tag = record_tag+' '+tank_names+' tank: '+str(tank_volume_diff)+' meter: '+str(meter_total)
         file_path = path+filename
         log_info('Stats: {} ---> error: {}'.format(record_tag,tank_error))
         incoming_line.append(str(tank_error))
         incoming_line.append(str(tank_volume_diff))

      try:
         if not os.path.exists(path):
            os.makedirs(path)
         if not os.path.exists(file_path):
            with open(file_path, 'wb') as csvfile:
                  writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_ALL)
                  writer.writerow(incoming_line)
                  csvfile.close()

         else:
            with open(file_path, 'a') as csvfile:
                  writer = csv.writer(csvfile, delimiter=',', quoting=csv.QUOTE_ALL)
                  writer.writerow(incoming_line)
                  csvfile.close()

      except:
         log_error('Could not write to the statistics filepath: {}... {}'.format(file_path,traceback.format_exc()))
         log_info('System still running')

   def track_bad_record (self, tank_selector, tank_name):
      self.bad_record_counter[tank_selector]+=1
      if self.bad_record_counter[tank_selector] >= self.config['max_bad_'+tank_name+'_records']:
         message = ('A significant difference in tank level readings and '+tank_name+'-meter readings has been detected after '
                     +str(self.config['max_bad_'+tank_name+'_records'])+ ' records in a row (greater than '+str(self.config[tank_name+'_error_warn'])+' error)'
                     +'<br>Check the most recent records of this unit for more information')
         self.alert_watcher.make_alert_report(message)
         log_debug('EMAIL SOMEBODY ('+tank_name+' meter reading is way off)')
         self.bad_record_counter[tank_selector] = 0
      log_info(tank_name+' tank meter/tank level mismatch (count: {}, {}) (max: {})'.format(self.bad_record_counter[tank_selector], type(self.bad_record_counter[tank_selector]), self.config['max_bad_'+tank_name+'_records']))


   def action (self):
      '''Periodically check the number of records available. If there are some, simply chuck them into the transaction files.'''

      count = self.get_record_count()

      cal_state = self.remote.get_param_value('Calibration State')
      if (cal_state==1 or cal_state==4):
         final = 1 if cal_state==4 else 0
         try:
            config = self.tank_monitor.config
            if config.get('enabled', False):
               self.mix_in_tank_data(3)
            self.cal_collect(final)
            self.save_cal_record()
         except Exception as e:
            log_error('An error occured when trying to create the calibration record!... {}'.format(traceback.format_exc()))
            log_info('System still running')
         self.remote.set_param_value('Calibration State', 0)
      elif (cal_state==2 or cal_state==3):
         #record tank volume for the "tank volume before" paramter
         try:
            # We need to mix in the tank information with these records.
            config = self.tank_monitor.config
            if config.get('enabled', False):
               if (cal_state==2):
                  self.mix_in_tank_data(2)
               else:
                  self.mix_in_tank_data(1)
            else:
               self.cal_tank_fields_first = []
               self.cal_tank_names_first = []
               self.cal_tank_fields_before = []
               self.cal_tank_names_before = []
               self.cal_tank_fields_after = []
               self.cal_tank_names_after = []

         except (KeyError, ValueError, IndexError) as e:
            log_error('Something went wrong while checking tank monitor data for calibration: {}'.format(traceback.format_exc()))
            log_info('System still running')
            pass

         self.remote.set_param_value('Calibration State', 0)

      # Is the count something impossible?
      if count > 256:
         log_error('Bad record count; asking controller to reinitialize storage.')
         return

      if count:
         log_info('Saving {} records to storage.'.format(count))
      else:
         return

      iters = 0
      first = True
      while count > 0:
         rec = self.get_single_record()

         try:
            config = self.tank_monitor.config
            if first and config.get('save_history', False) and config.get('enabled', False):
               # We need to mix in the tank information with these records.
               self.mix_in_tank_data(0,rec)
               first = False
         except (KeyError, ValueError, IndexError) as e:
            log_error('Something went wrong while checking tank monitor data: {}'.format(traceback.format_exc()))
            pass

         self.save_single_record(rec)

         # Instead of counting down, ask the system for the new count.
         count = self.get_record_count()
         iters += 1

         # Did this go nuts?
         if iters > 256:
            # It sure did.
            break

