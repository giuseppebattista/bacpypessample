#!/usr/bin/python

"""
BACpypes_001.py
"""

import sys
import logging

from BACpypes.Debugging import Logging
from BACpypes.CommandLogging import ConsoleLogHandler

from BACpypes.Core import run

from BACpypes.Application import BIPSimpleApplication
from BACpypes.Object import LocalDeviceObject

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

# some debugging
_log = logging.getLogger(__name__)

#
#   TestApplication
#

class TestApplication(BIPSimpleApplication, Logging):

    def __init__(self):
        TestApplication._debug("__init__")
        BIPSimpleApplication.__init__(self, thisDevice, config.get('BACpypes','address'))
        
    def Request(self, apdu):
        TestApplication._debug("Request %r", apdu)
        BIPSimpleApplication.Request(self, apdu)

    def Indication(self, apdu):
        TestApplication._debug("Indication %r", apdu)
        BIPSimpleApplication.Indication(self, apdu)

    def Response(self, apdu):
        TestApplication._debug("Response %r", apdu)
        BIPSimpleApplication.Response(self, apdu)

    def Confirmation(self, apdu):
        TestApplication._debug("Confirmation %r", apdu)
        BIPSimpleApplication.Confirmation(self, apdu)

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

