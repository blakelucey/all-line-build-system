<?php

class Device {
   public $file;
   public $name;
   public $directory;
   public $label;
   public $size;
   public $mounted = false;
   public $attributes = [];

   public function get_formatted_label ($append_size = false) {
      if (strlen($this->label) < 1) {
         return $this->get_formatted_size() . ' device';
      }

      $label = $this->label;
      if ($append_size) {
         $label .= ' (' . $this->get_formatted_size() . ' device' . ')';
      }

      return $label;
   }

   public function get_formatted_size () {
      # If the size ends with a unit, make it more readable.
      $text = $this->size;
      $unit = substr($this->size, -1, 1);
      if (in_array($unit, ['G', 'M', 'T'])) {
         $text = substr($text, 0, -1);
         $unit = ' ' . $unit . 'B';
         return $text . $unit;
      }

      return $text;
      # Old code:
      # return DeviceConfig::format_size($this->size);
   }
}

class DeviceConfig implements Iterator, ArrayAccess, Countable {
   public $devices = [];
   private $ptr = null;

   public function __construct () {
      $this->load();
      $this->rewind();
   }

   public function parse_device ($line) {
      if (strlen($line) < 5) return false;

      # Each line from lsblk is in 'key="value" ...' format
      # Separate it
      $parts = [];
      $pc = '';
      $inq = false;
      $pair = '';
      for ($i = 0; $i < strlen($line); $i++) {
         $c = $line[$i];

         if ($i == strlen($line) - 1) {
            $pair .= $c;
            $parts[] = $pair;
            break;
         }

         if ($inq) {
            if ($c == '"' && $pc != '\\') {
               $inq = false;
               $pc = $c;
               continue;
            }

            $pair .= $c;
            $pc = $c;
         } else {
            if ($c == '"' && $pc != '\\') {
               $pair .= $c;
               $inq = true;
               $pc = $c;
               continue;
            }

            if ($c == ' ') {
               # Split here
               $parts[] = $pair;
               $pair = '';
            }

            $pair .= $c;
            $pc = $c;
         }
      }

      # Convert into key/value pairs
      $info = [];
      foreach ($parts as $part) {
         list($key, $value) = explode('=', $part, 2);
         $info[strtolower(trim($key))] = trim($value, '"');
      }

      $dev = new Device();
      $dev->attributes = $info;
      $dev->name = $info['name'];
      $dev->file = '/dev/' . $info['name'];
      $dev->label = $info['label'];
      $dev->size = $info['size'];

      # Don't add mmc blocks or whole devices
      if (substr($dev->name, 0, 2) !== 'sd') {
         return false;
      }

      $part_id = (int)substr($dev->name, -1, 1);
      if ($part_id < 1 || $part_id > 9) {
         return false;
      }

      $dev->directory = $this->get_mouth_path($dev);

      return $dev;
   }

   public function parse_devices () {
      $result = `sudo lsblk -Pno name,size,type,mountpoint,label`;
      $devs = [];
      $lines = explode("\n", $result);

      foreach ($lines as $line) {
         $line = trim($line);
         $dev = $this->parse_device($line);
         if ($dev === false) continue;
         $devs[$dev->name] = $dev;
      }

      return $devs;
   }

   public function get_mouth_path ($dev) {
      return '/run/shm/device-' . $dev->name;
   }

   public function get_device_by_id ($id) {
      return $this->devices[$id];
   }

   public function load () {
      $devs = $this->parse_devices();
      $this->devices = $devs;
   }

   public function save () {
      # No operation
   }

   public function current () {
      return $this->devices[$this->ptr];
   }

   public function key () {
      return $this->ptr;
   }

   public function next () {
      next($this->devices);
      $this->ptr = key($this->devices);
   }

   public function rewind () {
      reset($this->devices);
      $this->ptr = key($this->devices);
   }

   public function valid () {
      return isset($this->devices[$this->ptr]);
   }

   public function offsetExists ($offset) {
      return isset($this->devices[$offset]);
   }

   public function offsetGet ($offset) {
      return $this->devices[$offset];
   }

   public function offsetSet ($offset, $value) {
      # Do nothing; it doesn't make sense to set a device here yet
   }

   public function offsetUnset ($offset) {
      # Again...
   }

   public function count () {
      return count($this->devices);
   }

   public static function format_size ($s, $p = 2) {
      $s = (int)$s;
      if ($s < 1024) return $s . ' kB';

      $base = log($s) / log(1024);
      $suf = array('kB', 'MB', 'GB', 'TB');

      return number_format(round(pow(1024, $base - floor($base)), $p), $p) . ' ' . $suf[floor($base)];
   }
}
