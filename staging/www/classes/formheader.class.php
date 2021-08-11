<?php

class FormHeader extends FormElement {
   protected $tag = 'div';
   protected $attributes = ['class' => 'form-header'];

   public function __construct ($text) {
      $this->text = $text;
   }
}

?>

