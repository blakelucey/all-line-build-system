import sys

log_file = '/dev/shm/debug_log.txt'

def log_debug(message):
    global log_file
    sys.stdout = open(log_file, 'a')
    print(message)
    sys.stdout.close()