<?php

class TableCell extends HtmlElement {
   protected $tag = 'td';
   protected $auto_escape = false;

   public function __construct ($contents) {
      if (is_string($contents)) {
         $this->text = $contents;
      } else {
         parent::__construct($contents);
      }
   }

   public function get_html () {
      return parent::get_html() . PHP_EOL;
   }
}

class TableHeaderCell extends TableCell {
   public $text = '';
   public $width = '';

   public function __construct ($text, $width = '') {
      $this->text = $text;
      $this->width = $width;

      if (strlen($width) > 0) {
         $this->add_style('width', $width);
      }
   }

   public function set_colspan ($span) {
      $this->attributes['colspan'] = $span;

      return $this;
   }
}

class TableRow extends HtmlElement {
   protected $tag = 'tr';

   public function __construct ($cells = []) {
      foreach ($cells as $cell) {
         if ($cell instanceof TableCell) {
            $this->add_child($cell);
         } else {
            $this->add_child(new TableCell($cell));
         }
      }
   }

   public function get_html () {
      return parent::get_html() . PHP_EOL;
   }
}

class TableHeader extends HtmlElement {
   protected $tag = 'thead';
}

class TableBody extends HtmlElement {
   protected $tag = 'tbody';
}

class Table extends HtmlElement {
   protected $tag = 'table';
}

?>
