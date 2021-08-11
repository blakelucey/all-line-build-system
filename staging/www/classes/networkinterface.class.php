<?php

class NetworkInterface {
   public $used = false;
   public $name = 'eth0';
   public $use_dhcp = true;
   public $ip_address = '0.0.0.0';
   public $subnet_mask = '255.255.255.255';
   public $dns_server = '0.0.0.0';
   public $default_gateway = '0.0.0.0';
   public $host_name = false;

   public static function get_config_path () {
      return '/opt/freeze-defender/config/ethernet.txt';
   }

   public static function restart_network () {
      exec('sudo /opt/freeze-defender/program/network-restart.sh > /dev/null &');
   }

   public static function write_default_config () {
      $handle = @fopen($this->get_config_path(), 'w+');
      if ($handle === false) return;

      flock($handle, LOCK_EX);
      fputs($handle, 'auto eth0' . PHP_EOL);
      fputs($handle, 'iface eth0 inet dhcp' . PHP_EOL);
      flock($handle, LOCK_UN);
      fclose($handle);
   }

   public function __construct ($name = 'eth0') {
      $this->name = $name;
   }

   public function write ($file = 'php://stdout') {
      $handle = @fopen($file, 'w+');
      if ($handle === false) return;

      flock($handle, LOCK_EX);

      fputs($handle, 'auto ' . $this->name . PHP_EOL);

      fputs($handle, 'iface ' . $this->name . ' inet');
      if ($this->use_dhcp) {
         fputs($handle, ' dhcp' . PHP_EOL);
      } else {
         fputs($handle, ' static' . PHP_EOL);
         fputs($handle, "\taddress {$this->ip_address}" . PHP_EOL);
         fputs($handle, "\tnetmask {$this->subnet_mask}" . PHP_EOL);
         fputs($handle, "\tgateway {$this->default_gateway}" . PHP_EOL);
         fputs($handle, "\tdns-nameservers {$this->dns_server}" . PHP_EOL);
      }

      fputs($handle, PHP_EOL);
      flock($handle, LOCK_UN);
      fclose($handle);

      # Now we need to write the hostname to /etc/hostname AND to /etc/hosts at the
      # appropriate place. That means we'll need to scan the file.
      # Since www-data and any regular user can't do this, we will write these to
      # a temporary location, and let the network-restart script do the rest.
      if ($this->host_name !== false) {
         $old_host_name = gethostname();
         $new_host_name_file = '/opt/freeze-defender/config/new-hostname.txt';
         $new_hosts_file = '/opt/freeze-defender/config/new-hosts.txt';

         $handle = @fopen($new_host_name_file, 'w+');
         if ($handle === false) return 'unable to open ' . $new_host_name_file;
         flock($handle, LOCK_EX);
         fputs($handle, $this->host_name);
         flock($handle, LOCK_UN);
         fclose($handle);

         # Read from the actual hosts file
         $lines = @file('/etc/hosts');
         if ($lines === false || count($lines) === 0) {
            return;
         }

         $handle = @fopen($new_hosts_file, 'w+');
         if ($handle === false) return 'unable to open ' . $new_hosts_file;
         flock($handle, LOCK_EX);

         foreach ($lines as $line) {
            # Replace instances of our old host name with our new one
            $new_line = str_replace($old_host_name, $this->host_name, $line);
            fputs($handle, $new_line);
         }

         flock($handle, LOCK_UN);
         fclose($handle);
      }

      return true;
   }

   private function parse_ifconfig ($name) {
      exec('/sbin/ifconfig ' . $name, $text, $result);

      if (count($text) < 2) return;

      $line = trim($text[1]);
      $params = explode(' ', $line);

      list($ignore, $this->ip_address) = explode(':', $params[1]);
      list($ignore, $this->subnet_mask) = explode(':', $params[5]);

      ## Default gateway ##

      unset($text);
      exec('/sbin/ip route show', $text);

      if (count($text) < 1) return;

      foreach ($text as $line) {
         $line = trim($line);
         if (strpos($line, 'default') !== false) {
            # IP is 3rd field
            list($ignore, $ignore2, $this->default_gateway) = explode(' ', $line, 4);
            break;
         }
      }

      ## DNS ##

      unset($text);
      $text = @file('/etc/resolv.conf');

      foreach ($text as $line) {
         $line = trim($line);
         if (substr($line, 0, 10) === 'nameserver') {
            list($ignore, $this->dns_server) = explode(' ', $line, 2);
            break;
         }
      }
   }

   # This will fill in any unknowns (if DHCP is used) from ifconfig and friends
   private function read_dhcp () {
      $this->parse_ifconfig('eth0');
   }

   public function read ($file) {
      $text = @file($file);

      if ($text === false || count($text) === 0) return;

      # Clear
      $this->used = false;
      $this->name = '';
      $this->use_dhcp = false;
      $this->ip_address = '0.0.0.0';
      $this->subnet_mask = '255.255.255.255';
      $this->default_gateway = '0.0.0.0';
      $this->dns_server = '0.0.0.0';

      # Get our hostname
      $this->host_name = gethostname();

      # Parse the interface file
      foreach ($text as $line) {
         $line = trim($line);
         preg_match_all('/"(?:\\\\.|[^\\\\"])*"|\S+/', $line, $words);
         $words = array_values($words[0]);

         # Nothing to parse?
         if (count($words) < 1) continue;

         # Replace all quotes with nothing
         foreach ($words as &$word) {
            $word = str_replace('"', '', $word);
         }

         # Is this an 'auto' directive?
         if ($words[0] === 'auto') {
            $this->used = true;
            $this->name = $words[1];
            continue;
         }

         # Is this an interface configuration directive?
         if ($words[0] === 'iface') {
            if (!empty($this->name) && $words[1] !== $this->name) {
               # This doesn't match us...
               continue;
            }

            # Save our name; we don't have one yet
            $this->name = $words[1];

            if ($words[2] !== 'inet') {
               # This isn't an IPv4 configuration...
               continue;
            }

            if ($words[3] === 'static') {
               # This is statically configured.
               $this->use_dhcp = false;
               continue;
            } else if ($words[3] === 'dhcp') {
               # This uses DHCP to be configured.
               $this->use_dhcp = true;
               continue;
            }

            continue;
         }

         # Is this a directive for a specific property?
         if ($words[0] === 'address') {
            $this->ip_address = $words[1];
            continue;
         }

         if ($words[0] === 'netmask') {
            $this->subnet_mask = $words[1];
            continue;
         }

         if ($words[0] === 'gateway') {
            $this->default_gateway = $words[1];
            continue;
         }

         if ($words[0] === 'dns-nameservers') {
            $this->dns_server = $words[1];
            continue;
         }
      }

      # Parse the DHCP configuration if possible
      if ($this->use_dhcp) {
         $this->read_dhcp();
      }
   }
}

?>
