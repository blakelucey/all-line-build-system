<?php

$math_ipc = new Ipc();
$math_system = new AdditiveInjector($math_ipc);
$math_records = new RecordFiles($math_system);
$self_dir = '/records';
$self_math = "$self_dir/index.php";
$manage_page = "$self_dir/manage.php";
$calibration_page = "$self_dir/calibration.php";
$statistics_page = "$self_dir/statistics.php";

function init_summarizers ($math) {
   # These are summarizers. You can use these to summarize, maximize, or average
   # different fields by name. These will have to change when the injector board
   # software changes. So as a precaution, the records page will warn you when
   # these fields do not exist.
   $math->add_totalizer('TOTAL MAIN', 'Total Main Product');
   $math->add_totalizer('TOTAL MAIN METER', 'Total Main Product through Meter');
   $math->add_totalizer('TOTAL BIO', 'Total Bio Product', 3);
   $math->add_totalizer('TOTAL BIO METER', 'Total Bio Product through Meter', 3);
   $math->add_totalizer('TARGET BIO', 'Total Bio Required', 3);

   $math->add_maximizer('HIGH MAIN FLOW RATE', 'Highest Main Flow Rate', 1, ' %units% per minute');

   # Old:
   #$math->add_averager('ACCURACY', 'Overall Accuracy', 2, '%');
   $math->add_averager('RESULT', 'Average Result', 2, '% blend');
}

class RecordMath {
   private $system;
   private $records;
   private $totalize;
   private $maximize;
   private $average;

   # A list of fields we were NOT able to find.
   # These are displayed to the user at some point.
   private $warn = [];

   public function __construct ($records, $system) {
      $this->records = $records;
      $this->system = $system;

      $this->unit = $system->get_param_value('Unit') ? 'liter' : 'gallon';
      $this->units = $system->get_param_value('Unit') ? 'liters' : 'gallons';

      $this->totalize = [];
      $this->maximize = [];
      $this->average  = [];
      $this->warn     = [];
   }

   public function print_warnings ($page) {
      if (!count($this->warn)) return;

      $page->begin_section('Warning');

      echo
         '<p>' .
         'These records are being automatically summarized and <strong>some fields are missing</strong>. ' .
         'The summary at the bottom of this page may be <strong>inaccurate or misleading</strong>. ' .
         'The following fields were required but were not in the data:' .
         '</p>';

      # Print out a list of the fields we didn't find
      echo '<ul>';
      foreach ($this->warn as $what) echo "<li>$what</li>";
      echo '</ul>';

      $page->end_section();
   }

   public function get_results_for_everything () {
      # Find our files, and then summarize them all by building a huge list
      # of record data, and processing that.

      $big = new Record();

      foreach ($this->records as $rec) {
         if (empty($big->columns)) $big->columns = $rec->columns;

         $big->rows = array_merge($big->rows, $rec->rows);
      }

      # Now we have one giant record "file" with every single record in it.
      # Do the math on that.
      return $this->get_results_for_record($big);
   }

   public function get_results_for_year_and_month ($year, $month) {
      $record = $this->records->get_by_year_and_month($year, $month);
      if ($record === false) return false;

      return $this->get_results_for_record($record);
   }

   public function get_results_for_record ($record) {
      $result = [];

      $columns = array_flip($record->columns);
      $average_cols = [];

      foreach ($record->rows as $row) {
         # Run totalizers
         foreach ($this->totalize as $col_name => $entry) {
            # If this isn't present, show a warning.
            if (!$record->has_column($col_name)) $this->warn[] = $col_name;
            $col = $columns[$col_name];

            if (!isset($result[$col])) {
               $result[$col] = ['info' => $entry, 'value' => 0.0];
            }

            # Is this a null result? Skip it.
            if (!is_numeric($row[$col])) continue;

            $result[$col]['value'] += (float)($row[$col]);
         }

         # Run maximizers
         foreach ($this->maximize as $col_name => $entry) {
            if (!$record->has_column($col_name)) $this->warn[] = $col_name;
            $col = $columns[$col_name];

            if (!isset($result[$col])) {
               $result[$col] = ['info' => $entry, 'value' => 0.0];
            }

            # Is this a null result? Skip it.
            if (!is_numeric($row[$col])) continue;

            $value = (float)($row[$col]);
            if ($value > $result[$col]['value']) {
               $result[$col]['value'] = $value;
            }
         }

         # Run averagers
         foreach ($this->average as $col_name => $entry) {
            if (!$record->has_column($col_name)) $this->warn[] = $col_name;
            $col = $columns[$col_name];

            if (!isset($result[$col])) {
               $result[$col] = ['info' => $entry, 'value' => 0.0];
               $average_cols[] = $col;
            }

            # Is this a null result? Skip it.
            if (!is_numeric($row[$col])) continue;

            $value = (float)($row[$col]);
            $result[$col]['value'] += $value;
            $result[$col]['count'] += 1;
         }
      }

      foreach ($average_cols as $col) {
         if ($result[$col]['count'] == 0) {
            $result[$col]['value'] = 'N/A';
            break;
         }
         $result[$col]['value'] /= $result[$col]['count'];
      }

      # Collapse the warnings.
      if (count($this->warn)) $this->warn = array_unique($this->warn);

      # Return the results.
      return $result;
   }

   function print_math ($page, $result, $make_section = true) {
      $table = new Table();
      $table->append_attribute('class', 'info-table');
      $table->append_attribute('width', '50%');
      $table->add_style('margin', 'auto');

      $body = new TableBody();

      foreach ($result as $col => $entry) {
         $row = new TableRow();

         $info = $entry['info'];
         $text = $info['text'];
         $suffix = $info['suffix'];
         $precision = isset($info['precision']) ? $info['precision'] : 0;

         $text = new TableCell($text);
         $text->add_style('text-align', 'right');
         $text->append_attribute('width', '50%');

         if (is_numeric($entry['value'])) {
            $value = new TableCell(number_format($entry['value'], $precision) . $suffix);
         }
         else {
            $value = new TableCell('N/A');
         }
         $value->append_attribute('width', '50%');

         $row->add_child($text);
         $row->add_child($value);

         $body->add_child($row);
      }

      $table->add_child($body);

      if ($make_section) $page->begin_section('Summary');
      echo '<a name="summary"></a>';
      echo $table->get_html();
      if ($make_section) $page->end_section();
   }

   public function make_suffix ($suffix) {
      # Unit alone?
      if ($suffix === false) return ' ' . $this->units;

      # Nope, parse away.
      $suffix = str_replace('%unit%', $this->unit, $suffix);
      $suffix = str_replace('%units%', $this->units, $suffix);

      return $suffix;
   }

   public function add_totalizer ($column, $text, $precision = 1, $suffix = false) {
      # Automatic unit?
      $suffix = $this->make_suffix($suffix);

      $this->totalize[$column] = [
         'text' => $text,
         'precision' => $precision,
         'suffix' => $suffix
      ];

      return $this;
   }

   public function add_maximizer ($column, $text, $precision = 1, $suffix = false) {
      # Automatic unit?
      $suffix = $this->make_suffix($suffix);

      $this->maximize[$column] = [
         'text' => $text,
         'precision' => $precision,
         'suffix' => $suffix
      ];

      return $this;
   }

   public function add_averager ($column, $text, $precision = 1, $suffix = false) {
      # Automatic unit?
      $suffix = $this->make_suffix($suffix);

      $this->average[$column] = [
         'text' => $text,
         'precision' => $precision,
         'suffix' => $suffix
      ];

      return $this;
   }
}

if (isset($_POST['submit'])) {
   # Try to get the record they asked for
   $param = $_POST['filename'];
   if ($param === 'manage') {
      # Special page.
      Page::redirect($manage_page);
      #die;
   }
   if ($param === 'calibration') {
      # Special page.
      Page::redirect($calibration_page);
      #die;
   }
   if ($param === 'bio_tank_stats') {
      # Special page.
      Page::redirect($statistics_page . '?bio');
      #die;
   }
   if ($param === 'blend_stats') {
      # Special page.
      Page::redirect($statistics_page . '?blend');
      #die;
   }
   if ($param === 'dsl_tank_stats') {
      # Special page.
      Page::redirect($statistics_page . '?dsl');
      #die;
   }
   $sel_rec = $math_records->get_by_filename($param . '.CSV');
   if ($sel_rec === false) {
      ErrorPage::show('The records you requested do not exist.');
   }
}

# Show a picker form
$filelist = [
   'Record Files' => [],
   'Other Options' => ['manage' => 'Manage All Record Files', 
                       'calibration' => 'View Calibration Records'],
   'Statistics' => ['bio_tank_stats' => 'Additive Tank Statistics',
                    'dsl_tank_stats' => 'Main Tank Statistics',
                    'blend_stats' => 'Blend Statistics']
];

foreach ($math_records as $rec) {
   $info = pathinfo($rec->filename);
   $filelist['Record Files'][$info['filename']] = $rec->year . ' ' . $rec->month_name;
}

$form = new Form($self_math);

if (count($math_records)) {
    $form = new Form('/records/index.php' . (isset($_GET['showdelete']) ? '?showdelete' : ''));
    $left_col = '13em';
 
    $form->add_child(new FormRow(
       'Select an Option',
       new SelectBox('filename', false, $filelist, isset($_POST['filename']) ? $_POST['filename'] : $page_selector),
       $left_col
    ));
 
    $form->add_child(new FormRow(
       '&nbsp;',
       new SubmitButton('submit', false, 'OK'),
       $left_col
    ));
    
}

?>
