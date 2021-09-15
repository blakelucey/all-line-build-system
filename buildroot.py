import os
import sys
import shutil
import json
import curses
import datetime
import subprocess
import time

import draw
import utils
import config
from menu import menu, make_columns
from __main__ import stdscr, crumb, del_crumb

class BuildrootCompiler:
   def __init__ (self):
      # Use the default Buildroot tree?
      self.buildroot_root = './buildroot/' + config.get('buildroot_version', 'buildroot-2021.08.13-pi2-tmp')
      self.buildroot_version = self.buildroot_root.split('-')[1]

      # Find all of the All-Line versions of buildroot.
      self.scan_boards()

   def scan_boards (self):
      self.boards = []

      try:
         scan = os.scandir(f'{self.buildroot_root}/board')
      except (IOError, FileNotFoundError):
         scan = []

      for entry in scan:
         if entry.name.startswith('all_line'):
            board = {'name': entry.name, 'path': entry.path}
            root_fs = os.path.join(entry.path, 'output', 'rootfs.tar.gz')
            has_cache = os.path.exists(root_fs)

            if has_cache:
               stat = os.stat(root_fs)
               timestamp = stat.st_mtime
               when = datetime.datetime.fromtimestamp(timestamp)

               size = 0
               for subentry in os.scandir(os.path.join(entry.path, 'output')):
                  size += subentry.stat().st_size

               size_str = utils.format_size(size, space = True)
            else:
               timestamp = None
               when = None
               size = 0
               size_str = 'N/A'

            board['defconfig'] = board['name'] + '_defconfig'
            board['has_cache'] = has_cache
            board['cache_path'] = f'{entry.path}/output'
            board['root_fs'] = root_fs
            board['timestamp'] = timestamp
            board['datetime'] = when
            board['size'] = size
            board['size_str'] = size_str

            self.boards.append(board)

      return self.boards

   def menu (self):
      if len(self.boards) == 0:
         draw.message(('There are no Buildroot boards that I can find.\n'
            'This is terrible news.\n'
            '\n'
            'Talk to Steven, he\'ll know what to do.'), colors = 10)
         return

      sizes = (24, 14, 18, 12)
      cols  = ('Board Name', 'Has Cache?', 'Last Compiled', 'Total Size')
      align = (None, None, None, 'rjust')
      items = [make_columns(sizes, cols, align = align, header = True)]

      for board in self.boards:
         when = board['datetime'].strftime('%Y-%m-%d %H:%M') if board['has_cache'] else 'N/A'
         size = board['size_str']
         text = (board['name'], 'Yes' if board['has_cache'] else 'No', when, size)
         items.append((make_columns(sizes, text, align = align), board))

      while True:
         ret = menu(items, title = f'Buildroot Version {self.buildroot_version}')

         if ret == -1:
            break

         elif isinstance(ret, dict):
            # This is a reference to a board definition.
            # Ask if they'd like to refresh the cache.
            self.cache_board(ret)

   def cache_board (self, board):
      if board['has_cache']:
         result = draw.question((
            'This board already has a cached output. Would you like to recompile?\n'
            '\n'
            'This will take quite a while. Rhyme unintentional.'),
            title = 'Recompile')

         if result != 'Y':
            # This is fine
            return

      # Clean the directory and make the default board configuration
      draw.begin_wait(f'Compiling {self.buildroot_version}, board {board["name"]}...')
      code = os.system(f'cd {self.buildroot_root} ; make clean > /dev/null 2>&1 && make {board["defconfig"]} > /dev/null 2>&1 && make > /dev/null 2>&1')

      if (code >> 8) != 0:
         draw.end_wait()
         draw.message((
            'Unable to build this board\'s software. There\'s a good chance you\'ll '
            'want to talk to Steven about this.'),
            colors = 10)
         return

      if (code >> 8) == 0:
         draw.end_wait()
         draw.message('Built successfully! You can now use this to make SD cards.', colors = 11)
      else:
         draw.end_wait()
         draw.message((
            'Unable to build this board\'s software. There\'s a good chance you\'ll '
            'want to talk to Steven about this.'),
            colors = 10)

def do_buildroot ():
   br = BuildrootCompiler()
   br.menu()

