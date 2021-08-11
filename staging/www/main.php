<?php

# helpful debugging print function
function print_var($var) {
   echo '<pre>';
   var_dump($var); 
   echo '</pre>';
}

# Time zone
$tz = realpath('/etc/TZ');
if ($tz !== false) {
   $tz = explode('/', $tz);
   $zi = array_search('zoneinfo', $tz);
   if ($zi !== false) {
      # We parsed the timezone correctly
      $tz = implode('/', array_slice($tz, $zi + 2));
      date_default_timezone_set($tz);
   }
}

# Wrapper for POST variables
function get_post ($key, $default = '', $sub = null) {
   if ($sub === null) {
      # Get the post value.
      if (isset($_POST[$key])) {
         return trim($_POST[$key]);
      }
      else {
         return $default;
      }
   }
   else {
      # Get a subkey of the post value.
      if (isset($_POST[$key][$sub])) {
         return trim($_POST[$key][$sub]);
      }
      else {
         return $default;
      }
   }
}

# We run in a directory called 'www', which is a sibling of other paths
# that we need to reach.
$root_path = null;

function find_root () {
   global $root_path;
   if ($root_path !== null) return $root_path;

   $dir = dirname($_SERVER['PHP_SELF']);

   # Adjust for subdirectories
   if ($dir !== '/') {
      $prefix = str_repeat('../', substr_count($dir, '/'));
   } else {
      $prefix = './';
   }

   $root_path = $prefix;
   return $root_path;
}

function __autoload ($class) {
   $class = strtolower($class);

   $prefix = find_root();
   $filename = $prefix . "classes/$class.class.php";
   require($filename);
}

function get_path ($type) {
   $root_path = find_root();
   $root_path = substr($root_path, 0, -1);

   $root_path = '../' . $root_path;

   $paths = [
      'temp' => '/dev/shm',
      'logs' => '/dev/shm/',
      'config' => '/config/',
      'www' => $root_path . '/www/',
      'images' => $root_path . '/images/',
      'records' => '/config/records/',
      'program' => '/program/',
      'tools' => '/program/tools/'
   ];

   return $paths[$type];
}

function validate_hostname ($hostname) {
   if (preg_match('/^(([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z0-9]|[A-Za-z0-9][A-Za-z0-9\-]*[A-Za-z0-9])$/', $hostname) !== 1) {
      return false;
   }
   return true;
}

function is_old_ie () {
   return preg_match('/(?i)msie [2-8]/i', @$_SERVER['HTTP_USER_AGENT']);
}

function is_edge () {
   return preg_match('/(?i)edge\//i', @$_SERVER['HTTP_USER_AGENT']);
}

function format_size ($s, $p = 2) {
   $base = log($s) / log(1024);
   $suf = array('bytes', 'kB', 'MB', 'GB', 'TB');
   $suffix = $suf[floor($base)];
   if (floor($base) < 1) $p = 0;
   return number_format(round(pow(1024, $base - floor($base)), $p), $p) . ' ' . $suffix;
}

?>
