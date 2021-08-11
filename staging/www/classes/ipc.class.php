<?php

class IpcException extends Exception {
}

class Ipc {
   const host = 'localhost';
   const port = 3737;

   private $socket;

   # $force is used to make a connection to the IPC server, even if the server
   # is busy processing a firmware update.
   public function __construct ($force = false) {
      $this->socket = socket_create(AF_INET, SOCK_STREAM, SOL_TCP);

      if (!@socket_connect($this->socket, self::host, self::port)) {
         ErrorPage::show(
            'Could not connect to internal service. ' .
            'The system may be rebooting, or not fully booted yet. ' .
            'If the problem persists, please contact support.'
         );
      }

      @socket_set_option($this->socket, SOL_TCP, TCP_NODELAY, 1);
      @socket_set_nonblock($this->socket);

      # Check to see if the system is busy processing a long request, such as
      # a firmware update. If so, we can't continue any further.
      if (!$force) {
         $result = $this->request([
            'request_type' => 'firmware_update_status'
         ]);

         if ($result['is_updating']) {
            ErrorPage::show(
               'The system firmware is currently being upgraded. Please try again in a minute.'
            );
         }
      }
   }

   public function __destruct () {
      socket_close($this->socket);
   }

   public function raw_request ($text) {
      socket_write($this->socket, $text);

      # There is always a response from the server, terminated by <cr><lf>
      $return = '';
      $now = microtime(true);
      do {
         $result = @socket_read($this->socket, 1, PHP_NORMAL_READ);
         if ($result === false) {
            return false;
         }

         if (microtime(true) - $now > 5.0) {
            # Timeout
            return false;
         }

         $return .= $result;
      } while (substr($return, -2) !== "\r\n");

      return trim($return);
   }

   public function request ($request, $auto_decode = true) {
      # Only PHP objects can be sent; they're JSON-encoded first.
      if (!($request instanceof object) && !is_array($request)) return false;

      $request = preg_replace('/\r|\n|\r\n/', '', json_encode($request));
      $result = $this->raw_request($request);

      # Second parameter is 'true' to decode to an associative array.
      # 'false' would decode to a native PHP object.
      if ($auto_decode) return json_decode($result, true);

      return $result;
   }
}

?>
