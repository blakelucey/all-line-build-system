<?php

$page_selector = 'manage';
require('../main.php');
require('math.php');

$web_users = new WebUserConfig();
$ipc = new Ipc();
$login = new Login($web_users, true, $ipc);
$system = new AdditiveInjector($ipc);
$self_dir = '/records';
$self = "$self_dir/manage.php";
$records = new RecordFiles($system);

$page = new Page($system);
$page->header('All Record Files');

if (count($records)) {
   
   $page->begin_section($system->get_param_value('Product Name') . ' Records');
   echo $form->get_html();
   $page->end_section();

} else {
  # Empty file list
  $page->begin_section($system->get_param_value('Product Name') . ' Records');
  echo '<p>There are no record files on this system.</p>';
  $page->end_section();
}


$page->begin_section('All Record Files');

if (count($records)) {
   $table = new Table();
   $table->append_attribute('class', 'data vertical-separators fixed-header');
   $table->add_style('width', '100%');

   $header = new TableHeader();
   $header->add_child(new TableRow([
      new TableHeaderCell('Year'),
      new TableHeaderCell('Month'),
      new TableHeaderCell('Number of Entries'),
      new TableHeaderCell('Size on Disk'),
      new TableHeaderCell('Options')
   ]));

   $body = new TableBody();

   $rows = [];
   foreach ($records as $rec) {
      $row = new TableRow();

      $row->add_child(new TableCell((string)$rec->year));
      $row->add_child(new TableCell((string)$rec->month_name));
      $row->add_child(new TableCell((string)count($rec)));
      $row->add_child(new TableCell((string)format_size($rec->file_size)));

      $info = pathinfo($rec->filename);
      $del_link = '<a href="' . $self_dir . '/delete.php?action=delete&amp;filename=' . $info['filename'] . '">Delete File</a>';
      $row->add_child(new TableCell($del_link));

      $rows[] = $row;
   }

   $rows = array_reverse($rows);
   foreach ($rows as $row) {
      $body->add_child($row);
   }

   $table->add_child($header);
   $table->add_child($body);

   echo $table->get_html();
}
else {
   # There aren't any record files to show.
   echo '<p>There are no record files on this system.</p>';
}

$page->end_section();

if (isset($_GET['summarize'])) {
   $math = new RecordMath($records, $system);
   init_summarizers($math);

   $math->print_warnings($page);
}

$page->begin_section('More Information');

# Do some math?
if (isset($_GET['summarize'])) {
   $result = $math->get_results_for_everything();

   echo '<p>This is a summary of all of the records ever saved by this system.</p>';
   echo '<hr />';

   $math->print_math($page, $result, false);

   echo '<hr />';
}
else {
   echo '<p>You can request a summary of all of the records on this system by clicking ';
   echo '<a href="' . $self . '?summarize">here</a>, although this may take a few seconds to prepare.</p>';
}

# Scrape 'df' for the free space on /config in KB
$df = explode("\n", `df /config`);
$free = (int)(preg_split('@\s@', $df[1], NULL, PREG_SPLIT_NO_EMPTY)[3]);

# We need bytes
$free *= 1024;

# Do more math
$avg_length = 140;
$remaining = (int)($free / $avg_length);
$remaining = number_format($remaining, 0, '', ',');
echo "<p>There is enough space left for approximately $remaining additional records.</p>";

$page->end_section();

$page->footer();

?>
