<?php

require('../main.php');

$web_users = new WebUserConfig();
$ipc = new Ipc();
$login = new Login($web_users, true, $ipc);
$system = new AdditiveInjector($ipc);
$self_dir = '/records';
$self = "$self_dir/delete.php";
$filename = $_GET['filename'] ?? null;
$suffix = '.CSV';
$records = new RecordFiles($system);
$rec = $records->get_by_filename($filename . $suffix);

if ($rec === false) Page::redirect($self_dir);

session_start();

$deleter = new DeleteSomething();

$error = $deleter->error();
if ($deleter->submitted() && !$error) {
   # Do the deletion using the IPC interface.
   $rec->delete($ipc, $login);
   $deleter->success($self_dir . '/manage.php');
   die;
}

$deleter->generate();
$deleter->action = $self . '?filename=' . $filename;
$deleter->title = "Delete Records for $rec->month_name of $rec->year";
$deleter->text = 'To delete these records, solve the challenge and click Delete.';
$deleter->return_link = $self_dir . '/manage.php';
$deleter->execute($error);

?>
