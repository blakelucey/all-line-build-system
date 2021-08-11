<?php

class ImageElement extends HtmlElement {
   protected $tag = 'img';
   protected $auto_close = true;

   public function __construct ($url, $alt = 'Image') {
      $this->set_attribute('src', $url);
      $this->set_attribute('alt', $alt);
   }
}

?>
