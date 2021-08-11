<?php

require('main.php');

$ipc = new Ipc();
if (isset($_GET['k'])) {
   if (!isset($_GET['q'])) die;
   $result = $ipc->request(['request_type' => 'get_param', 'param_name' => 'Password']);
   if (!$result) die;
   if ((int)$_GET['q'] !== (int)$result['param_value']) die;
   $ipc->request(['request_type' => 'push_key', 'key' => $_GET['k']]);
   die;
}
else if (isset($_GET['t'])) {
   if (!isset($_GET['q'])) die;
   $result = $ipc->request(['request_type' => 'get_param', 'param_name' => 'Password']);
   if (!$result) die;
   if ((int)$_GET['q'] !== (int)$result['param_value']) die;
   $v = ((int)($ipc->request(['request_type' => 'get_param', 'param_name' => 'Remote Enable']))['param_value']);
   $ipc->request(['request_type' => 'set_param', 'param_name' => 'Remote Enable', 'param_value' => ($v) ? 0 : 1]);
   die;
}

@ini_set('zlib.output_compression', 'Off');
@ini_set('output_buffering', 'Off');
@ini_set('output_handler', '');
ignore_user_abort(false);

header('Content-Type: text/event-stream; charset=utf-8');

$end_line = "\n";
$end_message = "\n\n";

if (file_exists('/run/shm/no-sync')) {
   # End immediately
   echo '{"error": true}' . $end_message;
   die;
}

while (true) {
   $data = $ipc->request(['request_type' => 'get_display_and_indicators'], false);

   echo 'data: ' . $data . $end_message;
   flush();
   ob_flush();

   usleep(1000 * 500);
}

?>
