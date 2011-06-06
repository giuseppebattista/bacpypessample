#!/usr/bin/python

"""
sample003.py
"""

import sys
import logging
from collections import defaultdict

from ConfigParser import ConfigParser

from bacpypes.debugging import Logging, ModuleLogger
from bacpypes.consolelogging import ConsoleLogHandler

from bacpypes.core import run

from bacpypes.app import BIPSimpleApplication
from bacpypes.object import LocalDeviceObject

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# counters
whoHasCounter = defaultdict(int)
iHaveCounter = defaultdict(int)

#
#   SampleApplication
#

class SampleApplication(BIPSimpleApplication, Logging):

    def __init__(self, device, address):
        if _debug: SampleApplication._debug("__init__ %r %r", device, address)
        BIPSimpleApplication.__init__(self, device, address)

    def do_WhoHasRequest(self, apdu):
        """Respond to a Who-Has request."""
        if _debug: SampleApplication._debug("do_WhoHasRequest, %r", apdu)

        key = (str(apdu.pduSource),)
        if apdu.object.objectIdentifier is not None:
            key += (str(apdu.object.objectIdentifier),)
        elif apdu.object.objectName is not None:
            key += (apdu.object.objectName,)
        else:
            print "(rejected APDU:"
            apdu.debug_contents()
            print ")"
            return

        # count the times this has been received
        whoHasCounter[key] += 1

    def do_IHaveRequest(self, apdu):
        """Respond to a I-Have request."""
        if _debug: SampleApplication._debug("do_IHaveRequest %r", apdu)

        key = (
            str(apdu.pduSource),
            str(apdu.deviceIdentifier),
            str(apdu.objectIdentifier),
            apdu.objectName
            )

        # count the times this has been received
        iHaveCounter[key] += 1

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

    # make a device object
    thisDevice = \
        LocalDeviceObject( objectName=config.get('BACpypes','objectName')
            , objectIdentifier=config.getint('BACpypes','objectIdentifier')
            , maxApduLengthAccepted=config.getint('BACpypes','maxApduLengthAccepted')
            , segmentationSupported=config.get('BACpypes','segmentationSupported')
            , vendorIdentifier=config.getint('BACpypes','vendorIdentifier')
            )

    # make a sample application
    SampleApplication(thisDevice, config.get('BACpypes','address'))

    _log.debug("running")

    # run until stopped, ^C works
    run()

    print "----- Who Has -----"
    for (src, objname), count in sorted(whoHasCounter.items()):
        print "%-20s %-30s %4d" % (src, objname, count)
    print

    print "----- I Have -----"
    for (src, devid, objid, objname), count in sorted(iHaveCounter.items()):
        print "%-20s %-20s %-20s %-20s %4d" % (src, devid, objid, objname, count)
    print

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")
