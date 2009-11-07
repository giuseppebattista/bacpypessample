#!/usr/bin/python

"""
BACpypes_007.py
"""

import sys
import logging

from BACpypes.Debugging import Logging
from BACpypes.CommandLogging import ConsoleLogHandler

from BACpypes.Core import run
from BACpypes.ConsoleCommunications import ConsoleLogging

from BACpypes.Application import BIPForeignApplication
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

class TestApplication(BIPForeignApplication, Logging):

    def __init__(self):
        TestApplication._debug("__init__")
        BIPForeignApplication.__init__(self, thisDevice
            , ('', config.getint('BACpypes','foreignPort'))  # local port to use
            , config.get('BACpypes','foreignBBMD')           # address of BBMD
            , config.getint('BACpypes','foreignTTL')         # time-to-live for registration
            )

    def Request(self, apdu):
        TestApplication._debug("Request %r", apdu)
        BIPForeignApplication.Request(self, apdu)
        sys.stdout.flush()

    def Indication(self, apdu):
        TestApplication._debug("Indication %r", apdu)
        BIPForeignApplication.Indication(self, apdu)
        sys.stdout.flush()

    def Response(self, apdu):
        TestApplication._debug("Response %r", apdu)
        BIPForeignApplication.Response(self, apdu)
        sys.stdout.flush()

    def Confirmation(self, apdu):
        TestApplication._debug("Confirmation %r", apdu)
        BIPForeignApplication.Confirmation(self, apdu)
        sys.stdout.flush()

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
    ConsoleLogging()

    _log.debug("running")
    run()
except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")

