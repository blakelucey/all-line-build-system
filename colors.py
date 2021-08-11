# Color names outside of curses.COLOR_...

import curses
import os

# Color pair names
window = 4
error = 10
help = 12

# Color contants
DARK_GRAY = dark_gray = curses.COLOR_BLACK + 8
BRIGHT_RED = bright_red = curses.COLOR_RED + 8
BRIGHT_GREEN = bright_green = curses.COLOR_GREEN + 8
BRIGHT_YELLOW = bright_yellow = curses.COLOR_YELLOW + 8
BRIGHT_BLUE = bright_blue = curses.COLOR_BLUE + 8
BRIGHT_MAGENTA = bright_magenta = curses.COLOR_MAGENTA + 8
BRIGHT_CYAN = bright_cyan = curses.COLOR_CYAN + 8
BRIGHT_WHITE = bright_white = curses.COLOR_WHITE + 8

if os.environ['TERM'] == 'linux':
   DARK_GRAY -= 8
   BRIGHT_RED -= 8
   BRIGHT_GREEN -= 8
   BRIGHT_YELLOW -= 8
   BRIGHT_BLUE -= 8
   BRIGHT_MAGENTA -= 8
   BRIGHT_CYAN -= 8
   BRIGHT_WHITE -= 8

def init_colors ():
   if os.environ['TERM'] == 'linux':
      return

   curses.init_color(curses.COLOR_BLACK + 8,   300, 300, 300)
   curses.init_color(curses.COLOR_RED + 8,     1000, 333, 333)
   curses.init_color(curses.COLOR_GREEN + 8,   333, 1000, 333)
   curses.init_color(curses.COLOR_YELLOW + 8,  1000, 1000, 333)
   curses.init_color(curses.COLOR_BLUE + 8,    333, 333, 1000)
   curses.init_color(curses.COLOR_MAGENTA + 8, 1000, 333, 1000)
   curses.init_color(curses.COLOR_CYAN + 8,    333, 1000, 1000) 
   curses.init_color(curses.COLOR_WHITE + 8,   1000, 1000, 1000)
