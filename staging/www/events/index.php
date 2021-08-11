<?php

require('../main.php');

$web_users = new WebUserConfig();
$ipc = new Ipc();
$login = new Login($web_users, true, $ipc);

if (isset($_GET['clear'])) {
   # Delete the event log and write a "cleared" message.
   if (!$login->get_user()->has_permission('admin')) {
      Page::redirect('/events');
      die;
   }

   $ipc->request([
      'request_type' => 'clear_event_log',
      'user' => $login->get_user()->get_real_name()
   ]);

   Page::redirect('/events');
   die;
}

$system = new AdditiveInjector($ipc);
$events = new EventLog();

$page = new Page($system);

$page->header('Event Log');
$page->begin_section('Event Log (most recent first)');

$table = new Table();
$table->append_attribute('class', 'data vertical-separators');
$table->add_style('width', '100%');

$header = new TableHeader();
$header->add_child(new TableHeaderCell('Time', '11em'));
$header->add_child(new TableHeaderCell('Type', '8em'));
$header->add_child(new TableHeaderCell('Event Text'));

$table->add_child($header);

$rows = [];
foreach ($events as $event) {
   if ($event->time == False) continue;
   $row = new TableRow();

   $row->add_child(new TableCell($event->time->format('Y-m-d H:i')));
   $row->add_child(new TableCell($event->kind));
   $row->add_child(new TableCell($event->text));

   $rows[] = $row;
}

$rows = array_reverse($rows);
foreach ($rows as $row) {
   $table->add_child($row);
}

echo $table->get_html();

if ($login->get_user()->has_permission('admin')) {
   echo '<hr />';
   echo '<p class="center"><a href="/events/index.php?clear">Clear Event Log</a></p>';
}

$page->end_section();

?>
