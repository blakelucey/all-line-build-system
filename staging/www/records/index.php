<?php

require('../main.php');
require('math.php');

$web_users = new WebUserConfig();
$ipc = new Ipc();
$login = new Login($web_users, true, $ipc);
$system = new AdditiveInjector($ipc);
$fields = $ipc->request(['request_type' => 'get_record_fields'])['fields'] ?? [];
$records = new RecordFiles($system);
$math = new RecordMath($records, $system);

#print_var($ipc);
#print_var($system);

init_summarizers($math);

function do_table ($page, $rec) {
   global $fields;
   global $system;
   global $total_diesel;
   global $total_bio;
   global $total_target;
   global $max_flow_rate;
   global $accuracy;
   global $main_name;
   global $additive_name;

   $rec_time = mktime(0, 0, 0, $rec->month, 1, $rec->year);

   $page->begin_section('Records for ' . date('F Y', $rec_time));

   $info = pathinfo($rec->filename);
   echo '<p class="center" style="margin-bottom: 1.2em">You can also ' .
        '<a href="/records/index.php?download&amp;filename=' . $info['filename'] . '">download these records</a> ' .
        'to your computer.</p>'; # Hover over a header to see its description.</p>';

   echo '<p class="center" style="margin-bottom: 1.8em">Click ' .
        '<a href="#summary">here</a> to jump to this month\'s summary.</p>';

   $table = new Table();
   $table->append_attribute('class', 'data vertical-separators');
   $table->add_style('width', '100%');

   $header = new TableHeader();
   $widths = [];
   $width = number_format(100 / count($rec->columns), 1, '.', '') . '%';
   foreach ($rec->columns as $index => $text) {
      $cell = new TableHeaderCell($text, $width);
      $cell->set_attribute('id', 'header-' . $index);
      $header->add_child($cell);
   }
   $table->add_child($header);

   $first = true;
   foreach ($rec->rows as $index => $row) {
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

   # Create tooltip divs
   foreach ($fields as $index => $field) {
      $tt = new DivElement();
      $tt->set_attribute('id', 'tooltip-' . $index);
      $tt->append_attribute('class', 'header-tooltip');

      $tt_text = new DivElement();
      $tt_text->set_text($field['description']);

      $tt->add_child($tt_text);

      echo $tt->get_html();
   }

   if (isset($_GET['showdelete'])) {
      echo '<hr />';
      echo '<p class="center">' .
           '<a href="/records/index.php?delete&amp;filename=' . $info['filename'] . '">Delete These Records</a> ' .
           '</p>';
   }

   $page->end_section();
}

function do_script () {
   global $fields;

   # This generates a hover and non-hover event for each of the table headers
   # that shows the corresponding tooltip. It was hacked together pretty quickly
   # and isn't my best work, but it looks nice.

   # This is disabled for now! It plays with long tables in a weird way.
   #return
   #THIS IF FIXED NOW!!! (3/12/2021) - brad
   #ok... ALMSOT fixed... for some reason the 'absolute' destroys the margins of the div?

   ?><script type="text/javascript" src="/scripts/jquery.floatThead.js"></script>
   <script type="text/javascript">
      $(function () {
         /* To anyone reading this, I'm aware this is not great. */
         $('table.data').css("width","98%");
         $('table.data').floatThead({
            position: 'absolute',
            top: -1,
         });
         var onHover = function (header, tt) {
            var doc = $(document);
            var pos = header.offset();
            var height = header.height();
            var width = header.height();
            var top = pos.top + height - doc.scrollTop() + 8;
            var left = pos.left;
            if (pos.left + 280 > doc.width()) left = doc.width() - 280;
            tt.css({'left': left, 'top': top}).fadeIn(150);
         };
         <?php foreach ($fields as $index => $field): ?>
         $('#header-<?= $index ?>').hover(
            function () { onHover($('#header-<?= $index ?>'), $('#tooltip-<?= $index ?>')); },
            function () { $('#tooltip-<?= $index ?>').fadeOut(100); }
         );
         <?php endforeach; ?>
      });
   </script><?php
}

if (isset($_GET['download'])) {
   # Same as below, but GET.
   $param = $_GET['filename'];
   $sel_rec = $records->get_by_filename($param . '.CSV');
   if ($sel_rec === false) {
      ErrorPage::show('The records you requested do not exist.');
   }

   # Hardcoded header file, at the moment
   $headers = trim(@file_get_contents('/config/headers.txt')) . "\r\n";
   $data    = trim(@file_get_contents($sel_rec->filename));
   $size    = strlen($headers . $data);

   header('Content-Type: text/plain; charset=us-ascii');
   header('Content-Type: application/octet-stream');
   header('Content-Disposition: attachment; filename=' . $_GET['filename'] . '.CSV');
   header('Expires: 0');
   header('Pragma: public');
   header('Content-Length: ' . $size);
   header('Content-Description: File Transfer');
   header('Cache-Control: must-revalidate');

   echo $headers . $data;
   die;
}

if (isset($_GET['delete'])) {
   $yes = ($_POST['confirm'] === 'Yes');
   $no = ($_POST['cancel'] === 'No');
   if (!$yes && !$no) {
      $page = new Page($system);
      $page->header('Delete Record File');
      $page->begin_section('Delete Record File');
      echo '<p>Are you absolutely sure you want to delete this file? This action <span class="error">cannot be undone</span>.</p>';
      echo '<form action="/records/?delete&amp;filename=' . $_GET['filename'] . '" method="post">';
      echo '<div class="form-row">';
      echo '<input type="submit" class="button" name="confirm" value="Yes" />&nbsp;&nbsp;';
      echo '<input type="submit" class="button" name="cancel" value="No" />';
      echo '<input type="hidden" name="submit" value="1" />';
      echo '<input type="hidden" name="filename" value="' . $_GET['filename'] . '" />';
      echo '</div>';
      echo '</form>';
      $page->end_section();
      $page->footer();
      die;
   }
   else if ($yes && !$no) {
      $sel_rec = $records->get_by_filename($_GET['filename'] . '.CSV');
      if ($sel_rec === false) {
         ErrorPage::show('The records you requested do not exist.');
      }

      unlink($sel_rec->filename);
      Page::redirect('/records/');
      die;
   }
}

$page = new Page($system);

$page->header('Records');

if (count($records)) {
   # Warn them about a math problem?
   $result = false;
   if (isset($sel_rec)) {
      $result = $math->get_results_for_year_and_month($sel_rec->year, $sel_rec->month);
      $math->print_warnings($page);
   }

   $page->begin_section($system->get_param_value('Product Name') . ' Records');
   echo $form->get_html();
   $page->end_section();

   if (isset($sel_rec)) {
      do_table($page, $sel_rec);
      do_script();
      $math->print_math($page, $result);
   }
} else {
   # Empty file list
   $page->begin_section($system->get_param_value('Product Name') . ' Records');
   echo '<p>There are no record files on this system.</p>';
   echo '<p>Click <a href="/records/calibration.php">here</a> to view any calibration records</p>';
   $page->end_section();
}

$page->footer();

?>

<script type="text/javascript">
/*   function toggle_tanks () {
      let is_checked = $('#tank_enable').prop('checked');
      is_checked ? $('td:nth-child(2)').hide() : $('td:nth-child(2)').show();
   }
*/   
</script>
