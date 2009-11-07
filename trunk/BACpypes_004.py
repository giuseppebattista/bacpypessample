#!/usr/bin/python

"""
BACpypes_004.py
"""

import sys
import random
import logging

from BACpypes.Debugging import Logging
from BACpypes.CommandLogging import ConsoleLogHandler

from BACpypes.Core import run

from BACpypes.PrimativeData import Real
from BACpypes.Application import BIPSimpleApplication
from BACpypes.Object import LocalDeviceObject, AnalogInputObject, Property, RegisterObjectType
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
#   RandomValueProperty
#

class RandomValueProperty(Property, Logging):

    def __init__(self, identifier):
        Property.__init__(self, identifier, Real, default=None, optional=True, mutable=False)
        
    def ReadProperty(self, obj, arrayIndex=None):
        RandomValueProperty._debug("ReadProperty %r arrayIndex=%r", obj, arrayIndex)
        
        # access an array
        if arrayIndex is not None:
            raise Error(errorClass='property', errorCode='property-is-not-an-array')
            
        # return a random value
        value = random.random() * 100.0
        RandomValueProperty._debug("    - value: %r", value)
        
        return value
        
    def WriteProperty(self, obj, value, arrayIndex=None, priority=None):
        RandomValueProperty._debug("WriteProperty %r %r arrayIndex=%r priority=%r", obj, value, arrayIndex, priority)
        raise Error(errorClass='property', errorCode='write-access-denied')
    
#
#   Random Value Object Type
#

class RandomAnalogInputObject(AnalogInputObject):
    properties = \
        [ RandomValueProperty('present-value')
        ]

RegisterObjectType(RandomAnalogInputObject)

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
    thisApplication = BIPSimpleApplication(thisDevice, config.get('BACpypes','address'))

    # make a random input object
    raio = RandomAnalogInputObject(objectIdentifier=('analog-input', 1), objectName='Random')

    # add it to the device
    thisApplication.AddObject(raio)

    _log.debug("running")
    run()
except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")

