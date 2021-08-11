<?php

class ErrorText extends FormElement {
   protected $tag = 'div';
   protected $auto_escape = false;
   protected $attributes = ['class' => 'arrow_box form-error'];

   public function __construct ($text) {
      $this->text = $text;
   }
}

?>

