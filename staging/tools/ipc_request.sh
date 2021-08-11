#!/bin/sh

# Makes a request to the interprocess communication system via the
# command line.

[ -z "$1" ] && exit 1
echo {\"request_type\": \"$1\"} | nc -w 3 localhost 3737

