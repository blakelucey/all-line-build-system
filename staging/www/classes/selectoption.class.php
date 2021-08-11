<?php

class SelectOption extends FormElement {
   protected $tag = 'option';

   public function __construct ($value, $text) {
      $this->set_attribute('value', $value);
      $this->text = $text;
   }

   public function get_html () {
      # Back up to the SelectBox parent, if one.
      $parent = $this->parent;
      while ($parent !== null && !is_a($parent, 'SelectBox')) {
         $parent = $parent->parent;
      }

      # Valid parent?
      if ($parent) {
         if ($parent->get_value() == $this->attributes['value']) {
            $this->set_attribute('selected', true);
         } else {
            $this->delete_attribute('selected');
         }
      }

      return parent::get_html();
   }
}

?>
