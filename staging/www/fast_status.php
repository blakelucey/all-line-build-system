<?php

require('main.php');

ini_set('zlib.output_compression', 'Off');
ini_set('output_buffering', 'Off');
ini_set('output_handler', '');
ignore_user_abort(false);
ob_implicit_flush(true);
ob_end_flush();

header('Content-Type: text/event-stream; charset=utf-8');

$ipc = new Ipc();
$end_message = "\n\n";

if (file_exists('/dev/shm/no-sync')) {
   # Stop
   echo '{"status": false}' . $end_message;
   die;
}

# Ten minutes of streaming data
for ($samples = 0; $samples < 60 * 10; $samples++) {
   $data = trim($ipc->raw_request('<request type="status"><action>get</action></request>'));
   echo 'data: ' . $data . $end_message;
   flush();
   ob_flush();

   usleep(1000 * 1000);
}

echo $end_message . $end_message;

?>
