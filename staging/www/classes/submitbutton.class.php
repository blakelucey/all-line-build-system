<?php

class SubmitButton extends FormElement {
   protected $tag = 'input';
   protected $attributes = ['type' => 'submit', 'class' => 'button'];
   protected $auto_close = true;

   public function __construct ($id, $name = false, $value = 'Submit') {
      $this->set_attribute('id', $id);
      $this->set_attribute('name', $name === false ? $id : $name);
      $this->set_attribute('value', $value);
   }
}

?>
