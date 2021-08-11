<?php

class TimeBox extends TextBox {
   protected $attributes = ['type' => 'time', 'class' => 'time'];
   const value_now = 0;

   public function __construct ($id, $name = false, $value = self::value_now) {
      if ($value === self::value_now) {
         $value = date('H:i');
      }

      parent::__construct($id, $name, $value, 5, 5);

      $this->set_attribute('placeholder', 'HH:MM');
   }

   public static function validate ($text) {
      $parts = explode(':', $text);
      if (count($parts) !== 2) return false;
      list($hour, $minute) = $parts;

      $tm = DateTime::createFromFormat('H:i', $hour . ':' . $minute);
      if ($tm === false) return false;

      return true;
   }

   public static function to_datetime ($text) {
      if (substr_count($text, ':') == 2) {
         $tm = DateTime::createFromFormat('H:i:s', $text);
      }
      else {
         $tm = DateTime::createFromFormat('H:i', $text);
      }
      return $tm;
   }
}

?>

