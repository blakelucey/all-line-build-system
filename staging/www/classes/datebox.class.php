<?php

class DateBox extends TextBox {
   protected $attributes = ['type' => 'date', 'class' => 'date'];
   const no_date = null;
   const invalid_date = false;
   const value_today = 0;

   public function __construct ($id, $name = false, $value = self::value_today) {
      if ($value === self::value_today) {
         $value = date('Y-m-d');
      }

      parent::__construct($id, $name, $value, 10, 10);

      #$this->set_attribute('placeholder', 'MM/DD/YYYY');
      $this->add_style('float', 'left');
   }

   public static function validate ($text) {
      if (strpos($text, '-') !== false) {
         $parts = explode('-', $text);
         if (count($parts) !== 3) return false;
         if (strlen($parts[0]) !== 4) return false;
         if (!checkdate($parts[1], $parts[2], $parts[0])) return false;
         $dt = DateTime::createFromFormat('Y-m-d', $text);
         if ($dt === false) return false;
         return true;
      }
      else {
         $parts = explode('/', $text);
         if (count($parts) !== 3) return false;
         if (strlen($parts[2]) !== 4) return false;
         if (!checkdate($parts[0], $parts[1], $parts[2])) return false;
         $dt = DateTime::createFromFormat('m/d/Y', $text);
         if ($dt === false) return false;
         return true;
      }
   }

   public static function to_datetime ($text) {

      if (strpos($text, '-') !== false) {
         return DateTime::createFromFormat('Y-m-d', $text);
      }
      else{
         return DateTime::createFromFormat('m/d/Y', $text);
      }
   }
}

?>
