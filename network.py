import os
import sys

def set_network (root_path, network, conf_path = None):
   # Write a network configuration file.

   text = ('auto lo\n'
      'iface lo inet loopback\n'
      'auto eth0\n')

   if network.get('dhcp', False):
      text += ('iface eth0 inet dhcp\n')
   else:
      text += ('iface eth0 inet static\n'
         f'address {network["address"]}\n'
         f'netmask {network["netmask"]}\n'
         f'gateway {network["gateway"]}\n')

   if conf_path is None:
      out = os.path.join(root_path, 'etc', 'network', 'interfaces')
   else:
      out = os.path.join(conf_path, 'network')

   with open(out, 'w') as f:
      f.write(text)

   # Now the DNS.
   if conf_path is None:
      out = os.path.join(root_path, 'etc', 'resolv.conf')
   else:
      out = os.path.join(conf_path, 'dns')

   with open(out, 'w') as f:
      f.write(f'nameserver {network["dns"]}')

