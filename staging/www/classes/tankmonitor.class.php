<?php

class TankMonitorConfig {
   public $enabled = false;
   public $host = '';
   public $port = 10001;
   public $tank_id = 0;
   public $low_level = 0;

   public static function get_config_file () {
      return get_path('config') . 'tank_monitor.cfg';
   }

   public function __construct ($auto_load = true) {
      if ($auto_load) $this->load();
   }

   public function load () {
      $filename = self::get_config_file();

      $config = @json_decode(@file_get_contents($filename), true);
      if (!$config) return;

      $this->enabled    = $config['enabled'] ?? false;
      $this->host       = $config['host'] ?? '';
      $this->port       = $config['port'] ?? 10001;
      $this->tank_id    = $config['tank_id'] ?? 0;
      $this->low_level  = $config['low_level'] ?? 0;
   }

   public function save ($ipc = null) {
      $filename = self::get_config_file();

      $config = [
         'enabled' => (bool)$this->enabled,
         'host' => (string)$this->host,
         'port' => (int)$this->port,
         'tank_id' => (int)$this->tank_id,
         'low_level' => (int)$this->low_level
      ];

      @file_put_contents($filename, json_encode($config, JSON_PRETTY_PRINT));

      if ($ipc) {
         $ipc->request([
            'request_type' => 'reload_tank_monitor'
         ]);
      }
   }
}

class TankMonitor {
   private $ipc = null;
   private $num_tanks = 0;
   private $tanks = [];
   private $collected = false;

   public function __construct ($ipc) {
      $this->ipc = $ipc;
   }

   public function can_connect () {
      $response = $this->ipc->request([
         'request_type' => 'can_connect_to_tank_monitor'
      ]);

      return $response['can_connect'];
   }

   public function get_recent_reading () {
      $response = $this->ipc->request([
         'request_type' => 'get_recent_tank_reading'
      ]);

      return $response['height'] ?? false;
   }

   public function collect () {
      if ($this->collected) return;

      $response = $this->ipc->request([
         'request_type' => 'get_tank_monitor_tanks'
      ]);

      if ($response['error']) {
         $this->num_tanks = 0;
         $this->tanks = [];
         $this->collected = true;
         return;
      }

      $this->tanks = $response['tanks'];
      $this->num_tanks = $response['num_tanks'];
   }

   public function get_num_tanks () {
      $this->collect();

      return $this->num_tanks;
   }

   public function get_tank_data () {
      $this->collect();

      return $this->tanks;
   }
}

