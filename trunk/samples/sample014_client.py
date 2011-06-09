#!/usr/bin/python

"""
sample014_client.py
"""

import sys
import logging
from pprint import pprint
from time import sleep

import urllib
import simplejson
from threading import Thread, Lock

from bacpypes.debugging import Logging, ModuleLogger
from bacpypes.consolecmd import ConsoleCmd

from bacpypes.core import run

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# globals
my_cache = {}
cache_lock = None

#
#   MyCacheCmd
#

class MyCacheCmd(ConsoleCmd, Logging):

    def do_dump(self, arg):
        """dump - nicely print the cache"""
        if _debug: MyCacheCmd._debug("do_dump %r", arg)

        cache_lock.acquire()
        pprint(my_cache)
        cache_lock.release()

    def do_set(self, arg):
        """set <key> <value> - change a cache value"""
        if _debug: MyCacheCmd._debug("do_set %r", arg)

        key, value = arg.split()

        cache_lock.acquire()
        my_cache[key] = value
        cache_lock.release()

    def do_del(self, arg):
        """del <key> - delete a cache entry"""
        if _debug: MyCacheCmd._debug("do_del %r", arg)

        try:
            cache_lock.acquire()
            del my_cache[arg]
            cache_lock.release()
        except:
            print arg, "not in cache"

#
#   MyCacheThread
#

class MyCacheThread(Thread, Logging):

    def __init__(self):
        if _debug: MyCacheThread._debug("__init__")
        Thread.__init__(self, name="MyCacheThread")

        # daemonic
        self.daemon = True

        # start the thread
        self.start()

    def run(self):
        if _debug: MyCacheThread._debug("run")

        while True:
            sleep(5)

            try:
                urlfile = urllib.urlopen("http://localhost:9090/")
                cache_update = simplejson.load(urlfile)
                if _debug: MyCacheThread._debug("    - cache_update: %r", cache_update)

                cache_lock.acquire()
                my_cache.update(cache_update)
                cache_lock.release()

                urlfile.close()
            except Exception, err:
                sys.stderr.write("[exception %r]\n" % (err,))

#
#   __main__
#

try:
    _log.debug("initialization")

    # create a lock for the cache
    cache_lock = Lock()

    # console
    MyCacheCmd()

    # cache update thread
    MyCacheThread()

    _log.debug("running")

    # run until stopped
    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")
