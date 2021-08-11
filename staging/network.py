# All-Line Equipment Company

import time
import os
import shutil
import sys
import subprocess
import struct
import socket
import traceback

from logger import *
from pollsomething import Pollable
from eventlog import log_event

eth_file = '/etc/network/interfaces'
def _execute (parts):
   proc = subprocess.Popen(parts, stdout = subprocess.PIPE)
   out, _ = proc.communicate()

   return out

class NetworkInterface:
   def __init__ (self, filename):
      self.used = False
      self.name = 'none'
      self.use_dhcp = False
      self.ip_address = '0.0.0.0'
      self.subnet_mask = '255.255.255.255'
      self.gateway = '0.0.0.0'
      self.dns = '0.0.0.0'
      self.host_name = socket.gethostname()
      self.failed_path = '/dev/shm/dhcp-lease-failed'
      self.filename = filename

   def change_to_static (self):
      with open(eth_file, 'r') as f:
         data = f.readlines()
      data[3]='iface eth0 inet static\n'
      with open(eth_file, 'w') as f:
         f.writelines(data)
      if os.path.exists(self.failed_path):
         os.system('rm '+self.failed_path)
      os.system('ifdown eth0')
      os.system('ifup eth0')

   def update_eth_file (self):
      with open(eth_file, 'r') as f:
         data = f.readlines()
      data[4]='address '+self.ip_address+'\n'
      data[5]='netmask '+self.subnet_mask+'\n'
      data[6]='gateway '+self.gateway+'\n'
      data[7]='dns-nameservers '+self.dns+'\n'
      with open(eth_file, 'w') as f:
         f.writelines(data)

   def parse_dhcp (self):
      errors = False
      if os.path.exists(self.failed_path):
         log_info('DHCP recently failed, will not attempt to parse_dhcp, changing system back to its default static configuration...')
         self.change_to_static()
         errors = True
      else:
         # Deduce our IP address
         out = _execute(['/sbin/ifconfig', self.name])
         lines = [line.strip() for line in out.split('\n')]

         addr_parts = lines[1].split(' ')
         _, self.ip_address = addr_parts[1].split(':')
         _, self.subnet_mask = addr_parts[5].split(':')

         # Now our default gateway
         out = _execute(['/sbin/ip', 'route', 'show'])
         lines = [line.strip() for line in out.split('\n')]

         for line in lines:
            if 'default' in line:
               # This line contains the IP address in the third field
               _, _, self.gateway, _ = line.split(' ', 3)
               break


      # DNS detection
      #try:
      for line in file('/etc/resolv.conf', 'r'):
         line = line.strip()

         if line.startswith('nameserver'):
            _, self.dns = line.split(' ', 1)
            if ' ' in self.dns:
               self.dns, _ = self.dns.split(' ', 1)
            break
      try:
         self.update_eth_file()
      except:
         log_error('Something went wrong while updating the eth0 file after DHCP: {}'.format(traceback.format_exc()))
      return errors
      #except ValueError:
      #   log_info('DNS detection failed; threw ValueError.')
      #   self.dns = '0.0.0.0'

   def parse (self):
      for line in file(self.filename, 'r'):
         line = line.strip()
         words = line.split(' ')

         # Nothing to do?
         if len(words) < 1: continue

         # Replace all quotes with nothing
         words = [word.strip().replace('"', '') for word in words]

         # Is this an 'auto' directive?
         if words[0] == 'auto':
            self.used = True
            self.name = words[1]
            continue

         # Is this an interface configuration directive?
         if words[0] == 'iface':
            if len(self.name) > 0 and words[1] != self.name:
               # This does not match us
               continue

            # We don't yet have a name; save this as our name
            self.name = words[1]

            if words[2] != 'inet':
               # This is not an IPv4 configuration
               continue

            if words[3] == 'static':
               # This is a statically configured interface
               self.use_dhcp = False
               continue

            elif words[3] == 'dhcp':
               # This interface uses DHCP
               self.use_dhcp = True
               continue

         # Is this a directive for a specific property?
         if words[0] == 'address':
            self.ip_address = words[1]

         elif words[0] == 'netmask':
            self.subnet_mask = words[1]

         elif words[0] == 'gateway':
            self.gateway = words[1]

         elif words[0] == 'dns-nameservers':
            self.dns = words[1]

      # Try to parse the DHCP configuration?
      if self.use_dhcp:
         return self.parse_dhcp()
      else:
         # Figure out DNS
         with open('/etc/resolv.conf', 'r') as fh:
            for line in fh:
               if line.startswith('nameserver'):
                  dns = line.split(' ')[1].strip()
                  break

         if dns is not None:
            self.dns = dns
         return False

class Network (Pollable):
   # Request types
   arm_to_avr = 1
   avr_to_arm = 2
   set_to_default = 3
   ping_test = 4

   def __init__ (self, remote, ipc):
      Pollable.__init__(self, **{
         'poll_interval': 1.0
      })

      self.remote = remote
      self.ipc = ipc

      self.dns_checks = 0
      self.failed_path = '/dev/shm/dhcp-lease-failed'
      try:
         self.prev_ethernet_status = bool(int(open('/sys/class/net/eth0/carrier', 'r').read()))
      except:
         self.prev_ethernet_status = True
         log_error('Something went wrong while initializing the ethernet status: {}'.format(traceback.format_exc()))

      ipc.add_handler('get_network', self.ipc_get_network)
      ipc.add_handler('set_network', self.ipc_set_network)

   def ipc_get_network (self, skt, data):
      '''Reply over the IPC interface with network information.'''
      iface = NetworkInterface(eth_file)
      if iface.parse():
         iface.parse()


      skt.send({
         'reply_to': data['request_type'],
         'dhcp': iface.use_dhcp,
         'ip_address': iface.ip_address,
         'subnet_mask': iface.subnet_mask,
         'gateway': iface.gateway,
         'dns': iface.dns,
         'hostname': socket.gethostname()
      })

   def ipc_set_network (self, skt, data):
      '''Accept a network configuration over the IPC interface.'''
      req_fields = ['dhcp', 'ip_address', 'subnet_mask', 'gateway', 'dns']
      for f in req_fields:
         if f not in data:
            skt.error('Set network request missing {} field.'.format(f))
            return

      # Looks like everything is there. Send success, and then change the configuration.
      reply = {
         'reply_to': data['request_type'],
      }
      reply.update(data)
      skt.send(reply)

      self.set(data)

   def set (self, config):
      '''Set the network configuration from 'config', a dict of values.'''

      mode = config['dhcp']
      ip = config['ip_address']
      subnet = config['subnet_mask']
      gateway = config['gateway']
      dns = config['dns']
      hostname = socket.gethostname() if 'hostname' not in config else config['hostname']

      # Copy the network configuration to a backup, just in case
      nf = '/etc/network/interfaces'
      old = '/etc/network/interfaces.old'
      shutil.copyfile(nf, old)

      # Write the new interfaces file
      with open(nf, 'w') as f:
         f.write('auto lo\n')
         f.write('iface lo inet loopback\n')
         f.write('auto eth0\n')
         if mode:
            f.write('iface eth0 inet dhcp\n')
         else:
            f.write('iface eth0 inet static\n')
         f.write('address {}\n'.format(ip))
         f.write('netmask {}\n'.format(subnet))
         f.write('gateway {}\n'.format(gateway))
         f.write('dns-nameservers {}\n'.format(dns))

      # DNS resolver file
      with open('/etc/resolv.conf', 'w') as f:
         f.write('nameserver {}'.format(dns))

      # Hostname file and direct set
      if hostname != socket.gethostname():
         with open('/etc/hostname', 'w') as f:
            f.write(hostname)
         os.system('hostname {}'.format(hostname))

      # Restart network to apply, it only takes a few seconds
      if os.path.exists(self.failed_path):
         os.system('rm '+self.failed_path)
      os.system('ifdown eth0')
      os.system('ifup eth0')
      # If UDHCPC fails, then this file is created
      if os.path.exists(self.failed_path):
         log_info('DHCP failed, changing back to old settings...')
         shutil.copyfile(old, nf)
         self.remote.set_param_value('Network Error Code', 2)
         return False

      # Log this
      log_info('Reconfiguring network:')
      if mode:
         log_info('Using DHCP.')
         iface = NetworkInterface(eth_file)
         if iface.parse():
            iface.parse()
         ip = iface.ip_address
         subnet = iface.subnet_mask
         gateway = iface.gateway
         dns = iface.dns
      else:
         log_info('Using static configuration.')      

      log_info('IP address is {}.'.format(ip))
      log_info('Subnet mask is {}.'.format(subnet))
      log_info('Default gateway is {}.'.format(gateway))
      log_info('DNS server is {}.'.format(dns))

      log_event('Network', 'Network configuration was changed.')
      return True

   def send_to_avr (self):
      iface = NetworkInterface(eth_file)
      if iface.parse():
         iface.parse()
         self.remote.set_param_value('Network Error Code', 2)
      self.remote.set_param_value('DHCP', 1 if iface.use_dhcp else 0)
      self.remote.set_param_value('IP Address', iface.ip_address)
      self.remote.set_param_value('Subnet Mask', iface.subnet_mask)
      self.remote.set_param_value('Default Gateway', iface.gateway)
      self.remote.set_param_value('DNS Server', iface.dns)

      # Tell the AVR that we've completed the request
      self.remote.set_param_value('Network Operation', 0)

   def receive_from_avr (self):
      '''Receive the network configuration from the AVR CPU.'''
      config = {
         'dhcp': True if self.remote.get_param_value('DHCP') else False,
         'ip_address': self.remote.get_param_value('IP Address'),
         'subnet_mask': self.remote.get_param_value('Subnet Mask'),
         'gateway': self.remote.get_param_value('Default Gateway'),
         'dns': self.remote.get_param_value('DNS Server')
      }

      # Apply the settings
      if (self.set(config)):
         # Tell the AVR that we've completed the request
         self.remote.set_param_value('Network Operation', 0)

   def reset_to_default (self):
      '''Receive the network configuration from the AVR CPU.'''
      if os.path.exists(self.failed_path):
         os.system('rm '+self.failed_path)
      default_config = {
         'dhcp': False,
         'ip_address': '192.168.1.8',
         'subnet_mask': '255.255.255.0',
         'gateway': '192.168.1.1',
         'dns': '8.8.8.8'
      }

      # Apply the settings
      self.set(default_config)
      # Tell the AVR that we've completed the request
      self.remote.set_param_value('Network Operation', 0)

   def check_ethernet_status (self):
      try:
         curr_ethernet_status = bool(int(open('/sys/class/net/eth0/carrier', 'r').read()))
         if self.prev_ethernet_status < curr_ethernet_status:
            if os.path.exists(self.failed_path):
               os.system('rm '+self.failed_path)
            os.system('ifdown eth0')
            os.system('ifup eth0')
            # If UDHCPC fails, then this file is created
            if os.path.exists(self.failed_path):
               log_info('DHCP failed, using default network parameters...')
               self.reset_to_default()
            log_info('Ethernet has been plugged in, network rebooted')
         self.prev_ethernet_status = curr_ethernet_status
      except:
         self.prev_ethernet_status = True
         log_error('Something went wrong while checking the ethernet status: {}'.format(traceback.format_exc()))

   def run_ping_test (self):
      ip = self.remote.get_param_value('Ping IP Address', 0)
      total_transmitted = 0
      total_received = 0
      self.remote.pause()
      self.remote.set_param_value('Display Command', 0)
      self.remote.set_param_value('Display Data', '\n\r')
      #self.remote.set_param_value('Display Data', 'Pinging: '+ip+'\n\r')
      for i in range (3):
         response = os.system('ping -W 3 -c 1 {} > /dev/shm/ping-result'.format(ip))
         with open('/dev/shm/ping-result', 'r') as f:
            data = f.readlines()
            for line in data:
               if 'transmitted' in line:
                  numbers = [int(s) for s in line.split() if s.isdigit()]
                  total_transmitted += numbers[0]
                  total_received += numbers[1]
                  data_string = str(total_transmitted)+' transmitted '+str(total_received)+' received'
                  self.remote.set_param_value('Display Data', data_string)
                  break
      
      percent_loss = str(round(float(total_transmitted-total_received)/float(total_transmitted),2)*100)
      self.remote.set_param_value('Display Data', percent_loss+'% Packet Loss')
      self.remote.play()
      self.remote.set_param_value('Network Operation', 0)

         
   def action (self):
      '''Periodically check the network requests on the AVR and respond accordingly.'''

      request = self.remote.get_param_value('Network Operation', 0)

      if request == Network.avr_to_arm:
         # Set the network configuration from the AVR.
         log_info('Receiving network configuration from AVR.')
         self.receive_from_avr()
      elif request == Network.arm_to_avr:
         # Get the network configuration.
         log_info('Sending network configuration to AVR.')
         self.send_to_avr()
      elif request == Network.set_to_default:
         # Reset the network configuration to its default.
         log_info('Resetting network configuration to default.')
         self.reset_to_default()
      elif request == Network.ping_test:
         try:
            self.run_ping_test()
         except:
            self.remote.play()
            log_error('Something went wrong while updating the eth0 file after DHCP: {}'.format(traceback.format_exc()))
      else:
         self.check_ethernet_status()

      # Also check to see if the DNS server is something weird.
      # Sometimes it gets set to 0.0.0.0, or gets removed entirely.
      if self.dns_checks == 30:
         dns = None
         try:
            with open('/etc/resolv.conf', 'r') as fh:
               for line in fh:
                  if line.startswith('nameserver'):
                     dns = line.split(' ')[1].strip()
                     break

            if dns is None or dns == '0.0.0.0':
               log_info('Network system noticed that DNS was not set. Using default.')

               with open('/etc/resolv.conf', 'w') as fh:
                  fh.write('nameserver 8.8.8.8')
         except (IOError, OSError, ValueError, IndexError):
            # Something went wrong
            log_error('Network system was not able to check DNS.')

         self.dns_checks = 0
      else:
         self.dns_checks += 1

