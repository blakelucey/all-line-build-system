<?php

class Record implements Countable {
   public $filename;
   public $columns = [];
   public $rows = [];
   public $month;
   public $file_size = 0;
   public $month_name;
   public $month_abbr;
   public $year;

   public function has_column ($id) {
      return in_array($id, $this->columns);
   }

   public function count () {
      return count($this->rows);
   }

   public function get_short_filename () {
      $info = pathinfo($this->filename);
      return $info['basename'];
   }

   public function get_short_filename_no_extension () {
      $info = pathinfo($this->filename);
      return $info['filename'];
   }

   public function delete ($ipc, $login) {
      # Try to delete this file by asking Python to do it.
      $ipc->request([
         'request_type' => 'delete_record_file',
         'file' => $this->get_short_filename(),
         'month' => $this->month_name,
         'year' => $this->year,
         'user' => $login->get_user()->get_real_name()
      ]);
   }
}

class RecordFiles implements Iterator, ArrayAccess, Countable {
   private $injector;
   private $file_list = [];
   private $record_list = [];
   private $ptr = 0;

   const record_path = '/config/records/';

   public function __construct ($injector) {
      $this->injector = $injector;

      $this->file_list = $this->build_list();
      $this->fetch_records();
   }

   private function fetch_file ($filename) {
      $handle = fopen($filename, 'r');
      if (!$handle) return;

      $cols = [];
      $index = 0;
      while (!feof($handle)) {
         $data = fgetcsv($handle);
         if (!$data || count($data) < 2) continue;

         $cols[$index] = $data;
         $index += 1;
      }

      fclose($handle);

      # Move these into a record
      $rec = new Record();
      $rec->filename = $filename;

      # Grab the headers.
      $fh = fopen(self::record_path . '../headers.txt', 'r');
      $rec->columns = fgetcsv($fh);
      fclose($fh);

      # For each header that is blank, skip that column.
      $shown_columns = [];
      foreach ($rec->columns as $index => $head) {
         if ($head != '--') {
            $shown_columns[] = $index;
         }
      }

      # Then strip those away from the headers.
      $original = $rec->columns;
      $rec->columns = [];
      foreach ($shown_columns as $i) {
         $rec->columns[] = $original[$i];
      }

      # Then, import the data, ignoring those columns.
      for ($i = 0; $i < count($cols); $i++) {
         $rec->rows[$i - 1] = [];
         # Previous loop: foreach ($cols[$i] as $c => $col) {
         foreach ($shown_columns as $c) {
            $col = $cols[$i][$c];
            $rec->rows[$i - 1][$c] = $col;
         }
      }

      $this->record_list[] = $rec;

      # Grab the file size.
      $rec->file_size = filesize($filename);

      # Try to figure out the month and year.
      # I can probably use PHP's built-in stuff for this but hey.
      $months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
      $months_long = [
         'January', 'February', 'March', 'April', 'May',
         'June', 'July', 'August', 'September', 'October',
         'November', 'December'
      ];

      $info = pathinfo($filename);
      $name = $info['basename'];
      $month_text = substr($name, 0, 3);
      $year_text = substr($name, 4, 4);
      $rec->month = array_search(strtolower($month_text), $months) + 1;
      $rec->month_name = $months_long[$rec->month - 1];
      $rec->month_abbr = $months[$rec->month - 1];
      $rec->year = (int)$year_text;
   }

   public function get_by_year_and_month ($year, $month) {
      foreach ($this->record_list as $rec) {
         if ($rec->year == $year && $rec->month == $month) return $rec;
      }

      return false;
   }

   public function get_by_filename ($filename) {
      if ($filename === null) return false;

      foreach ($this->record_list as $rec) {
         if (substr($rec->filename, -strlen($filename)) == $filename) return $rec;
      }

      return false;
   }

   private function fetch_records () {
      foreach ($this->file_list as $name => $file) {
         $this->fetch_file($file);
      }
   }

   private function add_path (&$list, $path) {
      if (substr($path, -1) != '/') $path .= '/';
      $dir = opendir($path);
      if (!$dir) return;

      while (($filename = readdir($dir)) !== false) {
         if ($filename == '.' || $filename == '..') continue;

         $info = pathinfo($path . $filename);
         if (!$info) continue;
         if (strtolower($info['extension']) != 'csv') continue;

         # This is a file we want
         $list[] = $path . $filename;
      }

      closedir($dir);
   }

   private function build_list () {
      $months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];

      $compare = function ($a, $b) {
         $a_info = pathinfo($a);
         $a_name = $a_info['basename'];
         $a_month_text = substr($a_name, 0, 3);
         $a_year_text = substr($a_name, 4, 4);

         $b_info = pathinfo($b);
         $b_name = $b_info['basename'];
         $b_month_text = substr($b_name, 0, 3);
         $b_year_text = substr($b_name, 4, 4);

         $a_date = strtotime("$a_month_text $a_year_text");
         $b_date = strtotime("$b_month_text $b_year_text");

         # Reverse sort (most recent first)
         return $b_date - $a_date;
      };

      $paths = [
         self::record_path
      ];

      $result = [];
      foreach ($paths as $path) {
         $this->add_path($result, $path);
      }

      usort($result, $compare);

      return $result;
   }

   public function get_latest_file () {
      return $this->get_by_year_and_month((int)date('Y'), (int)date('m'));
   }

   public function current () {
      return $this->record_list[$this->ptr];
   }

   public function key () {
      return $this->ptr;
   }

   public function next () {
      $this->ptr++;
   }

   public function rewind () {
      $this->ptr = 0;
   }

   public function valid () {
      return isset($this->record_list[$this->ptr]);
   }

   public function offsetExists ($offset) {
      return $offset >= 0 && $offset < count($this->record_list);
   }

   public function offsetGet ($offset) {
      return $this->record_list[$offset];
   }

   public function offsetSet ($offset, $new_value) {
   }

   public function offsetUnset ($offset) {
   }

   public function count () {
      return count($this->record_list);
   }
}

?>
