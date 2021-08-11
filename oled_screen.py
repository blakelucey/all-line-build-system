import os
import datetime
import time

import utils
import draw
import programmer
from menu import menu
from text_input import text_input
from __main__ import crumb, del_crumb, stdscr

screen_data = './data/oled_screen'

def do_oled_screen ():
   message = ('Plug the programmer into the programming header '
      'with the white arrow on the circuit board pointing to the '
      'red wire on the programmer.\n'
      '\n'
      'Then, connect HALF of the special USB cable\'s connector to the '
      'left-most pin of the white 6-pin connector. The white connector should be on the bottom. '
      'Again MAKE SURE this is only connected to 1 pin on the header.\n'
      '\n'
      'Press ENTER when ready, or ESCAPE to cancel.')
   do_prompt = True

   crumb('Program an OLED screen')

   while True:
      prog = programmer.BoardProgrammer()
      prog.add_target('atmega644p',
         message = message, title = 'Programming',
         fuses = (0xFF, 0xD0, 0xFD),
         hex_file = f'{screen_data}/main.hex',
         eeprom_hex = f'{screen_data}/main.eep',
         can_skip = False,
         require_prompt = do_prompt,
         speed = 0.1)

      if not prog.program():
         draw.message(('Unable to program CPU/EEPROM.'), colors = 10)
         return False

      draw.begin_wait('Successfully programmed!', colors = 11)
      time.sleep(1.25)
      draw.end_wait()
      result = draw.question('Do you want to program another OLED screen?')
      do_prompt = False
      if result == 'N':
         del_crumb()
         return True
      
   return True

