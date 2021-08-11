import os
import datetime
import time

import utils
import draw
import programmer
from menu import menu
from text_input import text_input
from __main__ import crumb, del_crumb, stdscr

repr_data = './data/repressurizer'

def do_repressurizer ():
   message = ('Plug the programmer into the programming header '
      'with the white arrow on the circuit board pointing to the '
      'red wire on the programmer.\n'
      '\n'
      'Then, connect the special USB cable\'s connector to the '
      'two-pin header in the upper left corner of the circuit board. '
      'Polarity is not important.\n'
      '\n'
      'Press ENTER when ready, or ESCAPE to cancel.')

   crumb('Program a Repressurizer')

   prog = programmer.BoardProgrammer()
   prog.add_target('atmega88',
      message = message, title = 'Programming',
      fuses = (0x62, 0xD5, 0xFF),
      hex_file = f'{repr_data}/main.hex',
      eeprom_hex = f'{repr_data}/main.eep',
      can_skip = False,
      speed = 128)

   if not prog.program():
      draw.message(('Unable to program CPU/EEPROM.'), colors = 10)
      return False

   draw.begin_wait('Successfully programmed!', colors = 11)
   time.sleep(3.0)
   draw.end_wait()

   del_crumb()
   return True

