<?php

class FormRow extends FormElement {
   protected $tag = 'div';
   protected $attributes = ['class' => 'form-row'];
   protected $error_state = false;

   public function __construct ($label, $elements, $label_size = '10em', $error_info = '') {
      $this->add_child(new FormRowLabel($label, $label_size !== false ? $label_size : '10em'));

      if (!empty($error_info)) {
         # Stick on an error label
         if (!is_array($elements)) {
            $elements = [$elements];
         }
         $elements[] = new ErrorText($error_info);
      }

      $this->add_child(new FormRowContainer($elements));
      $this->set_error_state(!empty($error_info));
   }
}

?>
