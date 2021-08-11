<?php

require('../main.php');

if (isset($_GET['info'])) {
   # This page should act as an update event source.
   # It will query the firmware_update_status parameter via IPC and report it.
   $events = new EventEmitter();
   $ipc = new Ipc(true);

   while (true) {
      $result = $ipc->request([
         'request_type' => 'firmware_update_status'
      ]);

      if ($result['error']) break;

      $events->emit($result['status_text']);
      $events->wait(250);
   }

   die;
}

$self = '/update/index.php';
$web_users = new WebUserConfig();
$login = new Login($web_users, true);
$ipc = new Ipc();
$system = new AdditiveInjector($ipc);
$page = new Page($system);

if (!$login->get_user()->has_permission('admin')) {
   ErrorPage::show('You do not have permission to update the software on this system.');
   die;
}

# Firmware update for the mainboard
if (isset($_POST['firmware'])) {
   $url = get_post('url');
   $result = $ipc->request([
      'request_type' => 'firmware_update',
      'file' => $url
   ]);

   if ($result['error']) {
      ErrorPage::show($result['message']);
   }

   header('Refresh: 30; url=/');

   $page->header('Firmware Update');
   $page->begin_section('Firmware Update');
   echo '<p>Please wait while the system updates its firmware. <b>This will refresh automatically.</b></p>';
   echo '<br />';
   echo '<div id="task-text"></div>';
   echo '<div class="progress-bar">';
   echo '<div class="background">&nbsp;</div>';
   echo '</div>';
   echo '<script type="text/javascript" src="/scripts/update.js"></script>';
   $page->end_section();
   $page->footer();

   die;
}

# Software update for the web interface
if (isset($_POST['software'])) {
   $url = get_post('url');
   $result = $ipc->request([
      'request_type' => 'software_update',
      'file' => $url
   ]);

   if ($result['error']) {
      ErrorPage::show($result['message']);
   }

   header('Refresh: 30; url=/');

   $page->header('Software Update');
   $page->begin_section('Software Update');
   echo '<p>Please wait while the system updates its software. <b>This will refresh automatically in about <span id="counter"></span> seconds.</b></p>';
?><script type="text/javascript">
   var counter = 30;
   var tick = function () {
      document.getElementById('counter').innerText = counter.toString();
      counter--;
      window.setTimeout(tick, 1000);
   };
   tick();
</script><?php
   $page->end_section();
   $page->footer();

   die;
}

# Main software update
if (isset($_POST['submit']) || isset($_POST['reboot'])) {
   die;
}

$page->header('Firmware Update');
$page->begin_section('Firmware Update');

$form = new Form($self);
$form->add_child(new FormRow(
   'URL of Firmware File',
   new TextBox('url', false, '', 40, 240),
   '13em'
));

$form->add_child(new FormRow(
   '&nbsp;',
   new SubmitButton('firmware', false, 'Update'),
   '13em'
));

echo $form->get_html();

$page->end_section();

$page->begin_section('Web Interface Update');
$form = new Form($self);
$form->add_child(new FormRow(
   'URL of Update File',
   new TextBox('url', false, '', 40, 240),
   '13em'
));

$form->add_child(new FormRow(
   '&nbsp;',
   new SubmitButton('software', false, 'Update'),
   '13em'
));

echo $form->get_html();

$page->end_section();
$page->footer();

?>
