<?php

$page_selector = 'calibration';
require('../main.php');
require('math.php');

$web_users = new WebUserConfig();
$ipc = new Ipc();
$login = new Login($web_users, true, $ipc);
$system = new AdditiveInjector($ipc);
$self_dir = '/records';
$self = "$self_dir/calibration.php";
$path = "/config/records/calibration/CALIBRATION_REC.CSV";
$records = new RecordFiles($system);

if (isset($_GET['download'])) {
   # Same as below, but GET.

   if (!file_exists($path)) {
      ErrorPage::show('The records you requested do not exist.');
   }

   # Hardcoded header file, at the moment

   header('Content-Type: text/plain; charset=us-ascii');
   header('Content-Type: application/octet-stream');
   header('Content-Disposition: attachment; filename=" ' .basename($path). '"');
   header('Expires: 0');
   header('Pragma: public');
   header('Content-Length: ' . filesize($path));
   header('Content-Description: File Transfer');
   header('Cache-Control: must-revalidate');

   readfile($path); 
   die;
}


$page = new Page($system);
$page->header('Calibration Records');

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


$page->begin_section('Calibration Records');

if (file_exists($path)) {
   $info = pathinfo($path);
   echo '<p class="center" style="margin-bottom: 1.2em">You can also ' .
        '<a href="/records/calibration.php?download&amp;filename=' . $info['filename'] . '">download these records</a> ' .
        'to your computer.</p>'; # Hover over a header to see its description.</p>';

   $handle = fopen($path, "r");
   
   $twoDarray = array();
   if (($handle = fopen($path, "r")) !== FALSE) {
      $header_data = fgetcsv($handle);
       while (($data = fgetcsv($handle)) !== FALSE) {
           $twoDarray[] = $data;
       }
       fclose($handle);
   }

   //Print_r($twoDarray);
   //echo '<hr>';
   //var_dump($twoDarray);

   $table = new Table();
   $table->append_attribute('class', 'data vertical-separators');
   $table->add_style('width', '100%');

   $width = number_format(100 / count($header_data), 1, '.', '') . '%';

   $header = new TableHeader();

   foreach ($header_data as $index => $text) {
      $cell = new TableHeaderCell($text, $width);
      $cell->set_attribute('id', 'header-' . $index);
      $header->add_child($cell);
   }
   $table->add_child($header);


   $first = true;
   foreach ($twoDarray as $row) {
      $table_row = new TableRow();
      for ($col = 0; $col < count($row); $col++) {
         $row_child = new TableCell($row[$col]);
         if ($first) {
            $row_child->set_attribute('width', $width);
            $first = false;
         }
         $table_row->add_child($row_child);
      }
      $table->add_child($table_row);
   }

   echo $table->get_html();
}
else {
   # There aren't any record files to show.
   echo '<p>There are no calibration records on this system.</p>';
   #echo '<p>Calibration recording has not yet been implemented for this system.</p>';
}

$page->end_section();

$page->footer();

?>
