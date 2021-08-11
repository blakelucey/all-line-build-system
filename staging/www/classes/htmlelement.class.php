<?php

class HtmlElement {
   protected $tag = 'invalid';
   protected $attributes = [];
   protected $styles = [];
   protected $text = '';
   protected $children = [];
   protected $auto_close = false;
   protected $auto_escape = true;
   protected $error_text = '';
   protected $parent = null;

   public function __construct ($children = []) {
      if (is_array($children)) {
         foreach ($children as $child) $this->add_child($child);
      } else {
         $this->add_child($children);
      }
   }

   public function set_text ($new_text) {
      $this->text = $new_text;

      return $this;
   }

   public function append_text ($more_text) {
      $this->text .= $more_text;

      return $this;
   }

   public function add_child ($child) {
      if (!is_a($child, 'HtmlElement')) return;
      $this->children[] = $child;
      $child->parent = $this;

      return $this;
   }

   public function get_children () {
      return $this->children;
   }

   public function get_style_text () {
      $style = '';

      foreach ($this->styles as $name => $value) {
         $style .= $name . ': ' . $value . '; ';
      }

      return rtrim($style);
   }

   public function add_style ($name, $value) {
      $this->styles[$name] = $value;

      return $this;
   }

   public function delete_style ($name) {
      if (isset($this->styles[$name])) {
         unset($this->styles[$name]);
      }

      return $this;
   }

   public function get_attributes_text () {
      $attr = '';
      $did_style = false;

      foreach ($this->attributes as $name => $value) {
         if ($value === true) {
            $attr .= $name . ' ';
         } else {
            if ($name === 'style') {
               # Combine style information with any explicit style attribute
               $attr .= $name . '="' . trim($value, ';');
               $attr .= $this->get_style_text();
               $attr .= '" ';
               $did_style = true;
            } else {
               $attr .= $name . '="' . htmlspecialchars($value) . '" ';
            }
         }
      }

      if (!$did_style && !empty($this->styles)) {
         $attr .= 'style="' . $this->get_style_text() . '" ';
      }

      $attr = substr($attr, 0, -1);

      return $attr;
   }

   public function delete_attribute ($name) {
      if (isset($this->attributes[$name])) {
         unset($this->attributes[$name]);
      }

      return $this;
   }

   public function set_attribute ($name, $value = '') {
      $this->attributes[$name] = $value;

      return $this;
   }

   public function append_attribute ($name, $value) {
      if (!isset($this->attributes[$name])) {
         $this->set_attribute($name, $value);
         return $this;
      }

      $this->attributes[$name] .= ' ' . $value;

      return $this;
   }

   public function get_html () {
      $text = '<' . $this->tag;

      $attr = $this->get_attributes_text();
      if (strlen($attr) > 0) {
         $text .= ' ' . $attr;
      }

      if (!$this->auto_close) {
         $text .= '>';
         foreach ($this->children as $element) {
            if (is_a($element, 'HtmlElement')) {
               $text .= $element->get_html();
            }
         }

         if ($this->auto_escape) {
            $text .= htmlspecialchars($this->text);
         } else {
            $text .= $this->text;
         }

         $text .= '</' . $this->tag . '>';
      } else {
         $text .= ' />';
      }

      return $text;
   }
}

?>
