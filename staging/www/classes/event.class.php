<?php

class Event {
   const log = 0;
   const alarm = 1;

   public $date_time;
   public $type;
   public $event_text;

   public static function get_event_log_path () {
      return '/opt/freeze-defender/logs/event.log';
   }

   public static function get_events ($limit = 20) {
      $lines = @file(self::get_event_log_path());
      if ($lines === false || count($lines) === 0) return [];

      $result = [];

      # The log format is 'date,time,type,event text'
      $start = count($lines) - 1;
      $end = count($lines) - 1 - $limit;
      if ($end < 0) $end = 0;

      for ($index = $start; $index >= $end; $index--) {
         $line = trim($lines[$index]);
         if (empty($line)) continue;
         list($date, $time, $type, $text) = explode(',', $line, 4);

         $event = new Event();
         $event->date_time = new DateTime($date . ' ' . $time);
         $event->type = (($type == 'alarm') ? self::alarm : self::log);
         $event->event_text = $text;

         $result[] = $event;
      }

      return $result;
   }

   public function get_html_type () {
      return (($this->type == self::alarm) ? '<span class="error"><strong>Alarm</strong></span>' : 'Event');
   }
}

?>
