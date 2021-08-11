<?php

/* AnsiUp: client-side based ANSI highlighting
$text = @file_get_contents('/dev/shm/logs/log.txt');
$text = str_replace("\n", "<br />", $text);

echo '<html><head><title>Debug Log</title><style type="text/css">body {background: black; font-family: monospace}</style></head><body>';
echo '<script type="text/javascript" src="/scripts/ansi_up.js"></script>';
echo '<script type="text/javascript">var text = \'' . $text . '\'; var ansi_up = new AnsiUp(); document.write(ansi_up.ansi_to_html(text));</script>';

die;
*/

$logfile = '/dev/shm/log.txt';
$lines = @file($logfile);
$tail = 250;

if (isset($_GET['tail']) && is_numeric($_GET['tail'])) {
   $tail = (int)$_GET['tail'];
}

if (isset($_GET['full'])) {
   $tail = false;
}

if ($tail !== false) {
   $lines = array_splice($lines, -$tail);
}

$colors = [
   '[30m' => 'black',
   '[31m' => 'darkred',
   '[32m' => 'green',
   '[33m' => 'brown',
   '[34m' => 'mediumblue',
   '[35m' => 'purple',
   '[36m' => 'darkcyan',
   '[37m' => 'lightgray',

   '[30;0m' => 'black',
   '[31;0m' => 'darkred',
   '[32;0m' => 'green',
   '[33;0m' => 'brown',
   '[34;0m' => 'mediumblue',
   '[35;0m' => 'purple',
   '[36;0m' => 'darkcyan',
   '[37;0m' => 'lightgray',

   '[30;1m' => 'gray',
   '[31;1m' => 'red',
   '[32;1m' => 'limegreen',
   '[33;1m' => 'yellow',
   '[34;1m' => 'deepskyblue',
   '[35;1m' => 'magenta',
   '[36;1m' => 'cyan',
   '[37;1m' => 'white',

   '[0m' => 'lightgray'
];

echo '<html><head><title>Debug Log</title><style type="text/css">body {background: black; font-family: monospace} a:link, a:visited {color: yellow}</style></head><body>';

# Maybe someday!
#echo '<p style="color: white; padding: 1em; border: 1px solid green;">';
#echo 'Click <a href="/debug/?send">here</a> to send this log to the developers at All-Line Equipment.';
#echo '</p>';

$size = (int)(filesize($logfile) / 1024) . ' KB';
echo '<p style="color: white; padding: 1em; border: 1px solid green;">';
if ($tail !== false) {
   echo 'The debug log has been clipped to ' . $tail . ' entries. To see the full log, ';
   echo 'click <a href="/debug/?full">here</a>. ';
}
echo 'For systems that have been up for a long time, ';
echo 'this may be slow to load. Log file size is ' . $size . '.</p>';

$start_time = microtime(true);
if ($lines === false) {
   echo '<p style="color: white; padding: 1em; border: 3px solid green;">No log file.</p>';
   $lines = [];
}
foreach ($lines as $line) {
   # Parse some basic ANSI codes
   echo '<span style="color: crimson">';
   $last_color = null;
   $prev = '';
   $color = '';
   for ($i = 0; $i < strlen($line); $i++) {
      if ($line[$i] == chr(0x1b)) {
         # ANSI code; some codes include a brightness qualifier, but all color codes
         # end with an ASCII 'm'.
         $end_of_code = strpos($line, 'm', $i + 1);
         $color_code = substr($line, $i + 1, $end_of_code - $i);
         if (array_key_exists($color_code, $colors)) {
            $color = $colors[$color_code];
            if ($last_color != $color) {
               echo "</span><span style=\"color: $color\">";
            }
            $i = $end_of_code;
            $last_color = $color;
         }
      }
      else {
         # Not ansi code
         if ($line[$i] == '<') {
            echo '&lt;';
         }
         else if ($line[$i] == '>') {
            echo '&gt;';
         }
         else {
            echo ($prev == ' ' && $line[$i] == ' ') ? '&nbsp;' : $line[$i];
            $prev = $line[$i];
         }
      }
   }
   echo '</span><br />';
}
$total = microtime(true) - $start_time;
if ($tail === false) {
   $dur = number_format($total, 2, '.', '') . ' seconds';
   echo '<p style="color: white; padding: 1em; border: 1px solid green;">This colorful log took ' . $dur . ' to generate.</p>';
}
echo '</body>';

?>
