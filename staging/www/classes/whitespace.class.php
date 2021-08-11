<?php

class WhiteSpace extends HtmlElement {
   protected $tag = 'span';
   protected $styles = ['display' => 'inline-block'];

   public function __construct ($width) {
      $this->add_style('width', $width);
   }
}

?>
