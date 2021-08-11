<?php

class NtpConfig {
   private $ipc;

   public $enabled = false;
   public $timezone = 'Unknown';

   const script_file = '/etc/init.d/S45ntpd';

   public function __construct ($ipc) {
      $this->ipc = $ipc;
      $this->enabled = is_executable(self::script_file);

      # Time zone
      $ok = false;
      $tz = realpath('/etc/TZ');
      if ($tz !== false) {
         $tz = explode('/', $tz);
         $zi = array_search('zoneinfo', $tz);
         if ($zi !== false) {
            # We parsed the timezone correctly
            $tz = implode('/', array_slice($tz, $zi + 2));
            $ok = true;
            date_default_timezone_set($tz);
         }
      }

      if (!$ok) {
         # Set things manually.
         $tz = 'America/Chicago';

         $ipc->request([
            'request_type' => 'set_timezone',
            'timezone' => 'America/Chicago'
         ]);
      }

      $this->timezone = $tz;
   }

   public function set_timezone ($tz) {
      $ipc->request([
         'request_type' => 'set_timezone',
         'timezone' => $tz
      ]);
   }
}

?>
