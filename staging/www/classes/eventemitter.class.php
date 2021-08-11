<?php

class EventEmitter {
   const end_line = "\n";
   const end_message = "\n\n";

   public function __construct () {
      @ini_set('zlib.output_compression', 'Off');
      @ini_set('output_buffering', 'Off');
      @ini_set('output_handler', '');
      ignore_user_abort(false);

      header('Content-Type: text/event-stream; charset=utf-8');
   }

   public function emit ($message) {
      echo 'data: ' . $message . self::end_message;
      flush();
      ob_flush();
   }

   public function wait ($milliseconds) {
      usleep(1000 * $milliseconds);
   }
}

?>
