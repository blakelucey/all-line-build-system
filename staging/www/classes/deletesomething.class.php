<?php

class DeleteSomething {
   public $title = '';
   public $text = '';
   public $action = '';
   public $return_link = '/';

   private $first = null;
   private $second = null;
   private $result = null;

   public function __construct () {
   }

   public function generate () {
      $a = rand(1, 15);
      $b = rand(1, 15);

      $this->first = $a;
      $this->second = $b;
      $this->result = ($a + $b);
   }

   public function submitted () {
      return isset($_POST['submit']);
   }

   public function error () {
      if (!$this->submitted()) return false;

      if (isset($_POST['name']) && strlen($_POST['name']) > 0) {
         # The 'name' field should not be populated.
         return true;
      }

      if (!isset($_POST['pumpkin'])) {
         return true;
      }

      if (get_post('answer') !== $_POST['pumpkin']) {
         return true;
      }

      return false;
   }

   public function success ($url) {
      $page = new Page();
      $page->header();
      $page->begin_section('Success');
      echo '<p>The item was deleted successfully.</p>';
      echo '<p>Click <a href="' . $url . '">here</a> to return.</p>';
      $page->end_section();
      $page->footer();
      die;
   }

   public function execute ($error = false) {
      $page = new Page();
      $page->header();
      $page->begin_section($this->title);

      echo '<p>' . $this->text . '</p>';
      echo '<p>To return without deleting this item, click <a href="' . $this->return_link . '">here</a>.</p>';
      echo '<br />';

      $form = new Form($this->action, 'post');
      $left_col = '13em';

      $form->add_child(new HiddenInput('name', false, ''));
      $form->add_child(new HiddenInput('pumpkin', false, $this->result));

      $form->add_child(new FormRow(
         'Challenge',
         new PlainText('What\'s the result of ' . $this->first . ' + ' . $this->second . '?'),
         $left_col
      ));

      $form->add_child(new FormRow(
         'Enter the Answer',
         new TextBox('answer', false, '', 10, 6),
         $left_col,
         $error === true ? 'You did not enter the correct answer.' : ''
      ));

      $form->add_child(new FormRow(
         '&nbsp;',
         new SubmitButton('submit', false, 'Delete'),
         $left_col
      ));

      echo $form->get_html();

      $page->end_section();
      $page->footer();
   }
}

?>
