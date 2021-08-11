<?php

class Login {
   private static $current_login = null;

   private $users;
   private $username;
   private $password;
   private $user;

   public function __construct ($users, $auto_login = false) {
      $this->users = $users;
      if ($auto_login) {
         $this->login();
      }
   }

   public function is_all_line () {
      if (!($this->user instanceof WebUser)) return false;
      if ($this->user->username !== 'all-line') return false;
      if (!$this->is_admin()) return false;
      return true;
   }

   public function is_admin () {
      if (!($this->user instanceof WebUser)) return false;
      return in_array('admin', $this->user->permissions);
   }

   public function admin_check () {
      if (!$this->is_admin()) {
         ##ErrorPage::show('You do not have permission to access this page.');

         http_response_code(404);
         die;
      }
   }

   public function login () {
      session_start();

      # If the session contains login info, use that
      if (isset($_SESSION['username']) && isset($_SESSION['password'])) {
         $this->username = $_SESSION['username'];
         $this->password = $_SESSION['password'];
      } else {
         # It does not. Use POST data.
         $this->username = $_POST['reticulating'];
         $this->password = $_POST['splines'];
      }

      # Check the login information
      $e_username = $this->username;
      $e_password = sha1($this->password);
      $result = $this->users->authenticate($e_username, $e_password);

      if ($result === false) {
         # Seems invalid. Show a form.
         if (!empty($this->username) || !empty($this->password)) {
            $error = 'Invalid user name or password.';
         } else {
            $error = '';
         }

         unset($_SESSION['username']);
         unset($_SESSION['password']);

# * * * * * * * * * * * * * * * * * * * * Login Form Begin * * * * * * * * * * * * * * * * * * * *
?><!DOCTYPE html>
<html>
   <head>
      <title>Login</title>
      <meta http-equiv="content-type" content="text/html; charset=utf-8" />
      <link rel="stylesheet" type="text/css" href="/css/blue.css" />
   </head>
   <body style="background: none !important;">
      <div id="login">
         <div id="login-logo">
         </div>
         <form method="post" action="/">
         <p class="center big<?= strlen($error) ? ' error' : '' ?>"><?= !strlen($error) ? 'Please enter your credentials to access this system.' : $error ?></p>
            <div class="form-row">
               <div class="label" style="width: 13em">Username</div>
               <div class="container">
               <input type="text" class="text" id="reticulating" name="reticulating" maxlength="20" size="16" value="<?= htmlspecialchars($e_username) ?>" />
               </div>
            </div>
            <div class="form-row">
               <div class="label" style="width: 13em">Password</div>
               <div class="container">
                  <input type="password" class="text" id="splines" name="splines" maxlength="128" size="16" />
               </div>
            </div>
            <div class="form-row">
               <div class="label" style="width: 13em">&nbsp;</div>
               <div class="container">
                  <input type="submit" class="button" id="submit" name="submit" value="Log In" />
               </div>
            </div>
         </form>
      </div>
   </body>
</html><?php
# * * * * * * * * * * * * * * * * * * * * * Login Form End * * * * * * * * * * * * * * * * * * * *
         die;
      } else {
         # Seems valid. Happy.
         $_SESSION['username'] = $this->username;
         $_SESSION['password'] = $this->password;

         $this->user = $result;

         # Set our global login
         if (self::$current_login === null) {
            self::$current_login = $this;
         }
      }
   }

   public static function logout () {
      session_start();

      unset($_SESSION['username']);
      unset($_SESSION['password']);
   }

   public function get_user () {
      return $this->user;
   }

   public static function get_current_login () {
      return self::$current_login;
   }
}

?>
