<?php

require('../main.php');

$web_users = new WebUserConfig();
$ipc = new Ipc();

# This differs slightly from the Fuel-Boss version
$ai = new AdditiveInjector($ipc);

$login = new Login($web_users, true, $ipc);
$left_col = '10em';

$login->admin_check();

# Create a new user?
if (isset($_POST['submit'])) {
   $login_name = get_post('apricot');
   $password1 = get_post('horticulture');
   $password2 = get_post('lorentztransform');
   $realname = get_post('realname');
   $isadmin = isset($_POST['isadmin']);

   # Check the login_name for stupid things.
   if (preg_match('/^[a-zA-Z0-9]+$/', $login_name) !== 1) {
      $errors['apricot'] = 'Invalid user name; alphanumeric only, no spaces.';
   }

   if (strlen($login_name) > 30) {
      $errors['apricot'] = 'login_names must be 30 characters or fewer.';
   }

   # Reserved names aren't allowed.
   if ($login_name == 'all-line') {
      $errors['apricot'] = 'This login_name is reserved by the system.';
   }

   # Passwords must match and must not be empty.
   # Passwords are limited to 128 characters but we don't really need to check that.
   if (!strlen($password1) || !strlen($password2)) {
      $errors['horticulture'] = 'Password cannot be empty.';
   }

   if ($password1 !== $password2) {
      $errors['horticulture'] = 'Passwords do not match.';
   }

   # Real names can be anything reasonable.
   $realname = trim(strip_tags($realname));

   if (count($errors) === 0) {
      # Everything looks OK. Add this user and save.
      $new_user = new WebUser();

      $new_user->username = $login_name;
      $new_user->real_name = $realname;
      $new_user->permissions = $isadmin ? ['admin'] : [];

      $web_users->add_user($new_user, $password1);

      Page::redirect('/users?save-success');
   }

   # Fall through to display errors.
}

# Regular page load
else {
   $login_name = get_post('apricot');
   $realname = get_post('realname');
   $isadmin = isset($_POST['isadmin']);
}

$page = new Page($ai);

$page->header('Managers');

# Delete a user script
?><script type="text/javascript">
   var delete_user = function (username) {
      if (confirm('Are you sure you want to delete this user?')) {
         window.location.assign('/users/index.php?action=delete&login_name=' + username);
      }

      return false;
   };
</script><?php

$page->begin_section('Managers');

$table = new Table();
$table->append_attribute('class', 'data vertical-separators');
$table->add_style('width', '100%');

$header = new TableHeader();
$header->add_child(new TableHeaderCell('User Name', '11em'));
$header->add_child(new TableHeaderCell('Real Name', '20em'));
$header->add_child(new TableHeaderCell('Administrator?'));
$header->add_child(new TableHeaderCell('Actions', '18em'));

$table->add_child($header);

foreach ($web_users as $user) {
   # The All-Line user is not shown unless we're all-line
   if (!$login->is_all_line() && $user->username === 'all-line') continue;

   $row = new TableRow();
   $actions = '<a href="/users/edit.php?username=' . $user->username . '">Edit</a>';
   if ($user->username !== 'all-line') {
      $actions .= ' &middot; <a href="/users/delete.php?username=' . $user->username . '">Delete</a>';
   }

   $row->add_child(new TableCell('<a href="/users/edit.php?username=' . $user->username . '">' . $user->username . '</a>'));
   $row->add_child(new TableCell(strlen($user->real_name) ? htmlspecialchars($user->real_name) : '-'));
   $row->add_child(new TableCell($user->has_permission('admin') ? 'Yes' : 'No'));
   $row->add_child(new TableCell($actions));

   $table->add_child($row);
}

echo $table->get_html();

echo '<hr />';
echo '<p class="center"><a href="/users/edit.php?new">Add a New Manager</a></p>';

$page->end_section();

?>
