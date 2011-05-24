#!/usr/bin/python

"""
BACpypes_010.py
"""

import sys
import logging

from BACpypes.Debugging import Logging
from BACpypes.CommandLogging import ConsoleLogHandler
from BACpypes.ConsoleCommunications import ConsoleCmd

from BACpypes.Core import run

from BACpypes.PDU import Address, GlobalBroadcast
from BACpypes.PrimativeData import Unsigned
from BACpypes.ConstructedData import Array
from BACpypes.Application import BIPSimpleApplication
from BACpypes.Object import LocalDeviceObject, GetDatatype

from BACpypes.BaseTypes import BACnetPropertyReference
from BACpypes.APDU import WhoIsRequest, IAmRequest, \
    ReadPropertyRequest, ReadPropertyACK, \
    ReadPropertyMultipleRequest, ReadAccessSpecification, ReadPropertyMultipleACK

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

class TestApplication(BIPSimpleApplication, Logging):

    def Request(self, apdu):
        TestApplication._debug("Request %r", apdu)

        # save a copy of the request
        self.request = apdu

        # forward it along
        BIPSimpleApplication.Request(self, apdu)

    def Confirmation(self, apdu):
        TestApplication._debug("Confirmation %r", apdu)

        values = {}

        if (isinstance(self.request, ReadPropertyRequest)) and (isinstance(apdu, ReadPropertyACK)):
            # find the datatype
            datatype = GetDatatype(apdu.objectIdentifier[0], apdu.propertyIdentifier)
            TestApplication._debug("    - datatype: %r", datatype)
            if not datatype:
                raise TypeError, "unknown datatype"

            # special case for array parts, others are managed by CastOut
            if issubclass(datatype, Array) and (apdu.propertyArrayIndex is not None):
                if apdu.propertyArrayIndex == 0:
                    value = apdu.propertyValue.CastOut(Unsigned)
                else:
                    value = apdu.propertyValue.CastOut(datatype.subtype)
            else:
                value = apdu.propertyValue.CastOut(datatype)
            TestApplication._debug("    - value: %r", value)
            if hasattr(value, 'DebugContents'):
                value.DebugContents()

            values[apdu.propertyIdentifier] = value

        if (isinstance(self.request, ReadPropertyMultipleRequest)) and (isinstance(apdu, ReadPropertyMultipleACK)):
            # loop through the list of read access results
            for rslt in apdu.listOfReadAccessResults:
                objID = rslt.objectIdentifier
                TestApplication._debug("    - objID: %r", objID)

                for r in rslt.listOfResults:
                    propId = r.propertyIdentifier
                    TestApplication._debug("    - propId: %r", propId)
                    
                    # find the datatype
                    datatype = GetDatatype(objID[0], propId)
                    TestApplication._debug("    - datatype: %r", datatype)
                    if not datatype:
                        continue

                    # special case for array parts, others are managed by CastOut
                    if issubclass(datatype, Array) and (r.propertyArrayIndex is not None):
                        if r.propertyArrayIndex == 0:
                            value = r.readResult.propertyValue.CastOut(Unsigned)
                        else:
                            value = r.readResult.propertyValue.CastOut(datatype.subtype)
                    else:
                        value = r.readResult.propertyValue.CastOut(datatype)
                    TestApplication._debug("    - value: %r", value)
                    if hasattr(value, 'DebugContents'):
                        value.DebugContents()

                    values[objID, propId] = value

        if values:
            print values

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

    def do_readm(self, args):
        """readm <addr> <type> <inst>"""
        args = args.split()
        TestConsoleCmd._debug("do_readm %r", args)

        try:
            addr, objType, objInst = args[:3]
            if isint(objType):
                objType = int(objType)
            objInst = int(objInst)

            # build a request
            if 0:
                request = ReadPropertyMultipleRequest(
                            listOfReadAccessSpecs = \
                                [ ReadAccessSpecification(objectIdentifier=(objType, objInst)
                                    , listOfPropertyReferences = \
                                        [ BACnetPropertyReference(propertyIdentifier='object-name')
                                        , BACnetPropertyReference(propertyIdentifier='description')
                                        ]
                                    )
                                ]
                            )

            if 1:
                request = ReadPropertyMultipleRequest(
                            listOfReadAccessSpecs = \
                                [ ReadAccessSpecification(objectIdentifier=(objType, objInst)
                                    , listOfPropertyReferences = \
                                        [ BACnetPropertyReference(propertyIdentifier='all')
                                        ]
                                    )
                                ]
                            )

            request.pduDestination = Address(addr)
            if len(args) == 5:
                request.propertyArrayIndex = int(args[4])
            TestConsoleCmd._debug("    - request: %r", request)
                
            # give it to the application
            thisApplication.Request(request)
            
        except Exception, e:
            TestConsoleCmd._exception("exception: %r", e)

    def do_write(self, args):
        """write <addr> <type> <inst> <prop> <value> [ <indx> ] [ <priority> ]"""
        args = args.split()
        TestConsoleCmd._debug("do_write %r", args)

        try:
            addr, objType, objInst, propId = args[:4]
            if isint(objType):
                objType = int(objType)
            objInst = int(objInst)

            value = indx = priority = None
            if len(args) >= 5:
                value = args[4]
            if len(args) >= 6:
                indx = int(args[5])
            if len(args) >= 7:
                priority = int(args[6])

            # get the datatype
            datatype = GetDatatype(objType, propId)
            TestConsoleCmd._debug("    - datatype: %r", datatype)

            # change atomic values into something encodeable
            if issubclass(datatype, Atomic):
                if datatype == Integer:
                    value = int(value)
                elif datatype == Real:
                    value = float(value)

                value = datatype(value)
            elif issubclass(datatype, Array) and (indx is not None):
                if indx == 0:
                    value = Integer(value)
                elif issubclass(datatype.subtype, Atomic):
                    value = datatype.subtype(value)
                elif not isinstance(value, datatype.subtype):
                    raise TypeError, "invalid result datatype, expecting %s" % (datatype.subtype.__name__,)
            elif not isinstance(value, datatype):
                raise TypeError, "invalid result datatype, expecting %s" % (datatype.__name__,)
            TestConsoleCmd._debug("    - encodeable value: %r %s", value, type(value))

            # build a request
            request = WritePropertyRequest(objectIdentifier=(objType, objInst), propertyIdentifier=propId)
            request.pduDestination = Address(addr)
            if indx is not None:
                request.propertyArrayIndex = indx
            if priority is not None:
                request.priority = priority

            # save the result in the property value
            request.propertyValue = Any()
            try:
                request.propertyValue.CastIn(value)
            except Exception, e:
                TestConsoleCmd._exception("WriteProperty cast error: %r", e)

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
    
    addr = config.get('BACpypes', 'address')
    
    # maybe use a different port
    if '--port' in sys.argv:
        i = sys.argv.index('--port')
        addr += ':' + sys.argv[i+1]
    _log.debug("    - addr: %r", addr)
        
    # make a simple application
    thisApplication = TestApplication(thisDevice, addr)
    
    TestConsoleCmd()

    _log.debug("running")
    run()
except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")

