<?php

class EventLogEntry {
   public $time;
   public $kind;
   public $text;
}

class EventLog implements Countable, Iterator {
   private $events = [];
   private $ptr;

   const event_file = '/config/events.cfg';

   public function __construct () {
      $data = file(self::event_file);
      if (!$data) {
         $entry = new EventLogEntry();
         $entry->time = new DateTime('now');
         $entry->kind = '-';
         $entry->text = 'The event log is empty.';
         $this->events = [0 => $entry];
         $this->ptr = 0;

         return;
      }

      foreach ($data as $index => $event) {
         $jsdata = json_decode($event, true);

         $entry = new EventLogEntry();
         $entry->time = DateTime::createFromFormat('Y-m-d?H:i:s', $jsdata['time']);
         $entry->kind = $jsdata['kind'];
         $entry->text = $jsdata['text'];

         $this->events[$index] = $entry;
      }

      $this->ptr = 0;
   }

   public function current () {
      return $this->events[$this->ptr];
   }

   public function key () {
      return $this->ptr;
   }

   public function next () {
      $this->ptr++;
   }

   public function rewind () {
      $this->ptr = 0;
   }

   public function valid () {
      return isset($this->events[$this->ptr]);
   }

   public function count () {
      return count($this->events);
   }
}

?>
