<?php

class SelectOptionGroup extends FormElement {
   protected $tag = 'optgroup';

   public function __construct ($text = '- - - - -') {
      $this->set_attribute('label', $text);
   }
}

class SelectBox extends FormElement {
   protected $tag = 'select';
   protected $items = [];
   protected $value = null;

   public function get_value () {
      return $this->value;
   }

   public function __construct ($id, $name = false, $items = [], $value = false) {
      $this->set_attribute('id', $id);
      $this->set_attribute('name', $name === false ? $id : $name);

      #foreach ($items as $v => $t) {
      #   $this->add_child(new SelectOption($v, $t));
      #}

      foreach ($items as $v => $t) {
         if (is_array($t)) {
            # This is an option group.
            $group = new SelectOptionGroup($v);
            foreach ($t as $sub_v => $sub_t) {
               $group->add_child(new SelectOption($sub_v, $sub_t));
            }
            $this->add_child($group);
         }
         else {
            $this->add_child(new SelectOption($v, $t));
         }
      }

      if ($value !== false) {
         # This is handled by our child <option> elements
         $this->value = $value;
      }
   }

   public function add_item ($key, $value) {
      $this->add_child(new SelectOption($key, $value));
   }
}

?>
