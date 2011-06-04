#!/usr/bin/python

"""
sample002.py
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
whoIsCounter = defaultdict(int)
iAmCounter = defaultdict(int)

#
#   SampleApplication
#

class SampleApplication(BIPSimpleApplication, Logging):

    def __init__(self, device, address):
        if _debug: SampleApplication._debug("__init__ %r %r", device, address)
        BIPSimpleApplication.__init__(self, device, address)

    def do_WhoIsRequest(self, apdu):
        """Respond to a Who-Is request."""
        if _debug: SampleApplication._debug("do_WhoIsRequest %r", apdu)

        # build a key from the source and parameters
        key = (str(apdu.pduSource),
            apdu.deviceInstanceRangeLowLimit,
            apdu.deviceInstanceRangeHighLimit,
            )

        # count the times this has been received
        whoIsCounter[key] += 1

        # pass back to the default implementation
        BIPSimpleApplication.do_WhoIsRequest(self, apdu)

    def do_IAmRequest(self, apdu):
        """Given an I-Am request, cache it."""
        if _debug: SampleApplication._debug("do_IAmRequest %r", apdu)

        # build a key from the source, just use the instance number
        key = (str(apdu.pduSource),
            apdu.iAmDeviceIdentifier[1],
            )

        # count the times this has been received
        iAmCounter[key] += 1

        # pass back to the default implementation
        BIPSimpleApplication.do_IAmRequest(self, apdu)

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

    print "----- Who Is -----"
    for (src, lowlim, hilim), count in sorted(whoIsCounter.items()):
        print "%-20s %8s %8s %4d" % (src, lowlim, hilim, count)
    print

    print "----- I Am -----"
    for (src, devid), count in sorted(iAmCounter.items()):
        print "%-20s %8d %4d" % (src, devid, count)
    print

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")
