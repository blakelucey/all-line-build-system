# Very intricate text input handling
# Includes required prefixes, pattern matching, numeric range matching,
# and custom error messages.

import curses
import re
import draw
from wrap import wrap
from __main__ import stdscr

ip_address_regex = '^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(\.|$)){4}'

def text_input (
   text = None,
   max_len = None,
   title = None,
   prompt = None,
   can_escape = True,
   force_width = None,
   border = True,
   coords = None,
   relative_to = None,
   key_handler = None,
   param = None,
   prefix = None,
   match = None,
   match_message = None,
   match_range = None,
   match_range_message = None):

   # We can't match multiple types of the things.
   if match is not None and match_range is not None:
      raise RuntimeError('Cannot match multiple data types.')

   need_draw = True
   force_draw = False
   max_len = 1000 if not max_len else max_len
   max_wrap = int(curses.COLS * 0.575) if force_width is None else force_width
   max_space = 1024
   pos = 0

   if match_message is None:
      match_message = 'Sorry, that value is not valid.'

   if match_range_message is None:
      match_range_message = 'Sorry, that value is not valid.'

   # No text yet?
   if text is None: text = ''

   # Non-removeable prefix?
   if prefix is not None:
      text = prefix

   # Calculate the window size
   # These may have been provided for us for integration into another
   # dialog window; if so, use those.
   if coords is None:
      if prompt is not None:
         prompt = wrap(prompt, width = max_wrap)
         width = max_wrap + 4
         height = len(prompt) + 4
      else:
         width = max_len + 4
         if width > curses.COLS - 20:
            width = curses.COLS - 20
         height = 3

      # And the position of the window and the text
      win_y = curses.LINES // 2 - height // 2
      win_x = curses.COLS // 2 - width // 2
   else:
      win_y, win_x, height, width = coords
      max_wrap = width - 4

      if prompt is not None:
         prompt = wrap(prompt, width = max_wrap)

      # Are we relative to another window/pad?
      if relative_to is not None:
         rel_y, rel_x = relative_to.getbegyx()
         win_y += rel_y
         win_x += rel_x

   # The text area is always on the last line of the window
   text_x = win_x + (2 if not relative_to else 1)
   text_y = win_y + height - 2
   text_w = width - (4 if not relative_to else 2)
   text_h = 1

   # Set up the scroll stops
   scroll = 0
   scroll_end = scroll + text_w

   # Already some text to display?
   if len(text):
      pos = len(text)
      if pos > scroll_end:
         scroll = pos - text_w + 4
         scroll_end = scroll + text_w

   # Now create the window and its pad
   win = curses.newwin(height, width, win_y, win_x)
   win.bkgdset(' ', curses.color_pair(4) | curses.A_BOLD) # | curses.A_STANDOUT)
   win.clear()
   if border:
      win.border()

   pad = curses.newpad(text_h, max_space)

   # This is a *weird* hack to get ncurses to not change the cursor
   # color. For some reason it would alternate between dim and not dim.
   # Using a space doesn't fix it, but using a non-printable character does.
   pad.bkgdset('\x01', curses.color_pair(6) | curses.A_BOLD)

   # Check against valid matches, if requested.
   def validate ():
      nonlocal match, match_message
      nonlocal match_range, match_range_message

      if not match and not match_range:
         return True

      if match is not None:
         if not re.match(match, text):
            draw.message(match_message)
            return False

         return True

      if match_range is not None:
         a, b = match_range
         if type(a) != type(b):
            raise RuntimeError('Mismatched match types in text_input.')

         try:
            convert = type(a)(text)
         except ValueError:
            draw.message('I\'m not sure that\'s a valid number.')
            return False

         if convert < a or convert > b:
            draw.message(match_range_message)
            return False

         return True

   # Clean up and remove the window.
   def clean_up ():
      nonlocal pad, win
      win.touchwin()
      win.refresh()
      del pad
      del win
      stdscr.touchwin()
      stdscr.refresh()
      curses.curs_set(0)
      draw.help()

   # Some things are only drawn initially.
   init = True
   def redraw ():
      nonlocal need_draw, text, pos, scroll, relative_to, init, force_draw
      curses.curs_set(0)
      chars = f' {len(text)}/{max_len} '
      if relative_to: chars = chars.strip()

      if init or force_draw:
         force_draw = False
         if isinstance(prompt, list):
            for y, line in enumerate(prompt):
               win.addstr(y + 1, 2, line)
         win.touchwin()
         win.refresh()
         init = False

      win.addstr(height - 1, text_w + 1 - len(chars), chars,
         curses.color_pair(13) | curses.A_BOLD)
      win.refresh()
      pad.erase()
      pad.addstr(0, 0, text)
      pad.refresh(0, scroll, text_y, text_x, 
         text_y + text_h - 1, text_x + text_w - 1)
      stdscr.move(text_y, text_x + pos - scroll)
      curses.curs_set(2)
      need_draw = False

   # How about some help?
   help_text = f'Enter text using the keyboard.'
   if can_escape:
      help_text += ' Use the ESC key to cancel.'
   draw.help(help_text)

   # Loop away!
   while True:
      if need_draw or force_draw:
         redraw()

      key = stdscr.getch()

      if key < 255:
         # ASCII escape?
         if key == 27 and can_escape:
            clean_up()
            return None

         elif chr(key) in '\r\n':
            if validate():
               clean_up()
               return text

            need_draw = True
            force_draw = True

            # Redraw a relative?
            if relative_to is not None:
               relative_to.touchwin()
               relative_to.refresh()

         else:
            if len(text) < max_len:
               text = text[:pos] + chr(key) + text[pos:]
               pos += 1
               if pos >= scroll_end:
                  scroll, scroll_end = scroll + 1, scroll_end + 1
               need_draw = True

      elif key == curses.KEY_DC:
         # Remove the following character.
         if pos < len(text):
            text = text[:pos] + text[pos + 1:]
            need_draw = True

      elif key == curses.KEY_BACKSPACE:
         # Remove a character, unless we shouldn't.
         if pos > 0:
            if (prefix is not None and pos > len(prefix)) or (prefix is None):
               text = text[:pos - 1] + text[pos:]
               pos -= 1
               if pos < scroll:
                  scroll, scroll_end = scroll - 12, scroll_end - 12
                  if scroll < 0: 
                     scroll = 0
                     scroll_end = scroll + text_w
               need_draw = True

      elif key == curses.KEY_LEFT:
         # Move the cursor left.
         if pos > (len(prefix) if prefix else 0):
            # Don't cursor into the prefix.
            pos -= 1
            if pos < scroll:
               scroll, scroll_end = scroll - 12, scroll_end - 12
               if scroll < 0: 
                  scroll = 0
                  scroll_end = scroll + text_w
            need_draw = True

      elif key == curses.KEY_RIGHT:
         if pos < len(text):
            pos += 1
            if pos >= scroll_end:
               scroll, scroll_end = scroll + 1, scroll_end + 1
            need_draw = True
            #if pos > scroll_end

      elif key == curses.KEY_END:
         pos = len(text)
         if len(text) > text_w:
            scroll = len(text) - 16
            if scroll < 0: scroll = 0
            scroll_end = scroll + text_w
         need_draw = True

      elif key == curses.KEY_HOME:
         scroll = 0
         pos = len(prefix) if prefix else 0
         need_draw = True

      else:
         if key:
            if callable(key_handler):
               key_handler(key, pos, text, param)

