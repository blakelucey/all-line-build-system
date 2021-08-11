<?php

class CheckBox extends FormElement {
   protected $tag = 'input';
   protected $attributes = ['class' => 'checkbox', 'type' => 'checkbox'];
   protected $auto_close = true;

   public function __construct ($id, $name = false, $text, $checked = false, $value = '') {
      $this->set_attribute('id', $id);
      $this->set_attribute('name', $name === false ? $id : $name);
      $this->text = $text;

      if ($checked !== false) {
         # Checked being set at all should work OK
         $this->set_attribute('checked', true);
      }

      if (strlen($value) > 0) {
         $this->set_attribute('value', $value);
      }
   }

   public function get_html () {
      $text = parent::get_html();
      $text .= '<label for="' . $this->attributes['id'] . '">' . $this->text . '</label>';
      return $text;
   }
}

?>
