<?php

class ConfigFile {
   private $data;
   private $filename;
   private $saved;

   public static function get_config_path () {
      return '/opt/freeze-defender/config/config.txt';
   }

   public static function get_smtp_config_path () {
      return '/opt/freeze-defender/config/smtp.txt';
   }

   public function __construct ($filename) {
      $this->filename = $filename;
      $this->data = [];
   }

   public function read () {
      if (!file_exists($this->filename)) {
         return false;
      }

      $lines = @file($this->filename);
      if ($lines === false || count($lines) === 0) {
         return false;
      }

      foreach ($lines as $idx => $line) {
         $line = trim($line);

         # Split along any colons
         list($key, $value) = explode(':', $line, 2);

         $this->data[$key] = $value;
      }

      $this->saved = false;

      return true;
   }

   public function write () {
      $fd = fopen($this->filename, 'w+');
      if (!$fd) return false;

      flock($fd, LOCK_EX);

      foreach ($this->data as $key => $value) {
         fputs($fd, $key . ':' . trim($value) . "\r\n");
      }

      flock($fd, LOCK_UN);
      fclose($fd);

      $this->saved = true;
   }

   public function get ($key, $default = '') {
      if (isset($this->data[$key])) {
         return $this->data[$key];
      }

      return $default;
   }

   public function get_html ($key, $default = '') {
      return htmlspecialchars($this->get($key, $default));
   }

   public function set ($key, $value) {
      $value = preg_replace('/\r|\n|\r\n/', '', $value);
      $this->data[$key] = $value;
   }

   public function is_modified () {
      return !$this->saved;
   }
}

?>
