<?php

# Interprocess-based configuration data.
# Implements loading and saving via the IPC interface to the backend.

class IpcConfig implements ArrayAccess, Countable {
   private $ipc = null;
   private $description = 'unknown';

   public $key = null;

   public $config = [];
   public $defaults = [];
   public $limits = [];

   # These are available after validate() is called.
   # Each key contains a message about why the corresponding value is not valid.
   public $invalid;

   public function __construct ($ipc, $key, $auto_load = true) {
      $this->ipc = $ipc;
      $this->key = $key;

      if ($auto_load) $this->load();
   }

   public function load () {
      $result = $this->ipc->request([
         'request_type' => 'get_' . $this->key . '_config',
      ]);

      $this->config = $result['config'];
      $this->defaults = $result['defaults'];
      $this->limits = $result['limits'];
      $this->description = $result['description'];
   }

   public function save () {
      $result = $this->ipc->request([
         'request_type' => 'save_' . $this->key . '_config',
         'config' => $this->config
      ]);

      return $result;
   }

   public function validate () {
      $result = $this->ipc->request([
         'request_type' => 'validate_' . $this->key . '_config',
         'config' => $this->config
      ]);

      $this->invalid = $result['invalid'];

      return $result['errors'] === 0;
   }

   public function get_defaults () {
      return $this->defaults;
   }

   public function get_limits () {
      return $this->limits;
   }

   public function get_description () {
      return $this->description;
   }

   public function count () {
      return count($this->config);
   }

   public function offsetExists ($offset) {
      return isset($this->config[$offset]);
   }

   public function &offsetGet ($offset) {
      return $this->config[$offset] ?? null;
   }

   public function offsetSet ($offset, $value) {
      $this->config[$offset] = $value;
   }

   public function offsetUnset ($offset) {
      unset($this->config[$offset]);
   }
}

?>
