<?php

class NetworkInterface {
   public $enabled;
   public $name;
   public $use_dhcp;
   public $ip_address;
   public $subnet_mask;
   public $default_gateway;
   public $dns_server;

   public static function from_xml ($xml) {
      $interface = new NetworkInterface();

      $interface->enabled = ((string)$xml['enabled'] == 'true') ? true : false;
      $interface->name = (string)$xml['name'];
      $interface->use_dhcp = ((string)$xml['use-dhcp'] == 'true') ? true : false;
      $interface->ip_address = (string)$xml->{'ip-address'};
      $interface->subnet_mask = (string)$xml->{'subnet-mask'};
      $interface->default_gateway = (string)$xml->{'default-gateway'};
      $interface->dns_server = (string)$xml->{'dns-server'};

      return $interface;
   }
}

class NetworkConfig {
   public $interfaces = [];
   public $host_name = '';

   public function __construct () {
      $this->load();
      $this->script = get_path('network') . 'network.py';
   }

   public static function get_xml_file () {
      return get_path('network') . 'ethernet.xml';
   }

   public static function execute_script ($args) {
      $command = 'python -B ' . $this->script . ' ' . $args;
      return `$command`;
   }

   public static function get_temp_file () {
      $dst = tempnam('/tmp', 'net-');
      chmod($dst, 0666);
      return $dst;
   }

   public function to_xml () {
      $src = get_path('network') . 'ethernet.txt';
      $dst = self::get_temp_file();

      self::execute_script("get $src $dst");

      return $dst;
   }

   public function from_xml ($src) {
      $dst = get_path('network') . 'ethernet.txt';
   }

   public function load () {
      # This is handled by an external program
      $filename = $this->to_xml();
      $xml = simplexml_load_file($filename);

      if ($xml === false) {
         return;
      }

      $this->host_name = (string)$xml->{'host-name'};

      foreach ($xml->interfaces->interface as $ixml) {
         $interface = NetworkInterface::from_xml($ixml);
         $this->interfaces[$interface->name] = $interface;
      }

      @unlink($filename);
   }

   public function save () {
      # Save our data to a temporary file, and then call upon
      # the network management script.
      $filename = self::get_temp_file();

      $xml = new SimpleXMLElement('<network></network>');
      $xml->addChild('host-name', $this->host_name);

      $interfaces = $xml->addChild('interfaces');

      foreach ($this->interfaces as $if) {
         $interface = $interfaces->addChild('interface');
         $interface->addAttribute('name', $if->name);
         $interface->addAttribute('use-dhcp', $if->use_dhcp === true ? 'true' : 'false');
         $interface->addAttribute('enabled', $if->enabled === true ? 'true' : 'false');

         $interface->addChild('ip-address', $if->ip_address);
         $interface->addChild('subnet-mask', $if->subnet_mask);
         $interface->addChild('default-gateway', $if->default_gateway);
         $interface->addChild('dns-server', $if->dns_server);
      }

      $handle = fopen($filename, 'w');
      fwrite($handle, $xml->asXML());
      fclose($handle);

      $this->from_xml($filename);
      sleep(1.5);
   }

   public function get_interface ($name) {
      return $this->interfaces[$name];
   }

   public static function get_external_ip () {
      $options = ['http' => [
         'user_agent' => 'Fuel-Boss',
         'max_redirects' => '5',
         'timeout' => '2.5'
      ]];

      $context = stream_context_create($options);

      $url = 'http://myexternalip.com/raw';
      $result = @file_get_contents($url, false, $context);

      if ($result === false) {
         return 'not able to be determined';
      }

      return trim($result);
   }
}
