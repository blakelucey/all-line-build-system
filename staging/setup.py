# All-Line Equipment Company
# Remote management software setup script

import os
import sys
import shutil

to_dir = '/config'

# Create cron directory
try:
   os.mkdir(to_dir + '/cron')
   os.chmod(to_dir + '/cron', 0777)
except OSError:
   pass

# Create records directory
try:
   os.mkdir(to_dir + '/records')
   os.chmod(to_dir + '/records', 0777)
except OSError:
   pass

# Set up cron
with open(to_dir + '/cron/root', 'w') as f:
   f.flush()
os.chmod(to_dir + '/cron/root', 0777)

# Set up the event log
with open(to_dir + '/events.cfg', 'w') as f:
   f.write('{"text": "System was initialized successfully from a blank installation medium.", "kind": "System", "time": "1970-01-01T00:00:00"}\r\n')
   f.flush()
os.chmod(to_dir + '/events.cfg', 0777)

# Set up web users
with open(to_dir + '/web-users.cfg', 'w') as f:
   f.write(
'''{"users": [
        {
            "real_name": "All-Line Equipment",
            "username": "all-line",
            "permissions": [
                "update",
                "admin"
            ],
            "password_hash": "bcdde72f8ffad157876b170249033f34e83b55b7"
        },
        {
            "real_name": "User",
            "username": "user",
            "permissions": [],
            "password_hash": "da39a3ee5e6b4b0d3255bfef95601890afd80709"
        }
    ]
}''')
   f.flush()
os.chmod(to_dir + '/web-users.cfg', 0777)

with open(to_dir + '/reporting.cfg', 'w') as f:
   f.write(
'''{
    "all_line_smtp": true,
    "server": "",
    "port": 0,
    "username": "",
    "alert": {
        "enabled": false,
        "recipients": [],
        "text": ""
    },
    "reporting": {
        "enabled": false,
        "limit": false,
        "recipients": [],
        "text": "",
        "when": "23:55"
    },
    "statistics": {
        "min_bio_tank_reading": 10.0,
        "min_bio_tank_reading_stats": 10.0,
        "bio_error_ignore": 0.2,
        "bio_error_warn": 0.1,
        "max_bad_bio_records": 3,
        "min_dsl_tank_reading": 10.0,
        "min_dsl_tank_reading_stats": 10.0,
        "dsl_error_ignore": 0.2,
        "dsl_error_warn": 0.1,
        "max_bad_dsl_records": 3,
        "min_blend_tank_reading": 10.0,
        "min_blend_tank_reading_stats": 10.0,
        "blend_error_ignore": 0.2,
        "blend_error_warn": 0.1,
        "max_bad_blend_records": 3,
        "diesel_tanks": []
    },
    "password": ""
}''')
   f.flush()
os.chmod(to_dir + '/reporting.cfg', 0777)

sys.exit(0)

