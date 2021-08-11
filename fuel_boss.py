import os
import datetime

import draw
from menu import menu
from text_input import text_input
from __main__ import crumb, del_crumb, stdscr

# These reference the most common systems we make.
# If those systems have their software updated, these references may need
# to change.

from fuel_boss_custom import *
import fuel_boss_stable_pi2

fuel_boss_dir = './data/fuel_boss'
staging_dir = './staging'
compile_dir = './compile'

fuel_boss_data = {
   'stable_pi2': {
      'name': 'Fuel-Boss V1 Stable, Pi 2',
      'dir': f'{fuel_boss_dir}/StableFB-2019-07-08',
      'func': lambda x: fuel_boss_stable_pi2.build(x),
      'main_menu': True,
      'staging_dir': staging_dir
   },
   'unstable_pi4': {
      'name': 'Fuel-Boss V2 Unstable, Pi 4',
      'dir': 'TNG',
      'func': None,
      'main_menu': True,
      'staging_dir': staging_dir
   },
   'road_ranger_rock_island': {
      'name': 'Road Ranger, Rock Island',
      'dir': '2019-07-06_StableFB_Road-Ranger',
      'func': None,
      'main_menu': False,
      'staging_dir': staging_dir
   }
}

def sub_find (hexes, serial, where):
   for entry in os.scandir(where):
      # Descend?
      if entry.is_dir():
         sub_find(hexes, serial, f'{where}/{entry.name}')

      elif entry.name.lower() == 'main.hex':
         info = os.stat(entry.path)
         if serial not in hexes:
            hexes[serial] = []
         hexes[serial].append({
            'serial': serial,
            'name': entry.name,
            'where': f'{where}/{entry.name}',
            'date': datetime.datetime.fromtimestamp(info.st_mtime),
            'timestamp': info.st_mtime,
            'is_debounce': 'debounce' in where
         })

def find_main_hexes (serial):
   where = f'./data/fuel_boss/{serial}'
   hexes = {}
   sub_find(hexes, serial, where)
   return hexes

def gather_descriptions ():
   descs = {}
   nondescs = 0

   for entry in os.scandir(fuel_boss_data):
      # Skip?
      if not entry.is_dir(): continue
      if not os.path.exists(f'{entry.path}/desc.txt'): 
         nondescs += 1
         continue

      # It has it.
      descs[entry.name] = open(f'{entry.path}/desc.txt', 'r').read().lower()

   return descs, nondescs

def search_descriptions ():
   crumb('Search All Descriptions')

   draw.begin_wait('Gathering descriptions...')
   descs, nondescs = gather_descriptions()
   draw.end_wait()

   win = draw.newwin(20, 60, title = 'Search Descriptions', text =
      ('This will allow you to search the description files for all injection systems.\n'
       '\n'
       'Some older systems may not have a description file and cannot be searched, '
       'contradicting my previous sentence.\n'
       '\n'
       f'I have found {len(descs)} systems with description files. Cross your fingers that it\'s '
       f'one of those! That means there are {nondescs} systems without description files.\n'
       '\n'
       '\n'
       '\n'
       'Type a search term and hit Enter, or hit Escape to go back.'))

   draw.separator(win, 11)
   win.refresh()

   win_h, win_w = win.getmaxyx()

   ret = text_input(
      can_escape = True, border = False, relative_to = win,
      coords = (16, 1, 2, win_w - 2))

   # Escape?
   if ret == -1:
      del win
      stdscr.touchwin()
      stdscr.refresh()
      return False

   # Search away!
   ret = ret.lower()
   matches = []
   for desc in descs:
      if ret in descs[desc]:
         matches.append((desc, desc))

   if len(matches):
      draw.viewer((
         f'I found {len(matches)} systems that include that term in their description file.\n'
         '\n'
         'Press Enter to see the list.'),
         rows = 8,
         cols = 70,
         title = 'Matches Found',
         center = True)

      sel = 0
      while True:
         sel = menu(matches, title = 'Matching Systems', pre_select = sel)

         if sel == -1:
            break

         else:
            # It's a serial as a key
            view_fuel_boss(sel)

   else:
      draw.viewer(('I did not find any system description files containing your search term.\n'
         '\n'
         'Press Enter to return.'),
         rows = 8,
         cols = 70,
         center = True)

   # Clean up
   del win
   stdscr.touchwin()
   stdscr.refresh()
   del_crumb()

def view_fuel_boss (serial):
   path = f'./data/fuel_boss/{serial}'
   desc_file = f'{path}/desc.txt'
   sel = 0

   crumb(f'Viewing "{serial}"')

   while True:
      items = []
      if os.path.exists(desc_file):
         items.append(('Read Description File', 'read'))

      items += [('Program this System', 'program')]

      sel = menu(items, pre_select = sel, title = serial)

      if sel == -1:
         break

      elif sel == 'read':
         draw.viewer(open(desc_file).read(),
            title = f'Description File for {serial}',
            rows = 24,
            cols = 90)

      elif sel == 'program':
         program_fuel_boss(serial)

   del_crumb()

def program_fuel_boss (serial):
   # Find all of the HEX files we can use
   hexes = find_main_hexes(serial)

   if not len(hexes):
      ret = draw.question((
         'It appears there aren\'t any firmware images in this directory.\n'
         '\n'
         'This may be a placeholder for a bioblender or other custom system.\n'
         'Would you like to see the list of files anyway?'),
         cols = 70,
         rows = 11)

      if ret == 'Y':
         items = os.listdir(f'./data/fuel_boss/{serial}')
         menu(items, title = 'Unknown Injector')

      return

   items = []

   for entry in hexes[serial]:
      # Skip debounce entries
      if entry['is_debounce']: continue

      when = entry['date'].strftime('%Y-%m-%d at %H:%M:%S')
      where = entry['where'].replace('./data/fuel_boss/', '')
      items.append(f'{where:50}Compiled {when}')

   sel = menu(items, title = f'Program {serial}')
   if sel == -1:
      # They decided against it
      return

   # They must want to do the thing.
   draw.question((
      'Power the system up and plug the programmer into the '
      'debounce programming header (right).\n'
      '\n'
      'Press Enter when ready, or Escape to cancel..'),
      choices = ())

def show_all (recent_first = False):
   title = 'All Serial Numbers'

   serials = [(serial, serial) for serial in sorted(os.listdir('./data/fuel_boss'))]

   crumb(title)

   ret = 0

   while True:
      ret = menu(serials, title = title, pre_select = ret)

      if ret == -1:
         break

      else:
         view_fuel_boss(ret)

   del_crumb()

def do_fuel_boss ():
   crumb('Build a Fuel Boss')
   ret = 0

   while True:
      items = []

      for key, data in fuel_boss_data.items():
         # Skip those not in the main menu.
         if data['main_menu'] == False:
            continue

         items.append((data['name'], key))

      items += [
         ('Build a Custom Fuel Boss', 'custom'),
         ('-'),
         ('Rebuild an Existing System', 'rebuild'),
         ('Discover or change an IP address', 'ip'),
         ('-'),
         ('See All Serial Numbers', 'serial'),
         ('Search Descriptions', 'desc'),
      ]
      
      ret = menu(items, title = 'Build a Fuel Boss', pre_select = ret)

      if ret == 'serial':
         show_all()

      elif ret == 'desc':
         search_descriptions()

      elif ret == 'rebuild':
         rebuild()

      elif ret == -1:
         del_crumb()
         break

      else:
         if ret in fuel_boss_data:
            func = fuel_boss_data[ret]['func']
            if not func:
               draw.message(('This Fuel Boss does not have a builder associated with it.\n'
                  '\n'
                  'Talk to Steven.'))
            else:
               func(fuel_boss_data[ret])

