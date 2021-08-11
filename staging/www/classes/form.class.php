<?php

class Form extends FormElement {
   protected $tag = 'form';
   protected $attributes = ['action' => '', 'method' => ''];
   protected $auto_close = false;

   public function __construct ($action, $method = 'post', $enctype = '') {
      $this->set_attribute('action', $action);
      $this->set_attribute('method', $method);

      if (strlen($enctype) > 0) {
         $this->set_attribute('enctype', $enctype);
      }
   }
}

?>
