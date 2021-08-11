from __main__ import stdscr
import textwrap
import itertools

def wrap (text, width = 80):
   # Oh my gosh this is horrible
   wrapper = textwrap.TextWrapper(width = width, drop_whitespace = False, replace_whitespace = False)
   split = [' ' if len(line) == 0 else line for line in text.splitlines()]
   data = [wrapper.wrap(i) for i in split if i != '']
   data = list(itertools.chain.from_iterable(data))
   return data

def old_wrap (text, width = None):
   if width is None: width = curses.COLS

   # Split into lines on newline.
   lines = text.split('\n')
   out = []

   for line in lines:
      if not len(line):
         out.append('')
         out.append('')
         continue

      # Split into words on space.
      words = line.split(' ')

      count = 0
      for word in words:
         # Will it fit?
         if count + len(word) > width:
            count = 0
            out.append('')
         count += len(word) + 1
         if not len(out): out.append('')
         out[-1] += (word + ' ')

   return [line.rstrip() for line in out]

