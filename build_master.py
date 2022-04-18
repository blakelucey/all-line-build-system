#!/usr/bin/python3 -B

import time
import sys
import locale
import os
import curses
import curses.textpad

import gfx_chars
from logo import all_line_logo
from curses import wrapper

# Make sure current working directory is the ~/build-master
os.chdir("/home/all-line/build-master")

# There's only one standard screen and it's global anyhow
stdscr = None

# List of menus we've been down
crumbs = []

def draw_crumbs ():
   stdscr.move(1, 2)
   stdscr.clrtoeol()
   stdscr.addstr('All-Line Equipment Build System', curses.color_pair(5) | curses.A_BOLD)
   stdscr.move(2, 2)
   stdscr.clrtoeol()
   stdscr.move(2, 2)
   for i, c in enumerate(crumbs):
      stdscr.addstr(c, curses.color_pair(2))
      if i < len(crumbs) - 1:
         stdscr.addstr(f' {gfx_chars.right_arrow} ', curses.color_pair(2) | curses.A_DIM)
   stdscr.refresh()

def crumb (name):
   crumbs.append(name)
   draw_crumbs()

def del_crumb ():
   global crumbs
   crumbs.pop()
   draw_crumbs()

def main (scr):
   global stdscr
   stdscr = scr

   curses.noecho()
   curses.cbreak()
   curses.curs_set(0)
   curses.use_default_colors()

   curses.init_color(curses.COLOR_BLACK, 0, 0, 0)

   import colors
   colors.init_colors()

   curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
   curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE)
   curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLUE)
   curses.init_pair(4, curses.COLOR_WHITE, curses.COLOR_BLACK)
   curses.init_pair(5, curses.COLOR_CYAN, curses.COLOR_BLUE)
   curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_CYAN)
   curses.init_pair(7, curses.COLOR_BLACK * 10, curses.COLOR_BLACK)
   # 256-color support only, someday
   #curses.init_pair(8, 0, 110)
   #curses.init_pair(9, 15, 110)
   curses.init_pair(8, curses.COLOR_WHITE, curses.COLOR_BLUE)
   curses.init_pair(9, curses.COLOR_YELLOW, curses.COLOR_BLUE)
   curses.init_pair(10, curses.COLOR_YELLOW, curses.COLOR_RED)
   curses.init_pair(11, curses.COLOR_YELLOW, curses.COLOR_GREEN)
   curses.init_pair(12, curses.COLOR_WHITE, curses.COLOR_CYAN)
   curses.init_pair(13, curses.COLOR_YELLOW, curses.COLOR_BLACK)
   curses.init_pair(14, curses.COLOR_YELLOW, curses.COLOR_CYAN)
   curses.init_pair(20, curses.COLOR_BLACK, curses.COLOR_BLUE)

   stdscr.bkgdset(' ', curses.color_pair(2) | curses.A_BOLD)
   stdscr.clear()
   stdscr.notimeout(False)

   stdscr.refresh()

   from menu import menu
   #from injector import do_injector
   from text_input import text_input
   import injector
   import bioblender
   import fuel_boss
   import repressurizer
   import draw
   import sys
   import config
   import utils
   import compiler
   import buildroot
   import oled_screen

   config.load()

   crumb('Main Menu')
   ret = 0

   while True:
      try:
         ret = menu([
            ('Build an Injector', 'injector'),
            ('Build a Repressurizer', 'repressurizer', False),
            ('Build an OLED screen', 'oled_screen', False),
            ('Build a Fuel Boss', 'fuel-boss', False),
            ('Build a Bioblender', 'bioblender', False),
            ('Build a Development SD Card', 'dev'),
            '-',
            ('Configure this Program', 'config'),
            ('Manage Buildroot', 'buildroot'),
            ('Quit this Program', 'quit'),
            ('Reboot the System', 'reboot')
         ], title = 'Main Menu', pre_select = ret)

         if ret == 'injector':
            injector.do_injector()

         elif ret == 'fuel-boss':
            fuel_boss.do_fuel_boss()

         elif ret == 'config':
            config.do_config()

         elif ret == 'repressurizer':
            repressurizer.do_repressurizer()

         elif ret == 'oled_screen':
            oled_screen.do_oled_screen()

         elif ret == 'buildroot':
            buildroot.do_buildroot()

         elif ret == 'bioblender':
            bioblender.do_bioblender()

         elif ret == 'dev':
            sd_card.do_dev_card()

         # TODO?
         #elif ret == 'reboot' or ret == 'quit' or ret == -1:
         #   draw.message(('I\'m sorry. I can\'t allow you to do that.'), colors = 10)

         elif ret == 'quit' or ret == -1:
            result = draw.question('Are you sure you want to quit?', escape = 1)
            #result = draw.question('Are you sure you want to quit?')
            if result == 'Y':
               return
            ret = 0
            continue
      except Exception as e:
         # This catches all exceptions, logs them, and also displays them.
         utils.trace_exception()
         continue

# Wrap the main program so curses cleans up after itself.
# Also set the environment's escape delay to be super short.
locale.setlocale(locale.LC_ALL, '')
os.environ['ESCDELAY'] = '10'
wrapper(main)

