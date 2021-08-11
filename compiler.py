import subprocess
import os
import curses
import time
import re
import shutil

import config
import draw
import utils
from __main__ import stdscr

compile_dir = './compile'
combine_dir = './compile/combine'

class DefinitionEditor:
   def __init__ (self, filename):
      self.tempfile = f'{utils.ramdisk}/temp_file'
      self.filename = filename

      if os.path.exists(self.tempfile):
         os.remove(self.tempfile)
      shutil.copy2(self.filename, self.tempfile)

      self.find_defines()

   def define (self, symbol, value = None):
      syms = self.get_symbols(symbol)
      for sym in syms:
         # Strip the comment off, set a value, set as define.
         sym['comment'] = False
         sym['is_define'] = True
         sym['is_undef'] = False

         if value is not None:
            sym['value'] = value
         else:
            sym['value'] = ''

   def remove_define (self, symbol):
      syms = self.get_symbols(symbol)
      for sym in syms:
         # Attach a comment.
         sym['comment'] = True

   def undefine (self, symbol):
      syms = self.get_symbols(symbol)
      for sym in syms:
         # Strip the comment, remove the value, set as undef.
         sym['comment'] = False
         sym['value'] = None
         sym['is_define'] = False
         sym['is_undef'] = True

   def get_symbols (self, *args):
      out = []
      for item in self.items:
         if item['symbol'] in args:
            out.append(item)
      return out

   def get_single_line (self, item):
      # Build a new string for this line.
      new = ''
      if item['comment']: new += '//'
      if item['is_define']: new += '#define'
      if item['is_undef']: new += '#undef'
      new += ' ' + item['symbol']
      if item['is_define'] and len(item['value']):
         new += ' ' + item['value']
      return new

   def get_text (self):
      lines = [line.strip() for line in open(self.filename, 'r')]

      for item in self.items:
         new = self.get_single_line(item)
         lines[item['line_no']] = new

      return '\n'.join(lines)

   def save (self):
      # Remove the original file and move our temporary file into its spot.
      # Make a backup first.
      with open(self.tempfile, 'w') as f:
         f.write(self.get_text())
      shutil.copy2(self.filename, f'{self.filename}.backup')
      os.remove(self.filename)
      shutil.copy2(self.tempfile, self.filename)

   def find_defines (self):
      # This searches for a line containing something like:
      #    #define SYMBOL VALUE
      # or just
      #    #define SYMBOL
      # or even
      #    #undef SYMBOL
      # and fills in self.items.

      #expr = '\s*(?P<comment>/*)\s*#\s*(?P<type>define|undef)\s*(?P<symbol>\w+)\s*(?P<value>\w*)'
      expr = '^\s*?(?P<comment>/*)\s*?#\s*?(?P<type>define|undef)\s*?(?P<symbol>\w+)\s*?(?P<value>[ -~]*?)\s*?$'
      self.items = []

      for nr, line in [(n, l.strip()) for n, l in enumerate(open(self.tempfile, 'r'))]:
         # Skip this line?
         if not re.search(expr, line): continue

         for match in re.finditer(expr, line):
            values = match.groupdict()

            # No dict from the match object?
            if not values: continue

            # Arguments will get absorbed as values.
            # Modifying the regex is unpleasant at this point, so let's
            # handle that here.
            arg_begin = line.find(values['symbol'] + '(')
            if arg_begin >= 0:
               # There are arguments.
               arg_begin += len(values['symbol'])
               arg_end = line.find(')', arg_begin)
               args = line[arg_begin:arg_end + 1]
               if values['value'].startswith(args):
                  values['value'] = values['value'][len(args):]
            else:
               args = ''

            self.items.append({
               'comment': len(values['comment']) >= 2 and values['comment'].count('/') == len(values['comment']),
               'line': line,
               'line_no': nr,
               'is_define': values['type'] == 'define',
               'is_undef': values['type'] == 'undef',
               'symbol': values['symbol'],
               'value': values['value'],
               'args': args
            })

class Compiler:
   def __init__ (self, src, in_place = False):
      self.source = src
      self.dest = compile_dir if not in_place else src

      # Out-of-tree compile directory?
      if not in_place:
         if os.path.exists(compile_dir):
            shutil.rmtree(compile_dir)
            if os.path.exists(compile_dir):
               os.rmdir(compile_dir)
         else:
            os.mkdir(compile_dir, 0o777)
         shutil.copytree(src, compile_dir)

   def get_path (self):
      return self.dest

   def compile (self):
      draw.begin_wait('Compiling from source...')

      proc = subprocess.run(f'make -C "{self.dest}" clean', 
         shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
      if proc.returncode != 0:
         draw.viewer(
            'Unable to clean source directory.\n\nYou might need to talk to Steven.',
            rows = 36, cols = 120, colors = 10, attrs = curses.A_BOLD)
         return False

      proc = subprocess.run(f'make -C "{self.dest}" -j {config.get("compiler_threads")}',
         shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)

      if proc.returncode != 0:
         draw.end_wait()
         draw.viewer(
            self.clean_output(proc.stderr.decode('utf-8')),
            rows = 40, cols = 120,
            title = 'Error Compiling',
            colors = 10, attrs = curses.A_BOLD)
         return False
      else:
         draw.end_wait()
         draw.viewer(
            self.clean_output(proc.stdout.decode('utf-8')),
            rows = 40, cols = 120,
            title = 'Successful Compilation',
            colors = 11, attrs = curses.A_BOLD)
         return True

   def clean_output (self, text):
      # This just replaces ANSI stuff with nothing.
      if not isinstance(text, str): text = text.decode('utf-8')
      out_text = ''

      is_escape = False
      for index, ch in enumerate(text):
         if is_escape:
            # The only ANSI codes that are used are for colorizing text,
            # meaning that they all end with 'm'.
            if ch == 'm':
               is_escape = False
         else:
            # I guess the way 'make' outputs "\x1b" is literally as the ASCII
            # string "\x1b", so let's assume the '\x' is out escape marker.
            if ch == '\\' and index < len(text) - 1 and text[index + 1] == 'x':
               is_escape = True
            else:
               out_text += ch

      return out_text

   def combine_with (self, src, hex_file = None):
      # This is usually for combining a bootloader with a main program.
      # We'll create an instance of ourselves but with a different destination
      # directory. Then we'll compile that, and use srec_cat to combine the
      # resulting hex files.

      comp = Compiler(src, combine_dir)
      if not comp.compile():
         return False

      hex_file = 'main.hex' if hex_file is None else hex_file

      result = utils.combine_hexes(f'{self.dest}/main.hex', hex_file)
      if result == False:
         return False

      # Return the combined file name.
      return result[1]

