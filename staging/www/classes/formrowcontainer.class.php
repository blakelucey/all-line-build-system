<?php

class FormRowContainer extends FormElement {
   protected $tag = 'div';
   protected $attributes = ['class' => 'container'];

   public function __construct ($children = []) {
      if (is_array($children)) {
         foreach ($children as $child) $this->add_child($child);
      } else {
         $this->add_child($children);
      }
   }
}
