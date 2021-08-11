# All-Line Equipment Company

import json

from string import maketrans

class RemoteDisplay:
   def __init__ (self, remote, ipc):
      self.ipc = ipc
      self.remote = remote
      self.rows = remote.get_param('Display Rows').get()
      self.cols = remote.get_param('Display Columns').get()
      self.count = remote.get_param('Display').maximum

      self.ansi_green = '\x1b[96m'
      self.ansi_gray = '\x1b[37m'

      self.dc_clear = 1
      self.dc_clear_row = 2
      self.dc_goto = 3
      self.dc_brightness = 4
      self.dc_cursor = 5
      self.dc_blink = 6
      self.dc_set_blink = 7

      self._make_table()

      self.ipc.add_handler('get_display', self.ipc_get_display)
      self.ipc.add_handler('get_indicator_info', self.ipc_get_indicator_info)
      self.ipc.add_handler('get_display_and_indicators', self.ipc_get_both)

   def ipc_get_both (self, skt, data):
      # Send all rows.
      disp_data = []

      for row in xrange(self.rows):
         row_data = self.remote.get_param_value('Display', row)
         disp_data.append(self.translate(row_data))

      skt.send({
         'reply_to': data['request_type'],
         'rows': self.rows,
         'columns': self.cols,
         'data': disp_data,
         'indicator_states': self.remote.get_param_value('Indicator States'),
         'cursor_row': ord(self.remote.get_param_value('Cursor Row')[0]),
         'cursor_column': ord(self.remote.get_param_value('Cursor Column')[0]),
         'cursor_enabled': self.remote.get_param_value('Cursor Enabled')
      }, json_encoding = 'latin1')

   def ipc_get_indicator_info (self, skt, data):
      skt.send({
         'reply_to': data['request_type'],
         'indicators': json.loads(self.remote.get_param_value('Indicators'))
      })

   def ipc_get_display (self, skt, data):
      disp_data = []

      if 'row' in data:
         # Get a single row.
         try:
            row = int(data['row'])
         except ValueError:
            skt.error('Invalid display row request.')
            return

         row_data = self.remote.get_param_value('Display', row)
         skt.send({
            'reply_to': data['request_type'],
            'row': str(row),
            'data': self.translate(row_data)
         }, json_encoding = 'latin1')
         return

      # Send all rows.
      for row in xrange(self.rows):
         row_data = self.remote.get_param_value('Display', row)
         disp_data.append(str(self.translate(row_data)))

      skt.send({
         'reply_to': data['request_type'],
         'rows': self.rows,
         'columns': self.cols,
         'data': disp_data
      }, json_encoding = 'latin1')

   def _make_table (self):
      '''Retrieves the character translation table from the remote system.'''
      # Set up the character translation table.
      # The table format we get from the remote system is char:replacement;char:replacement;...

      table = self.remote.get_param('Display Mapping').get()
      parts = table.split(';')
      pairs = {}
      inchars, outchars = '', ''
      for part in parts:
         if not len(part): continue
         char, repl = part.split(':')
         inchars += char
         outchars += repl

      self.translation_table = maketrans(inchars, outchars)

   def translate (self, text):
      # Translate characters, then replace unprintables with spaces.
      # Then join the list.

      # This used to be a thing, but isn't anymore.
      #text = ''.join(map(lambda x: x if ord(x) >= 20 and ord(x) < 127 else ' ', text.translate(self.translation_table)))

      return text.replace('\x00', ' ')

   def get_saved_screenshot (self):
      result = ''
      for row in xrange(self.rows):
         line = self.translate(self.remote.get_param('Screenshot').get(row))
         result += line + '\r\n'
      return result

   def print_display (self):
      for row in xrange(self.rows):
         line = self.translate(self.remote.get_param('Display').get(row))
         print '{}{}{}'.format(self.ansi_green, line, self.ansi_gray)

   def goto (self, row, col):
      rc = (row << 8) | col
      self.remote.set_param_value('Display Command', rc, self.dc_goto)

   def clear (self):
      self.remote.set_param_value('Display Command', 0, self.dc_clear)

   def clear_row (self, row):
      self.remote.set_param_value('Display Command', row, self.dc_clear_row)

   def set_brightness (self, br):
      self.remote.set_param_value('Display Command', br, self.dc_brightness)

   def cursor_on (self):
      self.remote.set_param_value('Display Command', 1, self.dc_cursor)

   def cursor_off (self):
      self.remote.set_param_value('Display Command', 0, self.dc_cursor)

   def blink_on (self):
      self.remote.set_param_value('Display Command', 1, self.dc_blink)

   def blink_off (self):
      self.remote.set_param_value('Display Command', 0, self.dc_blink)

   def set_blink_speed (self, speed = 8):
      self.remote.set_param_value('Display Command', speed, self.dc_set_blink)

   def write (self, text = ''):
      self.remote.set_param_value('Display Data', text)

