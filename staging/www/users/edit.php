<?php

require('../main.php');

$web_users = new WebUserConfig();
$ipc = new Ipc();

# This differs slightly from the Fuel-Boss version
$ai = new AdditiveInjector($ipc);

$login = new Login($web_users, true, $ipc);
$left_col = '12em';

$new = isset($_GET['new']);
$who = false;

if (!$new) {
   $who = $_GET['username'] ?? false;
   if ($who === false) {
      Page::redirect('/');
      die;
   }
}

# Are we editing all-line?
$editing_all_line = false;
if ($who === 'all-line' && $login->is_all_line()) {
   $editing_all_line = true;
}

# Are we editing ourselves?
$self_edit = false;
if (!$new && $who != $login->get_user()->username) {
   # We aren't; check that they can do this.
   $login->admin_check();
}
else {
   $self_edit = true;
   if ($new) $self_edit = false;
}

$page = new Page($ai);
$title = 'Edit Manager';
if ($self_edit) $title = 'Edit Your Details';
if ($new) $title = 'Add a New Manager';

$errors = [];

if (isset($_POST['submit'])) {
   # Create or edit the user.
   $username = $_POST['apricot'] ?? '';
   $password1 = $_POST['password1'] ?? false;
   $password2 = $_POST['password2'] ?? false;
   $realname = $_POST['realname'] ?? '';
   $is_admin = isset($_POST['isadmin']);

   if ($editing_all_line) $username = 'all-line';

   $user = ($new ? new WebUser() : $web_users->get_by_username($who));

   # Are they trying to turn off administrative privileges for the last administrator?
   if (!$self_edit) {
      $num_admin = 0;
      foreach ($web_users as $u) {
         if ($u->has_permission('admin')) $num_admin++;
      }
      if ($num_admin <= 2 && !$is_admin && $user->has_permission('admin')) {
         # Yeah, we can't let them do that.
         $errors['isadmin'] = 'You cannot remove administrative permissions from the last administrator.';
      }
   }

   # Some checks.
   if (!strlen($username)) {
      $errors['username'] = 'Username cannot be blank.';
   }
   else {
      if (preg_match('/^[a-zA-Z0-9\\.-]+$/', $username) !== 1) $errors['username'] = 'Invalid username; alphanumeric characters only.';
   }

   # Does this already exist? If they're editing a user, make sure they can't
   # change the name to a different one that is also in use.
   if ($new || $username !== $user->username) {
      if ($web_users->get_by_username($username)) {
         $errors['username'] = 'Username is already in use.';
      }
   }

   if ($new || (strlen($password1) || strlen($password2))) {
      # They have to set a password, or are changing theirs.
      if ($password1 !== $password2) {
         $errors['password1'] = 'Passwords do not match.';
      }

      if ($new && !strlen($password1)) {
         $errors['password1'] = 'You must set a password for the new manager.';
      }
   }

   # OK?
   if (count($errors) === 0) {
      $user->username = $username;
      $user->real_name = $realname;

      # Users editing themselves cannot turn off the admin permission.
      if (!$self_edit) {
         if ($is_admin) {
            # Make sure if there are special permissions set, like 'all-line' or 'update', etc
            # that those stick around.
            $user->permissions = array_merge($user->permissions, ['admin']);
         }
         else {
            $user->permissions = array_filter($user->permissions, function ($e) {
               return ($e !== 'admin');
            });
         }
      }

      if ($new) {
         $web_users->add_user($user, $password1);
      }
      else {
         # Editing; are they changing a password?
         if (strlen($password1)) {
            $user->set_password($password1);
         }
      }

      $web_users->save();

      if ($self_edit) {
         Page::redirect('/users/edit.php?username=' . $username . '&save-success');
      }
      else {
         Page::redirect('/users/?save-success');
      }
      die;
   }

   # Fall through to display errors.
}
else {
   # Load data.
   $user = ($new ? new WebUser() : $web_users->get_by_username($who));

   $username = $user->username;
   $realname = $user->real_name;
   $is_admin = in_array('admin', $user->permissions);
}

$page->header($title);
$page->begin_section($title);

$form = null;

if ($new) {
   $form = new Form('/users/edit.php?new');
}
else {
   $form = new Form('/users/edit.php?username=' . $who);
}

if (!$editing_all_line) {
   $form->add_child(new FormRow(
      'Username',
      [
         new TextBox('apricot', false, $username, 16, 30),
         new PlainText('<br />The name the manager will use to log in. Up to 30 characters.')
      ],
      $left_col,
      $errors['username']
   ));
}
else {
   $form->add_child(new FormRow(
      'Username',
      [
         (new TextBox('unused', false, $username, 16, 30))->set_attribute('disabled', 'disabled')
      ],
      $left_col,
      $errors['username']
   ));
}

$form->add_child(new FormRow(
   'Password',
   [
      new PasswordBox('password1', false, 16, 128, true),
      new PlainText(
         $new ? '<br />The password for the user. Up to 128 characters.' :
         '<br />Enter this only if you want to change ' . ($self_edit ? 'your' : 'this user\'s') . ' password.'
      )
   ],
   $left_col,
   $errors['password1']
));

$form->add_child(new FormRow(
   'Repeat Password',
   [
      new PasswordBox('password2', false, 16, 128, true),
      new PlainText('<br />Repeat the same password you typed above' . ($new ? '.' : ', if changing ' . ($self_edit ? 'your' : 'this user\'s') . ' password.'))
   ],
   $left_col,
   $errors['password2']
));

$form->add_child(new FormRow(
   'Real Name',
   [
      new TextBox('realname', false, $realname, 22, 50),
      new PlainText(
         $self_edit ?
         '<br />Your real name. Optional. Up to 50 characters.' :
         '<br />The real name for this user. Optional. Up to 50 characters.'
      )
   ],
   $left_col
));

if (!$self_edit) {
   $form->add_child(new FormRow(
      '&nbsp;',
      [
         new CheckBox('isadmin', false, 'This user will be an administrator', $is_admin == true, '1'),
         new PlainText('<br /><span style="padding-left: 1.75em">Administrators can change system settings, edit other managers, and add groups and accounts</span>')
      ],
      $left_col,
      $errors['isadmin']
   ));
}

$form->add_child(new FormRow(
   '&nbsp;',
   new SubmitButton('submit', false, $new ? 'Add Manager' : 'Save Changes'),
   $left_col
));

echo $form->get_html();

$page->end_section();

$page->footer();


