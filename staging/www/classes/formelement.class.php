<?php

class FormElement extends HtmlElement {
   protected $error_text = '';
   protected $parent = null;
   protected $error_state = false;

   public function set_error_text ($text) {
      $this->error_text = $text;
   }

   public function set_error_state ($state) {
      $this->error_state = $state;
      foreach ($this->children as $child) {
         if ($child instanceof FormElement) {
            $child->set_error_state($state);
         }
      }
   }

   public function get_html () {
      $text = parent::get_html();

      if (!empty($this->error_text)) {
         $text .= '<span class="form-error-text">' . htmlspecialchars($this->get_error_text) . '</span>';
      }

      $text .= PHP_EOL;

      return $text;
   }
}

?>
