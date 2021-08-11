import os
import sys

def set_network (root_path, network):
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

   out = os.path.join(root_path, 'etc', 'network', 'interfaces')

   with open(out, 'w') as f:
      f.write(text)

   # Now the DNS.
   out = os.path.join(root_path, 'etc', 'resolv.conf')

   with open(out, 'w') as f:
      f.write(f'nameserver {network["dns"]}')

