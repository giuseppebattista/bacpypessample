#!/usr/bin/python

"""
sample005.py
"""

import sys
import logging

from ConfigParser import ConfigParser

from bacpypes.debugging import Logging, ModuleLogger
from bacpypes.consolelogging import ConsoleLogHandler
from bacpypes.consolecmd import ConsoleCmd

from bacpypes.core import run

from bacpypes.pdu import Address, GlobalBroadcast
from bacpypes.app import BIPSimpleApplication
from bacpypes.object import get_object_class, get_datatype, LocalDeviceObject

from bacpypes.apdu import WhoIsRequest, IAmRequest, ReadPropertyRequest, Error, AbortPDU, ReadPropertyACK
from bacpypes.constructeddata import Array, Any

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# reference a simple application
thisApplication = None

#
#   TestApplication
#

class TestApplication(BIPSimpleApplication, Logging):

    def request(self, apdu):
        if _debug: TestApplication._debug("request %r", apdu)

        # save a copy of the request
        self._request = apdu

        # forward it along
        BIPSimpleApplication.request(self, apdu)

    def confirmation(self, apdu):
        if _debug: TestApplication._debug("confirmation %r", apdu)

        if isinstance(apdu, Error):
            sys.stdout.write("error: %s\n" % (apdu.errorCode,))
            sys.stdout.flush()

        elif isinstance(apdu, AbortPDU):
            apdu.debug_contents()

        elif (isinstance(self._request, ReadPropertyRequest)) and (isinstance(apdu, ReadPropertyACK)):
            # find the datatype
            datatype = get_datatype(apdu.objectIdentifier[0], apdu.propertyIdentifier)
            TestApplication._debug("    - datatype: %r", datatype)
            if not datatype:
                raise TypeError, "unknown datatype"

            # special case for array parts, others are managed by cast_out
            if issubclass(datatype, Array) and (apdu.propertyArrayIndex is not None):
                if apdu.propertyArrayIndex == 0:
                    value = apdu.propertyValue.cast_out(Unsigned)
                else:
                    value = apdu.propertyValue.cast_out(datatype.subtype)
            else:
                value = apdu.propertyValue.cast_out(datatype)
            TestApplication._debug("    - value: %r", value)

            sys.stdout.write(str(value) + '\n')
            sys.stdout.flush()

#
#   isint
#

def isint(s):
    """Return true if s is all digits."""
    for c in s:
        if c not in '0123456789':
            return False
    return True

#
#   TestConsoleCmd
#

class TestConsoleCmd(ConsoleCmd, Logging):

    def do_whois(self, args):
        """whois [ <addr>] [ <lolimit> <hilimit> ]"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_whois %r", args)

        try:
            # build a request
            request = WhoIsRequest()
            if (len(args) == 1) or (len(args) == 3):
                request.pduDestination = Address(args[0])
                del args[0]
            else:
                request.pduDestination = GlobalBroadcast()

            if len(args) == 2:
                request.deviceInstanceRangeLowLimit = int(args[0])
                request.deviceInstanceRangeHighLimit = int(args[1])
            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # give it to the application
            thisApplication.request(request)

        except Exception, e:
            TestConsoleCmd._exception("exception: %r", e)

    def do_iam(self, args):
        """iam"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_iam %r", args)

        try:
            # build a request
            request = IAmRequest()
            request.pduDestination = GlobalBroadcast()

            # set the parameters from the device object
            request.iAmDeviceIdentifier = thisDevice.objectIdentifier
            request.maxAPDULengthAccepted = thisDevice.maxApduLengthAccepted
            request.segmentationSupported = thisDevice.segmentationSupported
            request.vendorID = thisDevice.vendorIdentifier
            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # give it to the application
            thisApplication.request(request)

        except Exception, e:
            TestConsoleCmd._exception("exception: %r", e)

    def do_read(self, args):
        """read <addr> <type> <inst> <prop> [ <indx> ]"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_read %r", args)

        try:
            addr, obj_type, obj_inst, prop_id = args[:4]

            if isint(obj_type):
                obj_type = int(obj_type)
            elif not get_object_class(obj_type):
                raise ValueError, "unknown object type"

            obj_inst = int(obj_inst)

            datatype = get_datatype(obj_type, prop_id)
            if not datatype:
                raise ValueError, "invalid property for object type"

            # build a request
            request = ReadPropertyRequest(
                objectIdentifier=(obj_type, obj_inst),
                propertyIdentifier=prop_id,
                )
            request.pduDestination = Address(addr)

            if len(args) == 5:
                request.propertyArrayIndex = int(args[4])
            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # give it to the application
            thisApplication.request(request)

        except Exception, e:
            TestConsoleCmd._exception("exception: %r", e)

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

    # make a device object
    thisDevice = \
        LocalDeviceObject( objectName=config.get('BACpypes','objectName')
            , objectIdentifier=config.getint('BACpypes','objectIdentifier')
            , maxApduLengthAccepted=config.getint('BACpypes','maxApduLengthAccepted')
            , segmentationSupported=config.get('BACpypes','segmentationSupported')
            , vendorIdentifier=config.getint('BACpypes','vendorIdentifier')
            )

    # make a simple application
    thisApplication = TestApplication(thisDevice, addr)
    TestConsoleCmd()

    _log.debug("running")

    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")