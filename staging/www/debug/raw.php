<?php
header('Content-Type: text/plain');
readfile('/dev/shm/log.txt');
?>
