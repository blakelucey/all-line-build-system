import time
import curses
import gfx_chars
import subprocess
from logger import log_debug
from wrap import wrap
from __main__ import stdscr, crumb, del_crumb

import math

waiting_window = None
output_window = None
output_scroll_window = None

def newwin (
   rows,
   cols,
   row = None,
   col = None,
   colors = None,
   attrs = None,
   title = None,
   text = None,
   center = False,
   v_center = False,
   double_border = False,
   shadow = False,
   subwin = False):

   if colors is None: 
      colors = curses.color_pair(0)
   else:
      colors = curses.color_pair(colors)
   if attrs is None: attrs = curses.A_BOLD

   # Center this window?
   if row is None:
      if rows > curses.LINES:
         rows = curses.LINES-2
         row = 1
      else:
         row = curses.LINES // 2 - rows // 2 - 1
   if col is None:
      if cols > curses.COLS:
         cols = curses.COLS-2
         col = 1
      else:
         col = curses.COLS // 2 - cols // 2 - 1

   if subwin:
      win = stdscr.subwin(rows, cols, row, col)
   else:
      win = curses.newwin(rows, cols, row, col)
   win.bkgdset(' ', colors | attrs)
   win.erase()

   if shadow:
      scolor = curses.color_pair(20) | curses.A_BOLD | curses.A_REVERSE
      schar = '\u2592'
      for line in range(row + 1, row + rows):
         stdscr.addstr(line, col + cols, schar, scolor)
      stdscr.addstr(row + rows, col + 1, schar * cols, scolor)
      stdscr.refresh()

   if double_border:
      # win.border() can't accept wide characters even though
      # ncurses supports it. Who knows. Do it ourselves.

      ls, rs, ts, bs, tl, tr, bl, br = (
         '\u2551', '\u2551', '\u2550', '\u2550', 
         '\u2554', '\u2557', '\u255A', '\u255D')

      win.insstr(0, 0, tl + ts * (cols - 2) + tr)
      win.insstr(rows - 1, 0, bl + bs * (cols - 2) + br)
      for line in range(rows - 2):
         win.insstr(line + 1, 0, ls)
         win.insstr(line + 1, cols - 1, rs)
   else:
      win.border()

   # Draw some text?
   if text is not None:
      text = wrap(text, cols - 4)
      y_offset = 0
      if v_center:
         y_offset = (rows - 1) // 2 - len(text) // 2 - 1
      for y, line in enumerate(text):
         if center:
            win.addstr(y + 1 + y_offset, 2 + (cols - 4) // 2 - len(line) // 2, line)
         else:
            win.addstr(y + 1 + y_offset, 2, line)

   # Draw a title?
   if title is not None:
      title = f'{gfx_chars.up_down_left_thin} {title} {gfx_chars.up_down_right_thin}'
      win.addstr(0, cols // 2 - len(title) // 2, title, 
         colors | attrs)

   win.refresh()

   return win

def border (
   win,
   row,
   col,
   width,
   height,
   colors = None):

   colors = curses.color_pair(colors) if colors is not None else curses.color_pair(4) | curses.A_BOLD

   win.addstr(row, col, gfx_chars.border_tl + (gfx_chars.border_ts * (width - 2)) + gfx_chars.border_tr, colors)
   for line in range(height - 2):
      win.addstr(row + 1 + line, col, gfx_chars.border_ls + (' ' * (width - 2)) + gfx_chars.border_rs, colors)
   win.addstr(row + height - 1, col, gfx_chars.border_bl + (gfx_chars.border_bs * (width - 2)) + gfx_chars.border_br, colors)

def scrollbar (
   win, 
   row, 
   col, 
   height, 
   vmin = 0, 
   vmax = 99, 
   value = 0, 
   colors = None):

   if colors is None: colors = curses.color_pair(4) | curses.A_BOLD
   acolors = curses.color_pair(4) | curses.A_REVERSE

   old = win.getbkgd()
   win.attroff(curses.A_REVERSE)
   win.insstr(row, col, gfx_chars.up_arrow, acolors)
   win.insstr(row + height - 1, col, gfx_chars.down_arrow, acolors)

   pos = row + 1 + int((value / (vmax - vmin)) * (height - 3))

   for line in range(row + 1, row + 1 + height - 2):
      if line == pos: continue
      win.insstr(line, col, gfx_chars.vline_thin, curses.color_pair(4))

   win.insstr(pos, col, ' ', curses.color_pair(1) | curses.A_BOLD)
   win.attron(old)

def separator (win, row, bold = False):
   if bold:
      chars = (
         gfx_chars.up_down_right,
         gfx_chars.up_down_left,
         gfx_chars.hline)
   else:
      chars = (
         gfx_chars.up_down_right_thin, 
         gfx_chars.up_down_left_thin,
         gfx_chars.hline_thin)

   h, w = win.getmaxyx()
   win.move(row, 0)
   win.addstr(chars[0])
   win.addstr(chars[2] * (w - 2))
   win.addstr(chars[1])

def message (
   text,
   coords = None,
   rows = None,
   cols = None,
   button_text = None,
   title = None,
   center = True,
   colors = None):

   if button_text is None:
      button_text = 'OK'

   question(
      text, 
      rows = rows, cols = cols,
      choices = ('&OK',), default = 0, title = title,
      colors = colors,
      center = center)

def question (text,
   rows = None,
   cols = None,
   row = None,
   col = None,
   colors = None,
   attrs = None,
   title = None,
   center = True,
   choices = None,
   choice_w = None,
   default = None,
   escape = None):

   # Default size.
   if cols is None:
      cols = 56

   # Default choices are Yes and No.
   if choices is None:
      choices = ('&Yes', '&No')
   
   # This is an Enter to confirm, Escape to cancel question.
   allowed_keys = ''

   # Set up choices.
   choice_color = curses.color_pair(8)
   choice_key_color = curses.color_pair(9) | curses.A_BOLD
   choice_text_color = curses.color_pair(8) | curses.A_DIM
   if choice_w is None: choice_w = 12
   choice_h = 1
   choice_pad = 4
   total_choice_w = len(choices) * choice_w + (choice_pad * (len(choices) - 1))
   allowed_keys = ''

   # If the buttons take up too much room, make things bigger.
   if total_choice_w > cols - 8:
      cols = total_choice_w + 8

   # Format the text into a list of lines.
   wrap_width = cols - 4
   text = wrap(text, width = wrap_width - 2)

   # Use a reasonably-sized window?
   if rows is None:
      rows = 8 if len(text) == 1 else len(text) + 6

   # Use our own newwin function
   win = newwin(rows, cols, row = row, col = col, colors = colors, attrs = attrs, title = title)

   # Display the text.
   win_y, win_x = win.getbegyx()

   for y, line in enumerate(text):
      if center:
         win.addstr(y + 2, 2, line.center(wrap_width))
      else:
         win.addstr(y + 2, 2, line)

   # This is probably some of the worst code I've ever written because
   # I'm a huge goof. Works great!
   def draw_choices (blink = None):
      nonlocal allowed_keys
      y = rows - 3
      x = cols // 2 - total_choice_w // 2

      # Choice backgrounds first
      choice_x = []
      for i, choice in enumerate(choices):
         # A little hacky.
         attr = 0
         if len(allowed_keys):
            if blink and allowed_keys[i].upper() == blink.upper():
               attr = curses.A_REVERSE

         win.addstr(y, x, ' ' * choice_w, choice_text_color | attr)
         choice_x.append(x + choice_w // 2 - len(choice) // 2)
         x += choice_w + choice_pad

      # Then the choice text
      for i, choice in enumerate(choices):
         highlight = False

         # A little hacky.
         attr = 0
         if len(allowed_keys):
            if blink and allowed_keys[i].upper() == blink.upper():
               attr = curses.A_REVERSE

         x = choice_x[i]
         for n, ch in enumerate(choice):
            if ch == '&':
               highlight = True
            elif highlight == True:
               # Highlight the character following the ampersand
               allowed_keys += ch
               win.addstr(y, x, ch, choice_key_color | attr)
               highlight = False
               x += 1
            else:
               win.addstr(y, x, ch, choice_text_color | attr)
               x += 1

   # Flash the selected item.
   def flash (which = None):
      if default is not None and which is None:
         which = allowed_keys[default]

      for n in range(6):
         draw_choices(which)
         win.refresh()
         time.sleep(0.05)
         draw_choices()
         win.refresh()
         time.sleep(0.05)

   draw_choices()

   # Minor help.
   if len(choices):
      temp = f'Press one of the following keys: {", ".join(allowed_keys.upper())}'
      if default is not None:
         temp += ', ENTER'
      if escape is not None:
         temp += ', ESCAPE'
      help(temp)
   else:
      help(f'Press Enter to confirm, or Escape to cancel.')

   win.refresh()

   ret = False
   while True:
      key = stdscr.getch()

      # ASCII?
      if key < 255:
         # Enter?
         if default is not None and chr(key) in '\r\n':
            flash()
            ret = allowed_keys[default]
            break

         if escape is not None and key == 27:
            flash(allowed_keys[escape])
            ret = allowed_keys[escape]
            break

         if not len(choices):
            if chr(key) in '\r\n':
               ret = True
            elif key == 27:
               ret = False
            break

         if chr(key).upper() in allowed_keys.upper():
            #flash(allowed_keys.upper().index(chr(key).upper()))
            flash(chr(key).upper())
            ret = chr(key).upper()
            break

   # Trash our window
   del win
   stdscr.touchline(win_y, rows, True)
   stdscr.refresh()
   help()
   if isinstance(ret, bool): return ret
   return ret.upper()

def viewer (text, rows = None, cols = None, row = None, col = None, colors = None, attrs = None, title = None, center = False, show_meter = True):
   # Use a reasonably-sized window?
   if rows is None:
      rows = curses.LINES - 8
   if cols is None:
      cols = curses.COLS - 8

   # Use our own newwin function
   win = newwin(rows, cols, row = row, col = col, colors = colors, attrs = attrs, title = title)

   # Format the text and display it
   wrap_width = cols - 4
   win_y, win_x = win.getbegyx()
   pad_y = win_y + 1
   pad_x = win_x + 2
   pad_w = cols - 4

   # newwin accepts colors as an int, but we called that already.
   # So convert them here.
   if colors is not None:
      colors = curses.color_pair(colors)
   else:
      colors = curses.color_pair(0)

   if attrs is None: attrs = curses.A_NORMAL

   text = wrap(text, width = wrap_width)
   pad_h = len(text)
   pad = curses.newpad(pad_h + 1, pad_w)
   pad.bkgdset(' ', colors | attrs)
   pad.erase()
   attr = curses.A_BOLD
   for y, line in enumerate(text):
      if center:
         pad.addstr(y, 2, line.center(wrap_width))
      else:
         pad.addstr(y, 0, line)

   # Scroll limit
   scroll = 0
   scroll_limit = len(text) - (rows - 2)
   #win.addstr(4, 4, f'{scroll_limit}')
   scroll_pct = 0.0

   # Help text
   up, down = gfx_chars.up_arrow, gfx_chars.down_arrow
   help_text = f'{up}/{down}/PgUp/PgDn: Scroll Text     Enter: Go Back'
   help(help_text)

   win.refresh()
   need_draw = True
   last_counter = ''
   counter = ''

   help(f'Use arrow keys to scroll up/down. Push ENTER or ESC when done.')

   def redraw ():
      nonlocal scroll, scroll_limit, scroll_pct, last_counter, counter
      last_counter = counter
      try:
         scroll_pct = (scroll / scroll_limit) * 100.0
      except ZeroDivisionError:
         scroll_pct = 0.0
      pad.refresh(scroll, 0, pad_y, pad_x, win_y + rows - 2, win_x + cols - 3)
      counter = f' {scroll+1}/{len(text)} ({scroll_pct:.1f}%) '
      if show_meter:
         if scroll_limit + pad_h < pad_h - 2:
            word = 'lines' if len(text) != 1 else 'line'
            counter = f' All Text ({len(text)} {word}) '
         win.addstr(rows - 1, cols - 1 - len(counter), counter)
         if len(counter) < len(last_counter):
            win.addstr(rows - 1, cols - 1 - len(last_counter), gfx_chars.hline_thin)
      win.refresh()

   while True:
      if need_draw:
         redraw()
         need_draw = False

      key = stdscr.getch()

      # ASCII escape?
      if key == 27 or (key < 255 and chr(key) in '\r\n'):
         help()
         break

      elif key == curses.KEY_UP:
         if scroll > 0:
            scroll -= 1
            need_draw = True

      elif key == curses.KEY_DOWN:
         if scroll < scroll_limit:
            scroll += 1
            need_draw = True

      elif key == curses.KEY_PPAGE:
         scroll -= 8
         if scroll < 0:
            scroll = 0
         need_draw = True

      elif key == curses.KEY_NPAGE:
         scroll += 8
         if scroll > scroll_limit:
            scroll = scroll_limit
         need_draw = True

   # Trash our window
   del win
   del pad
   stdscr.touchwin()
   stdscr.refresh()

def begin_output (
   title = None,
   colors = None,
   rows = None,
   cols = None):

   global output_window, output_scroll_window

   rows = 16 if rows is None else rows
   cols = 60 if cols is None else cols
   colors = 4 if colors is None else colors
   title = 'Output' if title is None else title
   output_window = newwin(rows, cols, title = title, colors = colors)
   row, col = output_window.getbegyx()
   output_scroll_window = curses.newwin(rows - 2, cols - 4, row + 1, col + 2)
   output_scroll_window.scrollok(True)

   output_window.refresh()
   output_scroll_window.refresh()

def write_output (text):
   if output_window is None: return
   if not isinstance(text, str): text = text.decode('ascii')
   output_scroll_window.addstr(text.rstrip() + '\n')
   output_scroll_window.refresh()

def end_output ():
   global output_window, output_scroll_window
   if output_window is None: return
   del output_scroll_window
   del output_window
   output_scroll_window = None
   output_window = None
   stdscr.touchwin()
   stdscr.refresh()

def begin_wait (
   text, 
   title = None, 
   blink = False, 
   colors = None,
   attrs = None,
   double_border = False):

   global waiting_window
   if waiting_window is not None:
      end_wait()

   colors = 0 if colors is None else colors

   if not isinstance(text, list):
      # Make lines from their text.
      lines = wrap(text, 60)
   else:
      lines = text
   max_line_len = max([len(line) for line in lines])
   if max_line_len < 20: max_line_len = 20
   win_w = max_line_len + 4
   win_h = len(lines) + 2
   win = newwin(
      win_h, win_w, 
      title = title, colors = colors, 
      attrs = attrs, double_border = double_border)
   win.erase()
   win.border()

   if blink:
      win.attron(curses.A_BLINK)
   win.attron(curses.A_BOLD)

   for y, line in enumerate(lines):
      win.addstr(y + 1, 2, line.center(max_line_len))

   win.attroff(curses.A_BLINK)
   win.attroff(curses.A_BOLD)
   win.refresh()

   waiting_window = win

def end_wait ():
   global waiting_window
   if waiting_window is None: return
   del waiting_window
   waiting_window = None
   stdscr.touchwin()
   stdscr.refresh()

help_list = []
last_help_text = ''
def help (help_text = None):
   global help_list, last_help_text

   if help_text is None:
      try:
         help_text = help_list.pop()
      except IndexError:
         help_text = ''
   else:
      help_list.append(last_help_text)

   stdscr.insstr(curses.LINES - 1, 0, 
      help_text.center(curses.COLS),
      #curses.color_pair(14))# | curses.A_BOLD | curses.A_REVERSE)
      curses.color_pair(4) | curses.A_BOLD)
   stdscr.refresh()
   last_help_text = help_text

def run_with_output (command, title = None, rows = None, cols = None):
   rows = 32 if rows is None else rows
   cols = 110 if cols is None else cols
   begin_output('Output' if not title else title, rows = rows, cols = cols)
   proc = subprocess.Popen(command, shell = True, 
      stdout = subprocess.PIPE, stderr = subprocess.PIPE, bufsize = 16384)

   while True:
      line = proc.stdout.readline()
      if not line:
         break
      write_output(line)

   proc.wait()

   end_output()
   return proc.returncode

class Observe:
   def __init__ (self, rows = None, cols = None, title = 'Output', colors = None):
      # Create our window
      rows = rows if rows else 26
      cols = cols if cols else 84
      self.win_h = rows
      self.win_w = cols
      self.win = newwin(self.win_h, self.win_w, title = title, colors = colors)
      self.win_y, self.win_x = self.win.getbegyx()

      # Create our scrolling window
      self.subwin = curses.newwin(self.win_h - 2, self.win_w - 4, self.win_y + 1, self.win_x + 2)
      self.subwin.scrollok(True)

      # Default help
      help('Follow the on-screen instructions. Or else.')

      # Append a crumb
      crumb(title)

   def wait_key (self, specific = None):
      while True:
         key = stdscr.getch()

         if specific is not None:
            if isinstance(specific, str) and key < 255:
               if chr(key) == specific:
                  return
            else:
               if key == specific:
                  return

         else:
            return

   def run_program (self, command_line, show_result = True):
      proc = subprocess.Popen(command_line, stdout = subprocess.PIPE, shell = True)
      while True:
         line = proc.stdout.readline()
         if not len(line) and proc.poll() is not None:
            break
         else:
            self.subwin.addstr(line.decode('utf-8'), curses.A_BOLD)
            self.refresh()

      proc.wait()

      if not show_result:
         # They don't want a result window.
         return proc.returncode

      code = proc.returncode
      if code is not None and code != 0:
         # Something went wrong. Let them know about it.
         errwin = newwin(8, 60, colors = 10, title = 'Error',
            text = 'Something went wrong. Try again, or talk to Steven.\n\nPress any key.')
         errwin.refresh()
         stdscr.getch()
         del errwin
         stdscr.touchwin()
         stdscr.refresh()
         self.win.touchwin()
         self.win.refresh()
         self.refresh()

         return False
      elif code is not None and code == 0:
         # Looks OK!
         goodwin = newwin(8, 60, colors = 11, title = 'Success',
            text = 'Looks like that went OK! Please wait...',
            center = True,
            v_center = True)
         goodwin.refresh()
         time.sleep(3)
         del goodwin
         self.win.touchwin()
         self.win.refresh()
         self.refresh()

         return True

      return proc.returncode

   def message (self, text = ''):
      message(text)
      self.refresh()

   def question (self, *args, **kwargs):
      ret = question(*args, **kwargs, colors = 9)
      self.refresh()
      return ret

   def refresh (self):
      self.win.touchwin()
      self.subwin.touchwin()
      self.win.refresh()
      self.subwin.refresh()

   def end (self):
      del self.win
      del self.subwin
      stdscr.touchwin()
      stdscr.refresh()
      help()
      del_crumb()

