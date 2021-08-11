<?php

class TextArea extends FormElement {
   protected $tag = 'textarea';

   public function __construct ($id, $name = false, $value = '', $rows = false, $cols = false) {
      $this->set_attribute('id', $id);
      $this->set_attribute('name', $name === false ? $id : $name);

      if ($rows !== false) $this->set_attribute('rows', $rows);
      if ($cols !== false) $this->set_attribute('cols', $cols);

      $this->text = $value;
   }
}
