# All-Line Equipment Company

import os
import sys
import json

from shutil import copy2, rmtree
from utils import get_path, generate_email_path
from logger import *
from eventlog import log_event

class EmailMaker:
   def __init__ (self, config_file):
      self.config_file = config_file
      self.sender = None
      self.recipients = []
      self.subject = ''
      self.body = ''
      self.attachments = []

      self.email_dir = generate_email_path()
      os.mkdir(self.email_dir)

   def set_from (self, who):
      self.sender = who

   def add_recipient (self, who):
      '''Adds one or more recipients to the list.'''
      if isinstance(who, list):
         self.recipients += who
      else:
         self.recipients.append(who)

   def set_body (self, text):
      self.body = str(text)

   def add_body (self, text):
      self.body += str(text)

   def set_subject (self, subject):
      self.subject = subject

   def attach (self, filename):
      if not os.path.exists(filename):
         log_info('Can\'t attach {} to email; does not exist.'.format(filename))
         self.body += '(An attachment to this email was not able to be delivered.)'
         return

      basename = os.path.basename(filename)
      self.attachments.append(basename)
      copy2(filename, self.email_dir + basename)

   def get_dir (self):
      return self.email_dir

   def send (self):
      '''Runs the emailer script to send an email in the background.'''

      with open(self.email_dir + 'email.cfg', 'w') as f:
         f.write(json.dumps({
            'to': self.recipients,
            'from': self.sender,
            'subject': self.subject
         }))
         f.flush()

      # Create the text.
      with open(self.email_dir + 'text.txt', 'w') as f:
         f.write(self.body)
         f.flush()

      ext = 'py' if not os.path.exists(get_path('tools') + 'emailer.pyc') else 'pyc'
      os.system('python -B ' + get_path('tools') + 'emailer.{} "{}" "{}" &'.format(ext, self.config_file, self.email_dir))
      log_info('Queued an email to be sent (subject: {})'.format(self.subject))
      log_event('Email', 'Sent an email. (Subject: {})'.format(self.subject))

