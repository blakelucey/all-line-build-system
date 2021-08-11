#!/bin/sh

LOG=/config/watchdog.txt
OLDLOG=/config/watchdog.old
OLDLOG2=/config/watchdog.older
FAILS=0
>$LOG
echo `date` Watchdog started. > $LOG

check_fail () {
   FAILS=$(($FAILS + 1))
   echo `date` Failure count is now $FAILS. >> $LOG
   if [ $FAILS -gt 5 ]; then
      echo `date` 'Watchdog detected system instability ('$FAILS' failures)' >> $LOG
      echo `date` Watchdog is rebooting. >> $LOG
      echo `date` Final report: `uptime` >> $LOG
      if [ -f $OLDLOG ]; then
         cp $OLDLOG $OLDLOG2
      fi
      cp $LOG $OLDLOG
      reboot
   fi
}

restart_server () {
   /etc/init.d/S50lighttpd restart
}

restart_monitor () {
   # The init.d monitor script restarts us as well, so just
   # run the python script directly
   if [ -f /program/main.pyc ] ; then
      python -B /program/main.pyc
   else
      python -B /program/main.py
   fi
}

while true; do
   sleep 5s
   if ! pidof lighttpd > /dev/null; then
      # Web server has stopped; stop the Bioblender service and reboot quickly
      echo `date` lighttpd is not running. Restarting. >> $LOG
      check_fail
      restart_server
   fi
   if ! pidof python > /dev/null; then
      # Monitor service has stopped; do the same
      echo `date` tank monitor is not running. Restarting. >> $LOG
      check_fail
      restart_monitor
   fi
done

