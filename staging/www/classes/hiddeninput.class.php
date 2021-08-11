<?php

class HiddenInput extends HtmlElement {
   protected $tag = 'input';
   protected $attributes = ['type' => 'hidden'];

   public function __construct ($id, $name, $value) {
      $this->set_attribute('id', $id);
      $this->set_attribute('name', $name === false ? $id : $name);
      $this->set_attribute('value', $value);
   }
}

?>
