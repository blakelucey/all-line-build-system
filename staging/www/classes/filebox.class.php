<?php

class FileBox extends FormElement {
   protected $tag = 'input';
   protected $attributes = ['type' => 'file', 'class' => 'file'];
   protected $auto_close = true;

   public function __construct ($id, $name = false) {
      $this->set_attribute('id', $id);
      $this->set_attribute('name', ($name !== false) ? $name : $id);
   }
}

?>
