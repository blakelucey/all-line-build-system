<?php

class CheckListBox extends FormElement {
   protected $items;

   public function __construct ($id, $name, $items = [], $height = '10em') {
      $this->set_attribute('id', $id);
      $this->set_attribute('name', $name === false ? $id : $name);
      $this->add_style('height', $height);

      # Item: [text => text, state => true/false, value => value]
      $this->items = $items;
   }

   public function get_html () {
      $this->children = [];

      foreach ($this->items as $idx => $item) {
         $id = $this->attributes['id'] . '-' . $idx;
         $name = $this->attributes['name'];

         $this->add_child(
            new CheckBox($id, $name . '[]', $item['text'], $item['state'], $item['value'])
         );
      }

      $text = '<div class="checklistbox" style="' . $this->get_style_text() . '">' . PHP_EOL;
      $text .= '<div class="inner">' . PHP_EOL;

      foreach ($this->children as $child) {
         $text .= $child->get_html();
         $text .= '<br />';
      }

      $text .= '</div>' . PHP_EOL;
      $text .=' </div>' . PHP_EOL;

      return $text;
   }
}

?>
