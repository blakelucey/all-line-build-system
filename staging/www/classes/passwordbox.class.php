<?php

class PasswordBox extends FormElement {
   protected $tag = 'input';
   protected $attributes = ['type' => 'password', 'class' => 'text'];
   protected $text = '';
   protected $auto_close = true;

   public function __construct ($id, $name = false, $size = false, $maxlength = 120) {
      $this->set_attribute('id', $id);
      $this->set_attribute('name', $name === false ? $id : $name);
      $this->set_attribute('maxlength', $maxlength);

      if ($size !== false) $this->set_attribute('size', $size);
   }

   public function has_help () {
      $this->append_attribute('class', 'has-help');
      return $this;
   }
}

?>
