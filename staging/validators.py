# All-Line Equipment Company

# Validators for common types of data.
# 'key' is not used in many of these, but is required for using these
# directly with the Configurable.validators interface.

# Validators return a tuple containing:
#  success, message
# where
#  success: True if the value is acceptable, False otherwise
#  message: The text of the error, if one occurred

import time

def validate_email (key, value, args = {}):
   return ('@' in value and ' ' not in value), 'Invalid email address.'

def validate_emails (key, values, args = {}):
   if 'limit' in args and len(values) > args['limit']:
      return (False, 'Too many addresses; the limit is {}.'.format(args['limit']))

   for addr in values:
      ok, message = validate_email(key, addr)
      if not ok:
         return (False, 'One or more email address are invalid.')

   return (True, '')

def validate_time (key, value, args = {}):
   try:
      time.strptime(value, '%H:%M')
   except ValueError:
      return (False, 'Invalid time. Must be HH:MM, in 24-hour format.')
   return (True, '')

def validate_int (key, value, args = {}):
   try:
      ivalue = int(value)
      minval = args.get('minimum', None)
      maxval = args.get('maximum', None)
      if minval is not None and maxval is not None:
         if ivalue < minval or ivalue > maxval:
            return (False, 'Invalid value; range is {}-{}, inclusive.'.format(minval, maxval))
   except ValueError:
      return (False, 'Invalid value.')
   return (True, '')

def validate_float (key, value, args = {}):
   try:
      ivalue = float(value)
      minval = args.get('minimum', None)
      maxval = args.get('maximum', None)
      if minval is not None and maxval is not None:
         if ivalue < minval or ivalue > maxval:
            return (False, 'Invalid value; range is {}-{}, inclusive.'.format(minval, maxval))
   except ValueError:
      return (False, 'Invalid value.')
   return (True, '')

def validate_ints (key, values, args = {}):
   for val in values:
      ok, message = validate_int(key, val)
      if not ok:
         return (ok, message)
   return (True, '')

def validate_hostname (key, value, args = {}):
   # This isn't great but it's good enough. Hostnames are awfully difficult
   # to validate. They can also be IP addresses, which presents its own challenge.
   if ' ' in value: return (False, 'Spaces are invalid in host names.')
   return (True, '')

