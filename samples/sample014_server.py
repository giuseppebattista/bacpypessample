#!/usr/bin/python

"""
sample014_server.py
"""

from random import seed, choice, uniform
from time import time as _time

import SocketServer
import SimpleHTTPServer
import simplejson

# globals
varNames = [
    "spam",
    "eggs",
    ]

#
#   ValueServer
#

class ValueServer(SimpleHTTPServer.SimpleHTTPRequestHandler):

    def do_GET(self):
        cache_update = {choice(varNames): uniform(0, 100)}
        simplejson.dump(cache_update, self.wfile)

#
#   __main__
#

try:
    seed(_time())
    httpd = SocketServer.TCPServer(('', 9090), ValueServer)
    httpd.serve_forever()
except KeyboardInterrupt:
    pass
