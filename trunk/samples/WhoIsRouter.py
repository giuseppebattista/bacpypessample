#!/usr/bin/python

"""
This sample application has just a network stack, not a full application,
and is a way to create InitializeRoutingTable and WhoIsRouterToNetwork requests.
"""

from bacpypes.debugging import bacpypes_debugging, ModuleLogger
from bacpypes.consolelogging import ConfigArgumentParser
from bacpypes.consolecmd import ConsoleCmd

from bacpypes.core import run

from bacpypes.pdu import Address
from bacpypes.npdu import InitializeRoutingTable, WhoIsRouterToNetwork
from bacpypes.app import BIPNetworkApplication

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# globals
this_application = None
this_console = None

#
#   WhoIsRouterApplication
#

@bacpypes_debugging
class WhoIsRouterApplication(BIPNetworkApplication):

    def __init__(self, *args):
        if _debug: WhoIsRouterApplication._debug("__init__ %r", args)
        BIPNetworkApplication.__init__(self, *args)

        # keep track of requests to line up responses
        self._request = None

    def request(self, adapter, npdu):
        if _debug: WhoIsRouterApplication._debug("request %r %r", adapter, npdu)

        # save a copy of the request
        self._request = npdu

        # forward it along
        BIPNetworkApplication.request(self, adapter, npdu)

    def indication(self, adapter, npdu):
        if _debug: WhoIsRouterApplication._debug("indication %r %r", adapter, npdu)
        BIPNetworkApplication.indication(self, adapter, npdu)

    def response(self, adapter, npdu):
        if _debug: WhoIsRouterApplication._debug("response %r %r", adapter, npdu)
        BIPNetworkApplication.response(self, adapter, npdu)

    def confirmation(self, adapter, npdu):
        if _debug: WhoIsRouterApplication._debug("confirmation %r %r", adapter, npdu)
        BIPNetworkApplication.confirmation(self, adapter, npdu)

#
#   WhoIsRouterConsoleCmd
#

@bacpypes_debugging
class WhoIsRouterConsoleCmd(ConsoleCmd):

    def do_irt(self, args):
        """irt <addr>"""
        args = args.split()
        if _debug: WhoIsRouterConsoleCmd._debug("do_irt %r", args)

        # build a request
        request = InitializeRoutingTable()
        request.pduDestination = Address(args[0])

        # give it to the application
        this_application.request(this_application.nsap.adapters[0], request)

    def do_wirtn(self, args):
        """wirtn <addr> [ <net> ]"""
        args = args.split()
        if _debug: WhoIsRouterConsoleCmd._debug("do_irt %r", args)

        # build a request
        request = WhoIsRouterToNetwork()
        request.pduDestination = Address(args[0])
        if (len(args) > 1):
            request.wirtnNetwork = int(args[1])

        # give it to the application
        this_application.request(this_application.nsap.adapters[0], request)

#
#   __main__
#

try:
    # parse the command line arguments
    args = ConfigArgumentParser(description=__doc__).parse_args()

    if _debug: _log.debug("initialization")
    if _debug: _log.debug("    - args: %r", args)

    # make a simple application
    this_application = WhoIsRouterApplication(args.ini.address)
    if _debug: _log.debug("    - this_application: %r", this_application)

    # make a console
    this_console = WhoIsRouterConsoleCmd()
    if _debug: _log.debug("    - this_console: %r", this_console)

    _log.debug("running")

    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")
