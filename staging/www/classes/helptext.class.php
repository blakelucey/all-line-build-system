<?php

class HelpText extends HtmlElement {
   protected $tag = 'div';
   protected $auto_escape = false;
   protected $auto_span = true;

   public function __construct ($text, $override_tag = 'div', $class = 'arrow_box', $style = '') {
      $this->text = $text;
      $this->tag = $override_tag;

      if (strlen($class) > 0) {
         $this->set_attribute('class', $class);
         $this->add_style('display', 'none');
      }
   }
}

?>
