import time
import os
import curses
import curses.textpad

import gfx_chars
import draw
from text_input import text_input
from __main__ import stdscr

def make_columns (sizes, items, align = None, header = False):
   if len(items) != len(sizes):
      # Not enough arguments or not enough sizes.
      return '(Invalid Item: Tell Steven About This)'

   # Make sure we have an align function for each column.
   if align is None or len(align) != len(sizes):
      if align is None: align = []
      while len(align) != len(sizes):
         align.append('ljust')

   text = ''
   for index, item in enumerate(items):
      # Use a text alignment function
      try:
         align_func = getattr(str, align[index])
      except (AttributeError, TypeError):
         align_func = getattr(str, 'ljust')

      # Truncate the item text?
      item_text = str(item)
      if len(item_text) > sizes[index] - 1:
         item_text = item_text[:-4] + '...'

      if index == 0 and header:
         text = '-' + align_func(item_text, sizes[index])
      else:
         text += align_func(item_text, sizes[index])

   return text

def menu (
   items = None,
   title = None,
   can_search = True,
   can_escape = True,
   help_text = None,
   erase = True,
   pre_select = 0,
   shadow = False):

   win_color = curses.color_pair(4)
   item_color = curses.color_pair(4) #| curses.A_BOLD
   sel_item_color = curses.color_pair(3) | curses.A_BOLD
   header_color = curses.color_pair(13) | curses.A_BOLD
   separator_color = curses.color_pair(4)
   shadow_color = curses.color_pair(20) | curses.A_BOLD | curses.A_REVERSE

   # No title? Also pad the title.
   if title is None: 
      title = ' Select an Option '
   else:
      title = f' {title} '
   title = f'{gfx_chars.up_down_left_thin}{title}{gfx_chars.up_down_right_thin}'

   # No help text?
   if help_text is None:
      up, down = gfx_chars.up_arrow, gfx_chars.down_arrow
      help_text = f'{up}/{down}/PgUp/PgDn: Move Selection     Enter: Select Item'

      # Searching is for later.
      if can_search:
         help_text += '     S: Search'

      if can_escape:
         help_text += '     Escape: Go Back'

   # No items?
   if items is None or (isinstance(items, list) and len(items) == 0):
      return -2

   # Convert any strings to tuples.
   new = []
   for item in items:
      if isinstance(item, str):
         new.append((item,))
      else:
         new.append(item)
   items = new

   # Properties
   need_draw = True
   scroll = 0
   scroll_off = 2
   sel = 0
   old_sel = -1

   # Calculate the width of the menu
   width = max([len(item[0]) + 2 for item in items])
   if width < 32: width = 32
   width += 4

   item_width = width - 2

   # Is the title longer than the item width?
   if len(title) + 6 > item_width:
      width = len(title) + 6
      item_width = width - 2

   # And the height
   height = min(len(items), 20)
   height += 2
   visible_items = height - 2

   # And the location
   win_y = curses.LINES // 2 - height // 2 - 1
   win_x = curses.COLS // 2 - width // 2 - 1

   # Create a window and a pad
   win = curses.newwin(height, width, win_y, win_x)
   win.bkgdset(' ', win_color)
   win.erase()
   win.attron(curses.A_BOLD)
   win.border()
   win.attroff(curses.A_BOLD)

   if shadow:
      schar = '\u2592'
      for line in range(win_y + 1, win_y + height):
         stdscr.insstr(line, win_x + width, schar, shadow_color)
      stdscr.insstr(win_y + height, win_x + 1, schar * width, shadow_color)
      stdscr.refresh()

   pad = curses.newpad(len(items), item_width)
   pad.bkgdset(' ', win_color)

   # Draw the title
   attrs = win_color
   attrs |= (curses.A_BOLD)
   win.addstr(0, width // 2 - len(title) // 2, title, attrs)

   # Initial item draw
   for line, item in enumerate(items):
      if item[0].startswith('-'):
         if len(item[0]) > 1:
            # This is a header; use the remaining item text.
            text = item[0][1:]
            pair = header_color | curses.A_UNDERLINE
         else:
            # This is a separator.
            text = gfx_chars.dotted_line * (item_width - 2)
            pair = separator_color
      else:
         text = item[0]
         pair = item_color
      x = 0
      pad.insstr(line, x, ' ', pair & ~curses.A_UNDERLINE)
      pad.insstr(line, x, text.ljust(item_width), pair)
      pad.insstr(line, x, ' ', pair & ~curses.A_UNDERLINE)
      pad.attroff(curses.A_UNDERLINE)

   # And initial help text draw.
   draw.help(help_text)

   stdscr.refresh()
   win.refresh()

   # Clean up the window and pad
   def clean_up ():
      nonlocal pad, win, erase
      if erase:
         win.touchwin()
         win.refresh()
      del pad
      del win
      if erase:
         stdscr.touchwin()
         stdscr.refresh()

   # Redraw function
   def redraw ():
      nonlocal old_sel

      # Draw the old and new items
      if old_sel >= 0:
         pad.chgat(old_sel, 0, item_width, item_color)
      pad.chgat(sel, 0, item_width, sel_item_color)

      # Draw a counter
      counter = f' {sel+1}/{len(items)} '
      win.addstr(height - 1, width - 1 - len(counter), counter, win_color)

      # And maybe a scrollbar.
      if len(items) > visible_items:
         draw.scrollbar(
            win, 1, width - 1, visible_items,
            vmin = 0, vmax = len(items) - visible_items,
            value = scroll)

      # Refresh
      stdscr.refresh()
      win.refresh()
      pad.refresh(scroll, 0, win_y + 1, win_x + 1, 
         win_y + visible_items, win_x + item_width)

      old_sel = sel

   # Move the cursor up, scrolling if necessary
   def move_up (places = 1):
      nonlocal need_draw, sel, scroll
      prev_sel, prev_scroll = sel, scroll
      for n in range(places):
         while True:
            if sel == 0: 
               # The first menu item may be a header or separator
               # by accident, or on purpose. If we landed on that,
               # reset the selection.
               if items[sel][0].startswith('-'):
                  # Yep.
                  sel, scroll = prev_sel, prev_scroll
                  break

               # No, ended on a normal item.
               break

            sel -= 1
            if sel < scroll + scroll_off and scroll > 0:
               scroll -= 1

            # Skip separators
            if not items[sel][0].startswith('-'): break
      need_draw = True

   # Move the cursor down, scrolling if necessary
   # Unlike move_up, this can "target" a particular key
   def move_down (places = 1, target = None):
      nonlocal need_draw, sel, scroll
      if target is not None: places = len(items)
      if len(items[0]) > 1 and target == items[0][1]:
         # Do nothing; we're already at the target.
         return
      double_break = False
      for n in range(places):
         while True:
            if sel == len(items) - 1: break
            sel += 1
            if sel > scroll + visible_items - (scroll_off + 1) and scroll < len(items) - visible_items:
               scroll += 1

            # Did we find a matching target key?
            if target is not None and len(items[sel]) > 1:
               if items[sel][1] == target:
                  # We did!
                  double_break = True
                  break

            # Skip separators
            if not items[sel][0].startswith('-'): break

         # Double break!
         if double_break: break
      need_draw = True

   # Search for an item
   def do_search ():
      nonlocal need_draw, items, sel

      search_text = text_input(
         title = 'Search for Item',
         prompt = 'Enter the text to search for:')

      match = False

      if len(search_text):
         for index, item in enumerate(items):
            # Skip?
            if index <= sel: continue

            if item[0][0] != '-' and search_text.lower() in item[0].lower():
               # This is a match.
               match = True
               sel = 0
               while sel != index:
                  move_down()

               break

         # Didn't find anything?
         if not match:
            draw.message((
               f'No items found matching "{search_text}".'
               '\n\n(The search function only searches from the cursor downward.)'))
         else:
            # Show a quick "found it" message.
            temp = draw.newwin(5, 44)
            temp.addstr(2, 2, 'Found a matching item.'.center(40))
            temp.refresh()
            time.sleep(0.8)
            del temp
            stdscr.touchwin()
            stdscr.refresh()

      win.touchwin()
      need_draw = True

   # Preselect an item?
   if isinstance(pre_select, str):
      move_down(target = pre_select)
   else:
      move_down(pre_select)

   # Now select the first reasonable item if we landed on a separator
   # or a header.
   while items[sel][0].startswith('-'):
      sel += 1

   while True:
      if need_draw:
         need_draw = False
         redraw()

      key = stdscr.getch()

      if key > 0 and key < 255:
         # This is a standard ASCII key.
         #if chr(key) in '\r\n':
         if key == 0x0A:
            # This item was selected.
            clean_up()

            if len(items[sel]) > 1:
               ret = items[sel][1]
            else:
               ret = sel

            return ret

         # Search key.
         if can_search and chr(key) in 'sS':
            do_search()

         # Escape is ASCII 27.
         elif key == 27:
            if can_escape:
               clean_up()
               return -1

      elif key == curses.KEY_UP:
         move_up()

      elif key == curses.KEY_DOWN:
         move_down()

      elif key == curses.KEY_PPAGE:
         move_up(10)

      elif key == curses.KEY_NPAGE:
         move_down(10)

      elif key == curses.KEY_HOME:
         while sel > 0:
            move_up()

      elif key == curses.KEY_END:
         while sel < len(items) - 1:
            move_down()

      # Sleep a bit.
      time.sleep(0.01)

