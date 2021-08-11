<?php

require('../main.php');

$web_users = new WebUserConfig();
$ipc = new Ipc();

# This differs slightly from the Fuel-Boss version
$ai = new AdditiveInjector($ipc);

$login = new Login($web_users, true, $ipc);

$login->admin_check();

$who = $_GET['username'] ?? false;
if ($who === false) {
   Page::redirect('/');
}

$user = $web_users->get_by_username($who);
if (!$user) {
   Page::redirect('/');
}

# Can we delete this?
$num_admin = 0;
foreach ($web_users as $u) {
   if ($u->has_permission('admin')) $num_admin++;
}

# If this is the only administrator, we can't let them do that.
# There is always the hidden 'all-line' account, which is also an
# administrator, so $num_admin will always be 1 at minimum.
if ($num_admin <= 2 && $user->has_permission('admin')) {
   ErrorPage::show('You cannot delete the last administrative manager.');
}

session_start();

$deleter = new DeleteSomething();

$error = $deleter->error();
if ($deleter->submitted() && !$error) {

   # Do delete.
   $web_users->delete_user($who);

   $deleter->success($path . '/users');
   die;
}

$deleter->generate();
$deleter->action = $path . '/users/delete.php?username=' . $who;
$deleter->title = 'Delete Manager ' . $user->get_formatted_name();
$deleter->text = 'To delete this manager, solve the challenge and click Delete.';
$deleter->return_link = $path . '/users';
$deleter->execute($error);

?>
