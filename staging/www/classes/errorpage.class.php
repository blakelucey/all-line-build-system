<?php

class ErrorPage extends Page {
   public static function show ($message, $title = '', $sectitle = '') {
      $page = new self();
      $page->header(empty($title) ? 'Error' : $title, true, false);
      $page->begin_section(empty($sectitle) ? 'Error' : $sectitle);
      echo '<p>' . $message . '</p>';
      $page->end_section();
      $page->footer();
      die;
   }
}

?>
