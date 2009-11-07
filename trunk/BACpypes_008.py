#!/usr/bin/python

"""
BACpypes_008.py
"""

import sys
import logging

from BACpypes.Debugging import Logging
from BACpypes.CommandLogging import ConsoleLogHandler
from BACpypes.ConsoleCommunications import ConsoleCmd

from BACpypes.Core import run

from BACpypes.PDU import Address, GlobalBroadcast
from BACpypes.Application import BIPForeignApplication
from BACpypes.Object import LocalDeviceObject

from BACpypes.APDU import WhoIsRequest, IAmRequest, ReadPropertyRequest

# some debugging
_log = logging.getLogger(__name__)

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

class TestApplication(BIPForeignApplication, Logging):

    def Request(self, apdu):
        TestApplication._debug("Request %r", apdu)
        BIPForeignApplication.Request(self, apdu)

    def Confirmation(self, apdu):
        TestApplication._debug("Confirmation %r", apdu)

# reference a simple application
thisApplication = None

#

def isint(s):
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
        TestConsoleCmd._debug("do_whois %r", args)
            
        try:
            # build a request
            request = WhoIsRequest()
            if (len(args) == 1) or (len(args) == 3):
                request.pduDestination = Address(args[0])
                del args[0]
            else:
                request.pduDestination = GlobalBroadcast()

            if len(args) == 2:
                loLimit = int(args[0])
                hiLimit = int(args[1])

                request.deviceInstanceRangeLowLimit = int(args[0])
                request.deviceInstanceRangeHighLimit = int(args[1])
            TestConsoleCmd._debug("    - request: %r", request)
        
            # give it to the application
            thisApplication.Request(request)
            
        except Exception, e:
            TestConsoleCmd._exception("exception: %r", e)

    def do_iam(self, args):
        """iam"""
        args = args.split()
        TestConsoleCmd._debug("do_iam %r", args)

        try:
            # build a request
            request = IAmRequest()
            request.pduDestination = GlobalBroadcast()
            
            # set the parameters from the device object
            request.iAmDeviceIdentifier = thisDevice.objectIdentifier
            request.maxAPDULengthAccepted = thisDevice.maxApduLengthAccepted
            request.segmentationSupported = thisDevice.segmentationSupported
            request.vendorID = thisDevice.vendorIdentifier
            TestConsoleCmd._debug("    - request: %r", request)
            
            # give it to the application
            thisApplication.Request(request)
            
        except Exception, e:
            TestConsoleCmd._exception("exception: %r", e)

    def do_read(self, args):
        """read <addr> <type> <inst> <prop> [ <indx> ]"""
        args = args.split()
        TestConsoleCmd._debug("do_read %r", args)

        try:
            addr, objType, objInst, propId = args[:4]
            if isint(objType):
                objType = int(objType)
            objInst = int(objInst)

            # build a request
            request = ReadPropertyRequest(objectIdentifier=(objType, objInst), propertyIdentifier=propId)
            request.pduDestination = Address(addr)
            if len(args) == 5:
                request.propertyArrayIndex = int(args[4])
            TestConsoleCmd._debug("    - request: %r", request)
                
            # give it to the application
            thisApplication.Request(request)
            
        except Exception, e:
            TestConsoleCmd._exception("exception: %r", e)

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
    
    # make a simple application
    thisApplication = TestApplication(thisDevice
        , ('', config.getint('BACpypes','foreignPort'))
        , config.get('BACpypes','foreignBBMD')
        , config.getint('BACpypes','foreignTTL')
        )

    TestConsoleCmd()

    _log.debug("running")
    run()
except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")

