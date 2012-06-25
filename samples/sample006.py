#!/usr/bin/python

"""
sample006.py

    This sample application has just a network stack, not a full application,
    and is a way to enter InitializeRoutingTable and WhoIsRouterToNetwork requests.
    To see the npdu's, attach a debugger to the NSE class.

    $ python sample006.py --debug bacpypes.netservice.NetworkServiceElement
"""

import sys
import logging

from ConfigParser import ConfigParser

from bacpypes.debugging import Logging, ModuleLogger
from bacpypes.consolelogging import ConsoleLogHandler
from bacpypes.consolecmd import ConsoleCmd

from bacpypes.core import run

from bacpypes.pdu import Address
from bacpypes.npdu import InitializeRoutingTable, WhoIsRouterToNetwork
from bacpypes.app import BIPNetworkApplication

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# reference a network application
thisApplication = None

#
#   TestConsoleCmd
#

class TestConsoleCmd(ConsoleCmd, Logging):

    def do_irt(self, args):
        """irt <addr>"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_irt %r", args)

        try:
            # build a request
            request = InitializeRoutingTable()
            request.pduDestination = Address(args[0])

            # give it to the application
            thisApplication.request(thisApplication.nsap.adapters[0], request)

        except Exception, e:
            print e.__class__, ":", e

    def help_irt(self):
        print self.do_irt.__doc__

    #-----

    def do_wirtn(self, args):
        """wirtn <addr> [ <net> ]"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_irt %r", args)

        try:
            # build a request
            request = WhoIsRouterToNetwork()
            request.pduDestination = Address(args[0])
            if (len(args) > 1):
                request.wirtnNetwork = int(args[1])

            # give it to the application
            thisApplication.request(thisApplication.nsap.adapters[0], request)

        except Exception, e:
            print e.__class__, ":", e

    def help_wirtn(self):
        print self.do_wirtn.__doc__

#
#   __main__
#

try:
    if ('--buggers' in sys.argv):
        loggers = logging.Logger.manager.loggerDict.keys()
        loggers.sort()
        for loggerName in loggers:
            sys.stdout.write(loggerName + '\n')
        sys.exit(0)

    if ('--debug' in sys.argv):
        indx = sys.argv.index('--debug')
        for i in range(indx+1, len(sys.argv)):
            ConsoleLogHandler(sys.argv[i])
        del sys.argv[indx:]

    _log.debug("initialization")

    # read in a configuration file
    config = ConfigParser()
    if ('--ini' in sys.argv):
        indx = sys.argv.index('--ini')
        ini_file = sys.argv[indx + 1]
        if not config.read(ini_file):
            raise RuntimeError, "configuration file %r not found" % (ini_file,)
        del sys.argv[indx:indx+2]
    elif not config.read('BACpypes.ini'):
        raise RuntimeError, "configuration file not found"

    # get the address from the config file
    addr = config.get('BACpypes', 'address')

    # maybe use a different port
    if '--port' in sys.argv:
        i = sys.argv.index('--port')
        addr += ':' + sys.argv[i+1]
    _log.debug("    - addr: %r", addr)

    # make a simple application
    thisApplication = BIPNetworkApplication(addr)
    TestConsoleCmd()

    _log.debug("running")

    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")
