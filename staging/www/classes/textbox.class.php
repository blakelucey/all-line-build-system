<?php

class TextBox extends FormElement {
   protected $tag = 'input';
   protected $attributes = ['type' => 'text', 'class' => 'text'];
   protected $text = '';
   protected $auto_close = true;

   public function __construct ($id, $name = false, $value = '', $size = false, $maxlength = 120, $enabled = true) {
      $this->set_attribute('id', $id);
      $this->set_attribute('name', $name === false ? $id : $name);
      $this->set_attribute('value', $value);
      $this->set_attribute('maxlength', $maxlength);

      if ($size !== false) $this->set_attribute('size', $size);
      if ($enabled === false) $this->set_attribute('disabled', true);
   }

   public function has_help () {
      $this->append_attribute('class', 'has-help');
      return $this;
   }

   public function set_error_state ($state) {
      parent::set_error_state($state);
      if ($state) $this->append_attribute('class', 'form-error');
   }
}

?>
