<?php

# *** NOTE ***
# This can manage multiple users with real names and passwords.
# However, for the time being, it is ONLY for the 'all-line' user and the 'user' user.
# Some things in here are designed around that.

class WebUser {
   public $real_name;
   public $username;
   public $permissions = [];
   public $password_hash;

   public function __construct ($real_name = null, $username = null, $password_hash = null) {
      $this->real_name = $real_name;
      $this->username = $username;
      $this->password_hash = $password_hash;
   }

   public function set_password ($pw) {
      $this->password_hash = sha1($pw);
   }

   public function get_formatted_name () {
      $text = $this->username;
      if (strlen($this->real_name)) $text = $this->real_name;
      return htmlspecialchars($text);
   }

   public static function from_json ($json) {
      $web_user = new WebUser();

      $web_user->real_name = $json['real_name'];
      $web_user->username = $json['username'];
      $web_user->password_hash = $json['password_hash'];
      $web_user->permissions = $json['permissions'];

      return $web_user;
   }

   public function has_permission ($perm) {
      if (!is_array($this->permissions)) return false;
      return in_array($perm, $this->permissions);
   }

   public function get_real_name () {
      if (empty($this->real_name)) return $this->username;
      return $this->real_name;
   }
}

class WebUserConfig implements Countable, Iterator {
   private $web_users = [];
   private $ptr = 0;

   public const default_user = 'user';

   public function __construct () {
      $this->load();
   }

   public function get_by_username ($username) {
      foreach ($this->web_users as $user) {
         if ($user->username === $username) return $user;
      }

      return null;
   }

   public static function get_json_file () {
      return get_path('config') . 'web-users.cfg';
   }

   public function add_user ($user, $password) {
      $user->password_hash = sha1($password);
      $this->web_users[] = $user;
      $this->save();
   }

   public function delete_user ($username) {
      $new_list = [];
      foreach ($this->web_users as $user) {
         if ($user->username === $username) continue;
         $new_list[] = $user;
      }
      $this->web_users = $new_list;
      $this->save();
   }

   public function set_password ($username, $newpw) {
      # Hash away
      $newpw = sha1($newpw);

      foreach ($this->web_users as &$web_user) {
         if ($web_user->username === $username) {
            $web_user->password_hash = $newpw;
            return;
         }
      }
   }

   public function authenticate ($username, $password_hash, $ipc = null) {
      foreach ($this->web_users as $web_user) {
         if ($web_user->username === $username) {
            # This is a matching user.
            # We can match against the stored password hash.
            # I'm an idiot and haven't salted them yet.
            # We can ALSO match against the activation code, if we've been given
            # an instance of Ipc().
            if ($ipc !== null && $ipc instanceof Ipc) {
               $code = $ipc->request([
                  'request_type' => 'get_param',
                  'param_name' => 'Activation Code'
               ]);

               if (sha1((string)$code['param_value']) === $password_hash) {
                  return $web_user;
               }

               # Not a match; fall through to try testing against the real password hash.
            }

            if ($web_user->password_hash === $password_hash) {
               return $web_user;
            }

            # Matched the user name, but didn't match the password.
            # We can't possibly match against someone else.
            return false;
         }
      }

      return false;
   }

   public function load ($filename = false) {
      if ($filename === false) {
         $filename = self::get_json_file();
      }

      # Load each user
      $this->web_users = [];

      $config = json_decode(@file_get_contents($filename), true);
      if ($config !== null) {
         foreach ($config['users'] as $data) {
            $web_user = WebUser::from_json($data);
            $this->web_users[] = $web_user;
         }
      }

      # Tack on the emergency user if there aren't any users
      if (!count($this->web_users)) {
         $all_line = new WebUser('All-Line Equipment', 'all-line', sha1('2236144'));
         $all_line->permissions = ['admin'];
         $this->web_users[] = $all_line;
      }

      # Save back what we've loaded; this will filter any invalid entries.
      $this->save($filename);
   }

   public function save ($filename = false) {
      if ($filename === false) {
         $filename = self::get_json_file();
      }

      $config = [
         'users' => $this->web_users
      ];

      file_put_contents($filename, json_encode($config, JSON_PRETTY_PRINT));
   }

   public function current () {
      return $this->web_users[$this->ptr];
   }

   public function key () {
      return $this->ptr;
   }

   public function next () {
      $this->ptr++;
   }

   public function rewind () {
      $this->ptr = 0;
   }

   public function valid () {
      return isset($this->web_users[$this->ptr]);
   }

   public function count () {
      return count($this->web_users);
   }
}

?>
