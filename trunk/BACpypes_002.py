#!/usr/bin/python

"""
BACpypes_002.py
"""

import sys
import logging

from BACpypes.Debugging import Logging
from BACpypes.CommandLogging import ConsoleLogHandler

from BACpypes.Core import run

from BACpypes.Application import BIPSimpleApplication
from BACpypes.Object import LocalDeviceObject

# some debugging
_log = logging.getLogger(__name__)

# counters
whoIsCounter = {}
iAmCounter = {}

# make a device object from a configuration file
from ConfigParser import ConfigParser
config = ConfigParser()
config.read('BACpypes.ini')

thisDevice = \
    LocalDeviceObject( objectName=config.get('BACpypes','objectName')
        , objectIdentifier=config.getint('BACpypes','objectIdentifier')
        , maxApduLengthAccepted=config.getint('BACpypes','maxApduLengthAccepted')
        , segmentationSupported=config.get('BACpypes','segmentationSupported')
        , vendorIdentifier=config.getint('BACpypes','vendorIdentifier')
        )

#
#   TestApplication
#

class TestApplication(BIPSimpleApplication, Logging):

    def __init__(self):
        BIPSimpleApplication.__init__(self, thisDevice, config.get('BACpypes','address'))
        
    def do_WhoIsRequest(self, apdu):
        """Respond to a Who-Is request."""
        TestApplication._debug("do_WhoIsRequest %r", apdu)
        
        key = (str(apdu.pduSource), apdu.deviceInstanceRangeLowLimit, apdu.deviceInstanceRangeHighLimit)
        
        whoIsCounter[key] = whoIsCounter.get(key,0) + 1
        
        # pass back to the default implementation
        BIPSimpleApplication.do_WhoIsRequest(self, apdu)
        
    def do_IAmRequest(self, apdu):
        """Given an I-Am request, cache it."""
        TestApplication._debug("do_IAmRequest %r", apdu)
            
        key = (str(apdu.pduSource), apdu.iAmDeviceIdentifier[1])
        
        iAmCounter[key] = iAmCounter.get(key,0) + 1
        
        # pass back to the default implementation
        BIPSimpleApplication.do_IAmRequest(self, apdu)

#
#   __main__
#

try:
    if ('--debug' in sys.argv):
        indx = sys.argv.index('--debug')
        for i in range(indx+1, len(sys.argv)):
            ConsoleLogHandler(sys.argv[i])
        del sys.argv[indx:]

    _log.debug("initialization")

    TestApplication()

    _log.debug("running")
    run()
except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")
    
print
print "----- Who Is -----"
for (src, lowlim, hilim), count in sorted(whoIsCounter.items()):
    print "%-20s %8s %8s %4d" % (src, lowlim, hilim, count)
    
print
print "----- I Am -----"
for (src, devid), count in sorted(iAmCounter.items()):
    print "%-20s %8d %4d" % (src, devid, count)
print

