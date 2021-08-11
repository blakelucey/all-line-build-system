# All-Line Equipment Company

import os
import sys
import time
import traceback

from utils import *
from remotesystem import RemoteSystem
from remotelink import RemoteLink, RemoteLinkError
from remoteparam import RemoteParam
from remotedisplay import RemoteDisplay
from recordstorage import RecordStorage
from interprocess import InterprocessServer, RemoteHaltRequest
from reporting import Reporting
from network import Network
from timewatcher import TimeWatcher
from alertwatcher import AlertWatcher
from firmwarewatcher import FirmwareWatcher
from tankmonitorwatcher import TankMonitorWatcher
from remotelogger import LogWatcher
from rebootwatcher import RebootWatcher, RebootException
from smtpconfig import SmtpConfig
from usbwatcher import UsbWatcher
from eventlog import EventLog, log_event
from logger import *

log_info('System is starting up.')

def ipc_halt (skt, data):
   '''Raises the above exception; attached to IPC request type 'halt'.'''
   raise RemoteHaltRequest()

try:
   link = RemoteLink()
   ipc = InterprocessServer()
   evt = EventLog(ipc)
   remote = RemoteSystem(link, ipc)
   display = RemoteDisplay(remote, ipc)
   timewatcher = TimeWatcher(remote, ipc)
   alertwatcher = AlertWatcher(remote, ipc, display)
   fwwatcher = FirmwareWatcher(remote, ipc, display, link)
   rbwatcher = RebootWatcher(ipc)
   tmwatcher = TankMonitorWatcher(remote, ipc)
   storage = RecordStorage(remote, tmwatcher, alertwatcher, ipc)
   reporting = Reporting(remote, storage, ipc)
   logwatcher = LogWatcher(remote)
   smtpconfig = SmtpConfig(ipc)
   network = Network(remote, ipc)

   ipc.add_handler('halt', ipc_halt)

   log_event('System', 'System has started up successfully.')

   while True:
      try:
         remote.poll()
         logwatcher.poll()
         timewatcher.poll()
         storage.poll()
         network.poll()
         alertwatcher.poll()
         tmwatcher.poll()
         fwwatcher.poll()
         ipc.poll()
         reporting.poll()

         # Yield to other tasks
         time.sleep(0.005)
      except RemoteLinkError as rle:
         log_info('Remote link error. Resetting link.')
         link.flush()
         link.sync_and_challenge()
         time.sleep(0.05)

except RemoteLinkError as e:
   log_error('Remote link error occurred during initialization: {}'.format(e.message))
   traceback.print_exc()

except RemoteHaltRequest:
   log_info('Remote halt request. Exiting.')
   reporting.stop_cron()
   ipc.close()
   sys.exit(0)

except KeyboardInterrupt:
   log_info('SIGINT received. Exiting.')
   reporting.stop_cron()
   ipc.close()
   sys.exit(0)

except RebootException:
   log_info('A system reboot was requested.')
   log_info('Synchronizing file systems...')
   os.system('sync')
   log_info('File systems OK. Rebooting.')
   os.system('reboot')

except Exception as e:
   text = traceback.format_exc()
   log_error('Uncaught exception: {} -> {}'.format(e, repr(e)))
   log_error('***')
   log_error(traceback.format_exc())
   log_error('***')
   log_info('Attempting to continue normally.')

