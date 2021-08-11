#!/usr/bin/python
#
# All-Line Equipment Company
# Email Sender
#
# New and Improved!
#     -- Steven Hidy Feb 2018
#
# This program takes two arguments:
#
#     emailer.py <configfile> <emaildir>
#
# <configfile> is a JSON file that must include, at minimum, these settings:
#
#     "smtp": {
#        "server": "hostname or ip"
#        "port": "port"
#        "username": "who"
#        "password": "pass"
#        "all_line_smtp": true|false
#     }
#
# This program requires that the SMTP server accept EHLO, STARTTLS and a login.
#
# <emaildir> contains the following:
#
#     "email.cfg" is the meta information, as JSON:
#        "to": ["recipient", ...]
#        "from": "who"
#        "subject": "what"
#     "text.txt" is the text of the email (can include HTML)
#     Other files to be attached to the email as-is
#
# Generally <emaildir> is somewhere in RAM, like /dev/shm/<random-id>
#
# Enjoy!

import base64
import os
import re
import time
import sys
import json

from email.utils import formataddr
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from mimetypes import guess_type
from email.encoders import encode_base64
from smtplib import SMTP
from shutil import rmtree

def exit_program (is_error, message = 'Unknown error.'):
   data = {
      'error': is_error,
      'message': message
   }
   print json.dumps(data).strip()
   sys.exit(1)

def read_config (filename):
   if not os.path.exists(filename):
      exit_program(True, 'Missing configuration file.')

   try:
      config = json.loads(open(filename, 'r').read())

      if 'smtp' not in config:
         exit_program(True, 'Missing configuration key "smtp".')

      config = config['smtp']

      return {
         'server': str(config['server']),
         'port': int(str(config['port'])),
         'username': str(config['username']),
         'password': str(config['password']),
         'all_line_smtp': config['all_line_smtp']
      }
   except:
      exit_program(True, 'Error in configuration file {}.'.format(filename))

def compose_email (config_file, email_dir):
   email_dir.rstrip('/')
   config = read_config(config_file)

   # Use the All-Line server?
   if config['all_line_smtp']:
      config['server'] = 'smtp.gmail.com'
      config['port'] = 587
      config['username'] = 'notifier@equipment-notifications.com'
      config['password'] = 'thisisaverycomplexpassword'

   if not len(config['server']):
      exit_program(True, 'SMTP definition is invalid.')

   if not os.path.isdir(email_dir):
      exit_program(True, 'Email directory provided, but does not exist.')

   # We need the following files: email.cfg, text.txt
   email_cfg = '{}/{}'.format(email_dir, 'email.cfg')
   if not os.path.exists(email_cfg):
      exit_program(True, 'Email directory does not contain email.cfg.')

   text_txt = '{}/{}'.format(email_dir, 'text.txt')
   if not os.path.exists(text_txt):
      exit_program(True, 'Email directory does not contain text.txt.')

   try:
      email_cfg = json.loads(open(email_cfg, 'r').read())
   except ValueError:
      exit_program(True, 'email.cfg is not valid JSON.')

   if 'to' not in email_cfg or \
      'from' not in email_cfg or \
      'subject' not in email_cfg:
      exit_program(True, 'email.cfg is missing "to", "from" or "subject"')

   # Single recipient?
   if not isinstance(email_cfg['to'], list):
      email_cfg['to'] = [email_cfg['to']]

   if len(email_cfg['to']) == 0:
      exit_program(True, 'No recipients in the list.')

   # Find other files we need to attach
   attach_files = filter(lambda x: x not in ['email.cfg', 'text.txt'], os.listdir(email_dir))

   # Create email information and return it
   the_email = {
      'path': email_dir,
      'server': config,
      'to': email_cfg['to'],
      'from': email_cfg['from'],
      'subject': email_cfg['subject'],
      'body': open(text_txt, 'r').read(),
      'attachments': [email_dir + '/' + x for x in attach_files]
   }

   return the_email

def get_address_only (email):
   if '<' in email:
      data = email.split('<')
      email = data[1].split('>')[0].strip()
   return email.strip()

def send_email (data):
   # The 'to' field is a list.
   # MIME expects a string, so join the list.
   # sendmail expects a list, so don't.

   email = MIMEMultipart('alternative')
   email['From'] = data['from']
   email['To'] = ', '.join(data['to'])
   email['Subject'] = data['subject']

   text = MIMEText(data['body'], 'html', 'us-ascii')

   email.attach(text)

   # Run through each attachment, if any
   for attach in data['attachments']:
      mimetype, encoding = guess_type(attach)
      mimetype = mimetype.split('/', 1)
      f = open(attach, 'rb')
      attachment = MIMEBase(mimetype[0], mimetype[1])
      attachment.set_payload(f.read())
      f.close()
      encode_base64(attachment)
      attachment.add_header('Content-Disposition', 'attachment', filename = os.path.basename(attach))
      email.attach(attachment)

   # Now we can try to connect to the server and send it.
   server = data['server']
   conn = SMTP(server['server'], int(server['port']))
   conn.ehlo()
   conn.starttls()
   conn.ehlo()
   conn.login(server['username'], server['password'])

   to = [get_address_only(addr) for addr in data['to']]
   msg_as_text = str(email)

   exit_msg = 'Mail sent successfully.'

   try:
      conn.sendmail(data['from'], to, msg_as_text)
   except SMTPRecipientsRefused:
      exit_msg = 'The SMTP server refused to send to one or more recipients.'
   except SMTPHeloError:
      exit_msg = 'The SMTP server did not reply to HELO/EHLO.'
   except SMTPSenderRefused:
      exit_msg = 'The SMTP server refused to send mail from this address.'
   except SMTPDataError:
      exit_msg = 'The SMTP server replied with an unexpected error code.'
   except SMTPNotSupportedError:
      exit_msg = 'The SMTP server is claiming it does not support a required feature.'
   except Exception as e:
      exit_msg = 'Something went wrong sending mail: {}'.format(e)

   conn.quit()

   exit_program(False, exit_msg)

def delete_email (data):
   if os.path.exists(data['path']):
      try:
         rmtree(data['path'])
      except OSError:
         return

# Again, the arguments are <configfile> <maildir>. See the top of this file.
if len(sys.argv) < 3:
   exit_program(True, 'Missing arguments.')

config_file, mail_dir = sys.argv[1], sys.argv[2]
the_email = compose_email(config_file, mail_dir)
send_email(the_email)
delete_email(the_email)

