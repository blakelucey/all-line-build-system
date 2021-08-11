# All-Line Equipment Company

import os
import stat
import json
import random
import string

from logger import *

_all_paths = {
   'program': '/program/',
   'config': '/config/',
   'records': '/config/records/',
   'tools': '/program/tools/',
   'www': '/program/www/',
   'cron': '/config/cron/',
   'temp': '/dev/shm/'
}

def check_mode (path, recurse = False):
   '''Checks path/file mode, owner and group; fixes if necessary.'''
   try:
      uid, gid = os.getuid(), os.getgid()
      st = os.stat(path)

      os.chown(path, uid, gid)
      os.chmod(path, st.st_mode | stat.S_IRWXG | stat.S_IRWXU | stat.S_IRWXO)
   except OSError:
      log_info('Failed to set mode for {}.'.format(path))

def get_path (path_id):
   if path_id not in _all_paths:
      log_info('Invalid path requested: {}'.format(path_id))
      return None

   return _all_paths[path_id]

def generate_email_path ():
   '''Return a path you can use to create an email structure for tools/emailer.py.'''
   return get_path('temp') + ''.join([random.choice(string.ascii_letters) for _ in xrange(16)]) + '/'

def print_param (remote, which = None, sub_count = 1):
   columns = [
      ('ID', 4),
      ('Index', 6),
      ('Parameter Name', 28),
      ('Type', 8),
      ('Array', 8),
      ('Minimum', 12),
      ('Maximum', 12),
      ('Value', 24),
      ('Description', 110)
   ]

   # Print column headers
   text = ''
   for column in columns:
      text += column[0].ljust(column[1]) + ' '
   print text

   text = ''
   for column in columns:
      text += '-' * column[1] + ' '
   print text

   # Now print the data
   names = remote.get_names() if which is None else [which]
   for param_info in names:
      for sub_id in xrange(sub_count):
         name = param_info
         param = remote.get_param(name)

         text  = '{}'.format(param.id).ljust(columns[0][1]) + ' '
         text += '{}'.format(sub_id).ljust(columns[1][1]) + ' '
         text += '{}'.format(name).ljust(columns[2][1]) + ' '
         text += '{}'.format(param.type_strings[param.type]).ljust(columns[3][1]) + ' '
         text += '{}'.format('Yes' if param.is_array() else 'No').ljust(columns[4][1]) + ' '

         if param.type == param.types['int']:
            text += '{}'.format(str(param.minimum)).ljust(columns[5][1]) + ' '
            text += '{}'.format(str(param.maximum)).ljust(columns[6][1]) + ' '
            text += '{}'.format(str(param.get(sub_id))).ljust(columns[7][1]) + ' '
         elif param.type == param.types['float']:
            text += ('{:.' + param.precision + 'f}').format(param.minimum).ljust(columns[5][1]) + ' '
            text += ('{:.' + param.precision + 'f}').format(param.maximum).ljust(columns[6][1]) + ' '
            text += ('{:.' + param.precision + 'f}').format(param.get(sub_id)).ljust(columns[7][1]) + ' '
         else:
            # Cut the string down, if necessary; don't show display strings/rows
            text += '{}'.format(str(param.minimum)).ljust(columns[5][1]) + ' '
            text += '{}'.format(str(param.maximum)).ljust(columns[6][1]) + ' '

            if not name.startswith('Display'):
               value = param.get(sub_id)
               if len(value) > columns[7][1] - 5:
                  value = value[:columns[7][1] - 5] + '...'
               text += '{}'.format(str(param.get(sub_id))).ljust(columns[7][1]) + ' '
            else:
               text += 'N/A'.ljust(columns[7][1]) + ' '

         # Cut the description down, if necessary
         desc = param.description
         if len(desc) > columns[8][1] - 5:
            desc = desc[:columns[8][1] - 5] + '...'

         text += '{}'.format(desc)

         print text

   # Blank line
   print

# Check all paths, recursing for the config directory.
for path in _all_paths:
   if not os.path.isdir(_all_paths[path]):
      log_info('{} is missing. Creating it.'.format(_all_paths[path]))
      os.mkdir(_all_paths[path])

# Check for some basic configuration files.
if not os.path.exists(get_path('config') + 'web-users.cfg'):
   # There is no web user list. Make a stock one.
   web_users = {
      'users': [
         {
            'real_name': 'All-Line Equipment',
            'username': 'all-line',
            'password_hash': 'bcdde72f8ffad157876b170249033f34e83b55b7',
            'permissions': ['update', 'admin']
         },
         {
            'real_name': 'User',
            'username': 'user',
            'password_hash': 'da39a3ee5e6b4b0d3255bfef95601890afd80709',
            'permissions': []
         },
         {
            'real_name': 'Administrator',
            'username': 'admin',
            'password_hash': '5baa61e4c9b93f3f0682250b6cf8331b7ee68fd8',
            'permissions': ['admin']
         }
      ]
   }

   with open(get_path('config') + 'web-users.cfg', 'w') as f:
      f.write(json.dumps(web_users))
      f.flush()

   check_mode(get_path('config') + 'web-users.cfg')

# Check the notes file
if not os.path.exists(get_path('config') + 'notes.txt'):
   with open(get_path('config') + 'notes.txt', 'w') as f:
      f.flush()
   check_mode(get_path('config') + 'notes.txt')

