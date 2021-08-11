<?php

class PlainText extends HtmlElement {
   protected $tag = 'span';
   protected $auto_escape = false;
   protected $auto_span = true;

   public function __construct ($text, $override_tag = 'span', $class = '', $style = '') {
      $this->text = $text;
      $this->tag = $override_tag;

      if (strlen($class) > 0) {
         $this->set_attribute('class', $class);
      }
   }
}

?>
