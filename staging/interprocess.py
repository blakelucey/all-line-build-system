# All-Line Equipment Company
# Interprocess Communication Server

import os
import sys
import time
import socket
import select
import json

from logger import *

class RemoteHaltRequest (Exception):
   '''Raised when the system receives a request to stop.'''
   pass

class InterprocessReplier:
   '''Wraps a socket in some helper methods for sending JSON data.'''

   def __init__ (self, skt):
      self.skt = skt

   def send (self, data, json_encoding = 'utf-8'):
      # Encode this as JSON, if possible.
      # Make sure there's always an error indicator.
      if 'error' not in data:
         data['error'] = False

      try:
         data = json.dumps(data, encoding = json_encoding).strip()
      except UnicodeDecodeError:
         # Something in the data is not appreciated by Python's JSON encoder.
         if 'param_name' in data:
            # We can report a bit more information about this error.
            self.error('Unable to encode JSON object for parameter {}.'.format(data['param_name']))
         else:
            self.error('Unable to encode JSON object.')
         return

      self.skt.send(data + '\r\n')

   def error (self, message = None):
      data = {'error': True}
      if message is not None:
         data['message'] = message
         log_info('Interprocess reply error: {}'.format(message))
      self.send(data)

   def get_socket (self):
      return self.skt

class InterprocessServer:
   def __init__ (self):
      self.address = '0.0.0.0'
      self.port = 3737

      self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
      self.socket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
      self.socket.bind((self.address, self.port))
      self.socket.setblocking(False)
      self.socket.listen(100)

      self.input = [self.socket]
      self.is_busy = False
      self.allowed_requests = []
      self.handlers = {}

   def close (self):
      for skt in self.input:
         try:
            skt.close()
         except Exception as e:
            log_info('Exception thrown during socket closure: {}'.format(e))
            continue

      try:
         self.socket.close()
      except Exception as e:
         log_info('Exception thrown during listening socket closure: {}'.format(e))

   def add_handler (self, request_type, callback):
      if request_type not in self.handlers:
         self.handlers[request_type] = [callback]
      else:
         self.handlers[request_type].append(callback)

      log_debug('Added request type "{}".'.format(request_type))

   def remove_handler (self, request_type, callback):
      if request_type not in self.handlers:
         return

      self.handlers[request_type].remove(callback)

   def busy (self, allowed_requests = []):
      '''Set the IPC interface to reply "busy" to all requests except those provided.'''
      self.allowed_requests = allowed_requests
      self.is_busy = True

   def not_busy (self):
      self.is_busy = False
      self.allowed_requests = []

   def poll (self):
      inready, outready, exready = select.select(self.input, [], [], 0)

      for s in inready:
         if s == self.socket:
            # A client wants to connect. We can accept this.
            client, address = self.socket.accept()
            self.input.append(client)

         else:
            # A client is sending us data.
            try:
               data = s.recv(4096, socket.MSG_DONTWAIT)

               if data:
                  self.dispatch(s, data)
               else:
                  s.close()
                  self.input.remove(s)
            except socket.error:
               s.close()
               self.input.remove(s)

   def dispatch (self, skt, request, is_json = True):
      # Does this request need converted from JSON?
      if is_json:
         try:
            data = json.loads(request)
         except:
            # Catch all exceptions; there's tons of them that loads() can throw.
            log_info('Invalid request on IPC server.')
            replier = InterprocessReplier(skt)
            replier.error('Invalid request data.')
            return
      else:
         data = request

      # Are there multiple incoming commands? 'data' will be a list, if so.
      if isinstance(data, list):
         for each in data:
            self.dispatch(skt, each, is_json = False)
         return

      # Extract the request type
      if not 'request_type' in data:
         log_info('Valid request on IPC server, but request_type is missing.')
         replier = InterprocessReplier(skt)
         replier.error('Missing request type.')
         return

      request_type = data['request_type']
      if request_type not in self.handlers:
         log_info('Valid request on IPC server, but no handler for {}.'.format(request_type))
         replier = InterprocessReplier(skt)
         replier.error('No handler for request type {}.'.format(request_type))
         return

      # Are we busy? If so, we can't handle this unless it's in the allowed list.
      if self.is_busy and request_type not in self.allowed_requests:
         replier = InterprocessReplier(skt)
         replier.error('The system is busy and cannot process this request.')
         return

      for handler in self.handlers[request_type]:
         # Pass ourselves to the handler, as well as the socket and data.
         handler(InterprocessReplier(skt), data)

