<?php

require('main.php');

$ipc = new Ipc();
header('Content-Type: text/plain; charset=utf-8');

if (file_exists('/run/shm/no-sync')) {
   # End immediately
   echo '{"error": true}' . $end_message;
   die;
}

$data = $ipc->request(['request_type' => 'get_display_and_indicators'], false);
echo $data;

?>
