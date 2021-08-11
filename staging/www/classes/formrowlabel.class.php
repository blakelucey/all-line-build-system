<?php

class FormRowLabel extends FormElement {
   protected $tag = 'div';
   protected $attributes = ['class' => 'label'];
   protected $auto_escape = false;

   public function __construct ($label, $label_size = '10em') {
      $this->text = $label;
      $this->set_attribute('style', 'width: ' . $label_size);
   }
}

?>
