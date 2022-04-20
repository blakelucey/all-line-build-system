import os
import sys
import json
import shutil
import time
import datetime
import subprocess
import curses

import draw
import utils
import config
from __main__ import stdscr, crumb, del_crumb
from logger import log_debug

class Partitioner:
   def __init__ (self):
      self.dev = config.get('sd_card_device')
      self.script = bytearray()
      self.interfix = 'p' if 'mmc' in self.dev else ''
      self.part_types = []

   def add_partition (self, size = None, is_vfat = False):
      if isinstance(size, int): 
         size = (f'+{size}M').encode('ascii')
      elif size is None:
         size = b''
      else:
         size = size.encode('ascii')

      self.script += b'n\np\n' + bytes((ord('1') + len(self.part_types),)) + b'\n\n' + size + b'\n'
      if is_vfat:
         self.script += b't\nc\n'

      self.part_types.append(is_vfat)

   def format_partition (self, id):
      kind = 'vfat' if self.part_types[id] else 'ext2'
      draw.begin_wait(f'Formatting partition {self.dev + self.interfix + str(id+1)} as {kind.upper()}...')
      dev = self.dev
      if dev.endswith('/'): dev = dev[:-1]
      command = f'sudo mkfs.{kind} {dev + self.interfix + str(id+1)}'
      proc = subprocess.run(command, shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
      if proc.returncode != 0:
         draw.end_wait()
         draw.message(f'Unable to format partition {self.dev + self.interfix + str(id+1)}')
         return False
      time.sleep(2.0)
      draw.end_wait()
      return True

   def safety_check (self):
      return not 'nvme' in self.dev and not utils.is_root_device(self.dev)

   def write_partitions (self):
      if not self.safety_check():
         draw.message(('Somehow this system was set up to write directly '
            f'to {self.dev}, which is probably a very bad idea.\n\n'
            'Use the "Configure this Program" option in the main menu to '
            'ensure the right SD card device is being used.'),
            colors = 10)
         return False

      draw.begin_wait(f'Clearing {self.dev}...')
      code = os.system(f'sudo dd if=/dev/zero of={self.dev} bs=16M count=1 > /dev/null 2>&1')
      if code >> 8 != 0:
         draw.end_wait()
         return False
      time.sleep(1.0)
      draw.end_wait()

      draw.begin_wait(f'Partitioning {self.dev}...')
      time.sleep(1.0)
      self.script = b'o\n' + self.script + b'w\n'
      proc = subprocess.Popen(f'sudo fdisk {self.dev} > /dev/null 2>&1', shell = True, stdin = subprocess.PIPE)
      proc.communicate(self.script)
      code = proc.returncode
      draw.end_wait()
      return True

   def format_partitions (self):
      for id in range(len(self.part_types)):
         if not self.format_partition(id):
            return False
      return True

   def mount_partition (self, id, name, is_vfat = False):
      path = f'/dev/shm/{name}'
      part = f'{self.dev}{self.interfix}{id+1}'
      proc = subprocess.run(f'lsblk -nrpo KNAME | grep {part} > /dev/null 2>&1', shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
      if proc.returncode != 0:
         draw.message(f'Unable to find partition "{part}".', colors = 10)
         return (False, path)

      if not os.path.exists(path):
         os.mkdir(path, 0o777)

      options = ''
      if is_vfat:
         options = '-o rw,uid=1000,gid=1000'

      proc = subprocess.run(f'sudo mount {part} {path} {options}', shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
      out, err = proc.stdout, proc.stderr

      if proc.returncode != 0:
         out = '\n   '.join(out.decode('utf-8').splitlines())
         err = '\n   '.join(err.decode('utf-8').splitlines())
         claim = f'Standard output text:\n{out}Standard error text:\n{err}'
         draw.viewer(
            f'Unable to mount partition "{part}" to path "{path}". Is your SD card well-seated?\n\n(Mount returned error code {proc.returncode}.\n\n{claim}.)',
            colors = 10, attrs = curses.A_BOLD)
         return (False, path)

      user = os.getlogin()
      code = os.system(f'sudo chown {user}:{user} {path}')
      if code >> 8 != 0:
         draw.message(f'Unable to set permissions for partition "{part}".', colors = 10)
         return (False, path)

      return (True, path)

   def unmount_partition (self, name, is_device_name = False):
      path = f'/dev/shm/{name}' if not is_device_name else name

      # Is it mounted at all?
      code = os.system(f'mount | grep {path} > /dev/null 2>&1')
      if code >> 8 != 0:
         # It doesn't look that way.
         draw.begin_wait(f'{path} was not mounted; skipping.')
         time.sleep(0.7)
         draw.end_wait()
         return True

      draw.begin_wait(f'Unmounting {path}...')

      code = os.system(f'sudo umount {path} > /dev/null 2>&1')
      if code >> 8 != 0:
         draw.message((f'Unable to unmount partition "{part}". Unplugging the SD card '
            'may leave it in an unknown state, but likely won\'t damage it.\n'
            '\n'
            'Steven may be able to rescue it for you.'), colors = 10)
         draw.end_wait()
         return False

      time.sleep(0.5)
      draw.end_wait()
      return True

   def unmount_all (self):
      for dev in [d.path for d in os.scandir('/dev')]:
         if dev.startswith(config.data['sd_card_device']) and dev[-1] in '123456789':
            self.unmount_partition(dev, is_device_name = True)

class SDCardBuilder:
   def __init__ (self, buildroot_version = None, board_name = None):
      # No board name? Use the Pi 2 board for now.
      if board_name is None: board_name = 'all_line_pi2'

      # No version? Use the version from the configuration file.
      if buildroot_version is None:
         self.br_version = config.get('buildroot_version')
      else:
         self.br_version = buildroot_version

      self.br_path = f'./buildroot/{self.br_version}'
      self.board_name = board_name

   def find_sd_card (self):
      # Is the SD card present?
      while True:
         result = draw.question(('Insert an SD card to program. Its contents will be wiped.\n'
            '\n'
            'Press ENTER when ready, or ESCAPE to cancel.\n'
            'You can also press S to skip this step,\n'
            'or P to skip the partition/format process.'),
            choices = ('&OK', '&Cancel', '&Skip', 'Skip &Partitioning'),
            choice_w = 18,
            default = 0, escape = 1)

         if result == 'C':
            return False

         elif result == 'S':
            return 'skip'

         elif result == 'P':
            # Skip partitioning
            return 'skip_part'

         # Must have wanted to go ahead.
         # See if we can find the SD card device.
         # We'll ask lsblk to output the kernel names only with no headings,
         # as well as the full device path (e.g., sda -> /dev/sda)
         draw.begin_wait('Checking for SD card...')
         proc = subprocess.run(f'lsblk -nrpo KNAME | grep {config.get("sd_card_device")} > /dev/null 2>&1', shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
         if proc.returncode != 0:
            time.sleep(1.0)
            draw.end_wait()
            # No, it isn't.
            result = draw.question('No SD card was found.\n\nSelect a different device?')
            if result == 'N':
               return False
            else:
               new_device = config.do_device()
               if new_device is not None:
                  config.data['sd_card_device'] = new_device
                  config.save()
         else:
            time.sleep(1.0)
            draw.end_wait()
            return True

   def prepare_sd_card (self):
      part = Partitioner()
      part.unmount_all()
      part.add_partition(100, True)    # /boot
      part.add_partition(150, False)   # /
      part.add_partition(150, False)   # /program
      part.add_partition(None, False)  # /config (remaining space)
      if not part.write_partitions(): return False
      if not part.format_partitions(): return False
      return True

   def prepare_buildroot (self):
      rebuild = False
      message = (f'There is no cached output for the board definition "{self.board_name}", or it is missing some important files.\n'
         '\n'
         'This means that a full re-compile is necessary, which will take a while.\n'
         '\n'
         'Press ENTER to go ahead, or ESCAPE to cancel.')

      log_debug(f'cache path {self.cache_path}')

      if not os.path.exists(self.cache_path):
         result = draw.question(message, title = 'Missing Cache', default = 0, escape = 1)
         if result == 'N':
            return False
         rebuild = True

      if 'pi4' in self.cache_path:
         self.required_files = [
            f'{self.cache_path}/bcm2711-rpi-4-b.dtb',
            #f'{self.cache_path}/bootcode.bin',
            f'{self.cache_path}/fixup4.dat',
            f'{self.cache_path}/start4.elf',
            f'{self.cache_path}/zImage',
            f'{self.cache_path}/rootfs.tar.gz',
            f'{self.cache_path}/overlays']
      else:
         self.required_files = [
            f'{self.cache_path}/bcm2709-rpi-2-b.dtb',
            f'{self.cache_path}/bootcode.bin',
            f'{self.cache_path}/fixup.dat',
            f'{self.cache_path}/start.elf',
            f'{self.cache_path}/zImage',
            f'{self.cache_path}/rootfs.tar.gz',
            f'{self.cache_path}/overlays']

      log_debug(f'required files {self.required_files}')

      cached_files = [self.cache_path + '/' + fn for fn in os.listdir(self.cache_path)]
      missing = False
      for required in self.required_files:
         if required not in cached_files:
            log_debug(f'MISSING FILE: {required}')
            missing = True

      if missing:
         result = draw.question(message, title = 'Missing Required Files', default = 0, escape = 1)
         if result == 'N':
            return False
         rebuild = True

      # Rebuild the entire source tree?
      if rebuild: 
         if not self.make_buildroot():
            return False

      return True

   def make_buildroot (self):
      draw.begin_wait(f'Recompiling "{self.br_version}" for board "{self.board_name}"...')
      begin = datetime.datetime.now()
      code = os.system('make -C "{self.br_path}" 2> /dev/shm/br_errors')
      if code >> 8 != 0:
         draw.end_wait()
         draw.message(('There was a problem compiling Buildroot.\n'
            '\n'
            'Unfortunately, you\'ll have to talk to Steven.'), colors = 10)
         return False
      draw.end_wait()
      end = datetime.datetime.now()
      dur = (end - start).total_seconds()
      h, m, s = dur // 3600, (d // 60) % 60, int(d % 60)
      draw.message((f'Success! That took {h} hours, {m} minutes and {s} seconds.\n'
         '\n'
         'Press ENTER to continue.'), colors = 11)
      return True

   def build (self):
      # Does it exist?
      if not os.path.exists(self.br_path):
         message = f'Buildroot version "{self.br_version}" cannot be found.'
         draw.message(message, colors = 10)
         return False

      # Does the board path exist?
      self.board_path = f'./buildroot/{self.br_version}/board/{self.board_name}'
      self.cache_path = f'{self.board_path}/output'
      if not os.path.exists(self.board_path):
         message = f'Buildroot is present, but the board definition "{self.board_name}" cannot be found.'
         draw.message(message, colors = 10)
         return False

      # Does the SD card exist?
      result = self.find_sd_card()
      skip_part = False
      if result == 'skip':
         return True
      elif result == 'skip_part':
         skip_part = True
      elif result == False:
         # They canceled.
         return False

      # Looks OK.
      # Let's do a wipe, then partition/format, then copy over all of the data.
      if not skip_part:
         if not self.prepare_sd_card():
            message = f'Something went wrong preparing the SD card.'
            draw.message(message, colors = 10)
            return False
      else:
         part = Partitioner()
         part.unmount_all()

      # Okay, we found Buildroot, the board definition, the SD card,
      # and the card has been cleared, partitioned and formatted.
      # We'll need to see if the board has a cached final build.
      if not self.prepare_buildroot():
         return False

      # Mount our partitions.
      draw.begin_wait('Mounting partitions...')
      part = Partitioner()
      boot_part = part.mount_partition(0, 'boot', is_vfat = True)
      root_part = part.mount_partition(1, 'root')
      prog_part = part.mount_partition(2, 'prog')
      conf_part = part.mount_partition(3, 'conf')
      if not boot_part[0] or not root_part[0] or not prog_part[0] or not conf_part[0]:
         draw.end_wait()
         return False
      boot_path, root_path, prog_path, conf_path = \
         boot_part[1], root_part[1], prog_part[1], conf_part[1]
      time.sleep(1.0)
      draw.end_wait()

      self.boot_path = boot_path
      self.root_path = root_path
      self.prog_path = prog_path
      self.conf_path = conf_path

      # Now we need to copy:
      #  - Pi firmware
      #  - Linux kernel
      #  - Custom cmdline.txt and config.txt
      #  - The root file system

      draw.begin_wait('Copying boot-up files...')
      try:
         for required in self.required_files:
            # Don't copy the root file system; that's for later.
            if 'rootfs' in required: continue
            if os.path.isdir(required):
               utils.copy_tree(required, boot_path.rstrip('/') + '/' + os.path.basename(required))
            else:
               shutil.copy(required, boot_path.rstrip('/') + '/' + os.path.basename(required))
            time.sleep(0.25)

         # Copy the cmdline.txt and config.txt files.
         shutil.copy(f'{self.cache_path}/../cmdline.txt', f'{boot_path}/cmdline.txt')
         shutil.copy(f'{self.cache_path}/../config.txt', f'{boot_path}/config.txt')
      except (IOError, OSError, PermissionError) as e:
         draw.message(f'Unable to copy required files.\n\nPython says: {e}', colors = 10)
         return False
      draw.end_wait()

      # Un-tar the root file system
      draw.begin_output(rows = 35, cols = 120, title = 'Decompressing Root File System')
      proc = subprocess.Popen(
         f'tar xvzf {self.cache_path}/rootfs.tar.gz -C {root_path}',
         shell = True,
         stdout = subprocess.PIPE, stderr = subprocess.PIPE)

      while True:
         line = proc.stdout.readline()
         if not line: break
         draw.write_output(line.decode('utf-8'))
         time.sleep(0.001)

      draw.end_output()

      draw.begin_wait('Synchronizing file systems...')
      os.system('sync')
      draw.end_wait()

      # Looks good!
      return True

   def cleanup (self):
      part = Partitioner()
      if not part.unmount_partition('boot'): return False
      if not part.unmount_partition('root'): return False
      if not part.unmount_partition('prog'): return False
      if not part.unmount_partition('conf'): return False
      return True

# This is for making a development card and doesn't actually put any
# software on the system.

def do_dev_card ():
   # Have them select a Buildroot version and build

   card = SDCardBuilder()
   pass

