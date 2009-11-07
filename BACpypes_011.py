#!/usr/bin/python

"""
BACpypes_011.py
"""

import sys
import logging

from BACpypes.Debugging import Logging
from BACpypes.CommandLogging import ConsoleLogHandler

from BACpypes.Core import run

from BACpypes.PrimativeData import Real
from BACpypes.Application import BIPSimpleApplication
from BACpypes.Object import LocalDeviceObject, BinaryValueObject, Property, RegisterObjectType
from BACpypes.APDU import Error

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

    def __init__(self):
        BIPSimpleApplication.__init__(self, thisDevice, config.get('BACpypes','address'))

#
#   InactiveValueProperty
#

class InactiveValueProperty(Property, Logging):

    def __init__(self, identifier):
        Property.__init__(self, identifier, Real, default=None, optional=True, mutable=False)
        
    def ReadProperty(self, obj, arrayIndex=None):
        InactiveValueProperty._debug("ReadProperty %r arrayIndex=%r", obj, arrayIndex)
        
        # access an array
        if arrayIndex is not None:
            raise Error(errorClass='property', errorCode='property-is-not-an-array')
            
        # return false/inactive
        value = False
        InactiveValueProperty._debug("    - value: %r", value)
        
        return value
        
    def WriteProperty(self, obj, value, arrayIndex=None, priority=None):
        InactiveValueProperty._debug("WriteProperty %r %r arrayIndex=%r priority=%r", obj, value, arrayIndex, priority)
        raise Error(errorClass='property', errorCode='write-access-denied')
    
#
#   InactiveBinaryValueObject
#

class InactiveBinaryValueObject(BinaryValueObject):
    properties = \
        [ InactiveValueProperty('present-value')
        ]

RegisterObjectType(InactiveBinaryValueObject)

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
    testApplication = TestApplication()

    # make a bunch of these
    bvo0 = InactiveBinaryValueObject(objectIdentifier=('binary-value', 1000), objectName='Fake Point 1')
    bvo1 = InactiveBinaryValueObject(objectIdentifier=('binary-value', 1001), objectName='Fake Point 2')
    bvo2 = InactiveBinaryValueObject(objectIdentifier=('binary-value', 1002), objectName='Fake Point 3')
    bvo3 = InactiveBinaryValueObject(objectIdentifier=('binary-value', 1003), objectName='Fake Point 4')

    # add it to the device
    testApplication.AddObject(bvo0)
    testApplication.AddObject(bvo1)
    testApplication.AddObject(bvo2)
    testApplication.AddObject(bvo3)

    _log.debug("running")
    run()
except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")

