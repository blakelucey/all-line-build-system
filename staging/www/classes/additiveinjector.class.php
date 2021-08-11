<?php

class Parameter {
   public $name;
   public $value;
   public $minimum;
   public $maximum;
   public $precision;
   public $type;
   public $type_string;
   public $flags;
   public $description;

   private $injector;
   private $valid = false;

   const pf_string_in_rom = 0x01;
   const pf_const = 0x08;

   public function __construct ($name, $ai) {
      $this->name = $name;
      $this->injector = $ai;

      $this->query();
   }

   public function is_read_only () {
      if ($this->flags & self::pf_string_in_rom) return true;
      if ($this->flags & self::pf_const) return true;
      return false;
   }

   public function get ($index = 0, $def = '', $format = false) {
      $result = $this->injector->ipc->request([
         'request_type' => 'get_param',
         'param_name' => $this->name,
         'index' => $index
      ]);

      if (!$result) return $def;
      if ($result['error'] == true) return $def;

      if ($format && $this->type_string === 'float') {
         # Format this to the requested precision
         return number_format($result['param_value'], $this->precision, '.', '');
      }

      return $result['param_value'];
   }

   public function query () {
      $result = $this->injector->ipc->request([
         'request_type' => 'query_param',
         'param_name' => $this->name
      ]);

      if (!$result) return;
      if ($result['error'] == true) return;

      $this->valid = true;

      $this->value = $result['param_value'];
      $this->minimum = $result['minimum_value'];
      $this->maximum = $result['maximum_value'];
      $this->precision = $result['precision'];
      $this->type = $result['type'];
      $this->type_string = $result['type_string'];
      $this->flags = $result['flags'];
      $this->description = $result['description'];
   }

   public function set ($value, $index = 0) {
      $result = $this->injector->ipc->request([
         'request_type' => 'set_param',
         'param_name' => $this->name,
         'index' => $index,
         'param_value' => $value
      ]);

      if (!$result) return false;
      if ($result['error'] == true) return false;

      return true;
   }

   public function validate_value ($value) {
      switch ($this->type_string) {
      case 'int':
         if (filter_var($value, FILTER_VALIDATE_INT) === false) return false;
         $value = (int)$value;
         return ($value >= $this->minimum && $value <= $this->maximum);
      case 'float':
         if (filter_var($value, FILTER_VALIDATE_FLOAT) === false) return false;
         $value = (float)$value;
         $min = (float)number_format($this->minimum, $this->precision, '.', '');
         $max = (float)number_format($this->maximum, $this->precision, '.', '');
         return ($value >= $min && $value <= $max);
      case 'string':
         if ($this->minimum > 0 && strlen($value) > $this->minimum) return false;
         if ($this->maximum > 0 && strlen($value) > $this->maximum) return false;
         return true;
      case 'bytes':
         # Bytes are not yet validated against anything.
         return false;
      }

      # Doesn't match any types; can't validate it.
      return false;
   }

   public function error_text () {
      # Return stock error text.
      switch ($this->type_string) {
      case 'int':
         return 'Valid range is ' . $this->minimum . '-' . $this->maximum;
      case 'float':
         $min = (float)number_format($this->minimum, $this->precision, '.', '');
         $max = (float)number_format($this->maximum, $this->precision, '.', '');
         return 'Valid range is ' . $min . '-' . $max;
      case 'string':
         if ($this->minimum > 0) return 'Maximum length is ' . $this->minimum;
         if ($this->maximum > 0) return 'Maximum length is ' . $this->maximum;
         return '';
      }

      return '';
   }

   public function is_valid () {
      # Was the parameter able to populate its data?
      return $this->valid;
   }
}

class AdditiveInjector {
   public $ipc;

   private $params = [];

   public function __construct ($ipc, $auto_pop = false) {
      $this->ipc = $ipc;
      if ($auto_pop) $this->collect();
   }

   public function get_all_names () {
      return array_keys($this->params);
   }

   public function collect () {
      $result = $this->ipc->request([
         'request_type' => 'list_params'
      ]);

      foreach ($result['names'] as $name) {
         $this->params[$name] = new Parameter($name, $this);
      }
   }

   public function get ($name) {
      if (!isset($this->params[$name])) {
         $param = new Parameter($name, $this);
         if (!$param->is_valid()) return false;

         $this->params[$name] = $param;
      }

      return $this->params[$name];
   }

   public function save_params () {
      $this->ipc->request([
         'request_type' => 'save_params'
      ]);
   }

   public function get_param_value ($name, $index = 0, $def = '', $format = false) {
      if (!isset($this->params[$name])) {
         $param = new Parameter($name, $this);
         if (!$param->is_valid()) return $def;

         $this->params[$name] = $param;
      }

      return $this->params[$name]->get($index, $def, $format);
   }

   public function get_formatted_param_value ($name, $index = 0, $def = '') {
      return $this->get_param_value($name, $index, $def, true);
   }

   public function set_param_value ($name, $value, $index = 0) {
      if (!isset($this->params[$name])) {
         $param = new Parameter($name, $this);
         if (!$param->is_valid()) return false;

         $this->params[$name] = $param;
      }

      return $this->params[$name]->set($value, $index);
   }

   public function get_date_and_time () {
      $iso = $this->get_param_value('Clock');

      return new DateTime($iso);
   }
}

?>
