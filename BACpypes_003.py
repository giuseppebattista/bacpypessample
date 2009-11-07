#!/usr/bin/python

"""
BACpypes_003.py
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
whoHasCounter = {}
iHaveCounter = {}

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
        
    def do_WhoHasRequest(self, apdu):
        """Respond to a Who-Has request."""
        TestApplication._debug("do_WhoHasRequest, %r", apdu)
        
        key = (str(apdu.pduSource),)
        if apdu.object.objectIdentifier is not None:
            key += (str(apdu.object.objectIdentifier),)
        if apdu.object.objectName is not None:
            key += (apdu.object.objectName,)
        else:
            print "(rejected APDU:"
            apdu.DebugContents()
            print ")"
            return
            
        whoHasCounter[key] = whoHasCounter.get(key,0) + 1
            
    def do_IHaveRequest(self, apdu):
        """Respond to a I-Have request."""
        TestApplication._debug("do_IHaveRequest %r", apdu)

        key = (str(apdu.pduSource), str(apdu.deviceIdentifier), str(apdu.objectIdentifier), apdu.objectName)
        iHaveCounter[key] = iHaveCounter.get(key,0) + 1

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
print "----- Who Has -----"
for (src, objname), count in sorted(whoHasCounter.items()):
    print "%-20s %-30s %4d" % (src, objname, count)
print
print "----- I Have -----"
for (src, devid, objid, objname), count in sorted(iHaveCounter.items()):
    print "%-20s %-20s %-20s %-20s %4d" % (src, devid, objid, objname, count)
print

