<?php

class PageNavItem {
   public $text;
   public $url;

   public function __construct ($text, $url) {
      $this->text       = $text;
      $this->url        = $url;
   }
}

class Page {
   private $title = '';
   private $ai = null;
   private $is_admin = false;

   public function __construct ($ai = null) {
      $this->ai = $ai;
      $this->is_admin = false;

      if (Login::get_current_login()) {
         if (Login::get_current_login()->get_user()->has_permission('admin')) {
            $this->is_admin = true;
         }
      }
   }

   public static function redirect ($location, $die = true) {
      header('Location: ' . $location);
      if ($die) {
         die;
      }
   }

   public function get_info_for_banner () {
      if (!$this->ai) {
         # Without a system passed to us, pretend there's nothing to fill in.
         # This used to say "Error" and was confusing.
         return ['name' => '', 'serial' => '', 'site_name' => ''];
      }

      $serial = $this->ai->get_param_value('Serial Number');
      if ($serial && strlen($serial)) {
         $serial = 'A' . $serial;
      }
      else {
         $serial = '';
      }

      return [
         'name' => $this->ai->get_param_value('Product Name'),
         'model' => $this->ai->get_param_value('Product Model'),
         'serial' => $serial,
         'site_name' => $this->ai->get_param_value('Site Name')
      ];
   }

   public function begin_section ($title, $link = '') {
      echo '<div class="section">' . PHP_EOL;
      echo '<h1>' . $title;
      if (!empty($link)) {
         echo '<span>' . $link . '</span>';
      }
      echo '</h1>' . PHP_EOL;
      echo '<div class="section-content">' . PHP_EOL;
   }

   public function end_section () {
      echo '</div>' . PHP_EOL;
      echo '</div>' . PHP_EOL;
   }

   public function get_nav_items ($auto_nav = true) {
      $items = [
         0 => new PageNavItem('Monitor', '/'),
         10 => new PageNavItem('Records', '/records')
      ];

      if ($this->is_admin) {
         $items[20] = new PageNavItem('Configuration', '/reporting');
         $items[40] = new PageNavItem('Network', '/network');
         $items[60] = new PageNavItem('Users', '/users');
      }

      $items[50] = new PageNavItem('Event Log', '/events');

      # Do we need a debug page?
      if (is_link('/program')) {
         # Yes, the main program directory is a symbolic link to a RAM disk.
         $items[100] = new PageNavItem('Debug', '/debug');
      }

      # Do we need a log out button?
      if (Login::get_current_login() !== null) {
         $items[101] = new PageNavItem('Log Out', '/logout.php');
      }

      ksort($items);
      return $items;
   }

   public function get_html_nav_items ($auto_nav = true) {
      $html = '';
      $items = $this->get_nav_items($auto_nav);

      foreach ($items as $index => $item) {
         $html .= '<li><a href="' . htmlspecialchars($item->url) . '">';
         $html .= htmlspecialchars($item->text) . '</a></li>';
      }

      return $html;
   }

   public function header ($title = '', $auto_info = true, $auto_nav = true) {
      if ($auto_info === true) {
         $info = $this->get_info_for_banner();
      } else {
         $info = $auto_info;
      }

      # If our title is not empty, prefix it with a colon and format it.
      if (!empty($title)) $title = ': ' . $title;

      # Stylesheet?
      $stylesheet = 'blue';

?>
   <!DOCTYPE html>
   <html>
      <head>
         <title><?= $info['name'] ?? 'Injector' ?><?= $title ?></title>
         <meta http-equiv="content-type" content="text/html; charset=utf-8" />
         <link rel="stylesheet" type="text/css" href="/css/<?= $stylesheet ?>.css" />
         <script type="text/javascript" src="/scripts/jquery-1.11.2.min.js"></script>
         <script type="text/javascript" src="/scripts/help.js"></script>
      </head>
      <body>
         <div id="top">
            <div id="logo"></div>
            <div id="info">
               <p><?= $info['name'] ?></p>
               <p><?= $info['model'] ?></p>
               <p><?= $info['site_name'] ?></p>
               <p><?= $info['serial'] ?></p>
            </div>
         </div>
         <div id="nav">
            <ul>
               <?php echo $this->get_html_nav_items($auto_nav); ?>
            </ul>
            <div id="clock"><?php
               if (Login::get_current_login()) {
                  $username = Login::get_current_login()->get_user()->username;
                  $realname = Login::get_current_login()->get_user()->get_formatted_name();
                  echo 'You are <a href="/users/edit.php?username=' . $username . '">' . $realname . '</a>. It is ';
               }
               echo date('m/d/Y, g:i A.');
            ?></div>
         </div>
         <div id="content">
<?php

      # Success/error banner? (Not both)
      if (isset($_GET['save-success'])) {
         echo '<div class="banner success">Your changes were saved successfully.</div>';
         echo '<script type="text/javascript">window.setTimeout(function () { $(\'.banner.success\').slideUp(); }, 3500);</script>';
      }
   }

   public function error_banner () {
      echo '<div class="banner error">One or more of your changes have not yet been saved. See errors below.</div>';
   }

   public function footer () {
?>
         </div>
         <div id="bottom"></div>
      </body>
   </html>
<?php
   }
}

?>
