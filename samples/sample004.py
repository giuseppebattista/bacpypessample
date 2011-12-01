#!/usr/bin/python

"""
sample004.py
"""

import sys
import logging
import random

from ConfigParser import ConfigParser

from bacpypes.debugging import DebugContents, Logging, ModuleLogger
from bacpypes.consolelogging import ConsoleLogHandler

from bacpypes.core import run

from bacpypes.primitivedata import Real
from bacpypes.app import LocalDeviceObject, BIPSimpleApplication
from bacpypes.object import AnalogValueObject, Property, register_object_type
from bacpypes.apdu import Error

# some debugging
_debug = 0
_log = ModuleLogger(globals())

#
#   RandomValueProperty
#

class RandomValueProperty(Property, Logging):

    def __init__(self, identifier):
        if _debug: RandomValueProperty._debug("__init__ %r", identifier)
        Property.__init__(self, identifier, Real, default=None, optional=True, mutable=False)

    def ReadProperty(self, obj, arrayIndex=None):
        if _debug: RandomValueProperty._debug("ReadProperty %r arrayIndex=%r", obj, arrayIndex)

        # access an array
        if arrayIndex is not None:
            raise Error(errorClass='property', errorCode='propertyIsNotAnArray')

        # return a random value
        value = random.random() * 100.0
        if _debug: RandomValueProperty._debug("    - value: %r", value)

        return value

    def WriteProperty(self, obj, value, arrayIndex=None, priority=None):
        if _debug: RandomValueProperty._debug("WriteProperty %r %r arrayIndex=%r priority=%r", obj, value, arrayIndex, priority)
        raise Error(errorClass='property', errorCode='writeAccessDenied')

#
#   Random Value Object Type
#

class RandomAnalogValueObject(AnalogValueObject, Logging):

    properties = [
        RandomValueProperty('presentValue'),
        ]

    def __init__(self, _deviceid, _tagid, **kwargs):
        if _debug:
            RandomAnalogValueObject._debug("__init__ %r %r %r",
                _deviceid, _tagid, kwargs
                )
        AnalogValueObject.__init__(self, **kwargs)

        self._deviceid = _deviceid
        self._tagid = _tagid

register_object_type(RandomAnalogValueObject)

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

    # make a local device
    thisDevice = \
        LocalDeviceObject(objectName=config.get('BACpypes', 'objectName')
            , objectIdentifier=config.getint('BACpypes', 'objectIdentifier')
            , maxApduLengthAccepted=config.getint('BACpypes', 'maxApduLengthAccepted')
            , segmentationSupported=config.get('BACpypes', 'segmentationSupported')
            , vendorIdentifier=config.getint('BACpypes', 'vendorIdentifier')
            )

    # make a sample application
    thisApplication = BIPSimpleApplication(thisDevice, config.get('BACpypes','address'))

    # make a random input object
    ravo1 = RandomAnalogValueObject('device1', 'random1',
        objectIdentifier=('analogValue', 1), objectName='Random1'
        )
    _log.debug("    - ravo1: %r", ravo1)

    ravo2 = RandomAnalogValueObject('device2', 'random2',
        objectIdentifier=('analogValue', 2), objectName='Random2'
        )
    _log.debug("    - ravo2: %r", ravo2)

    # add it to the device
    thisApplication.add_object(ravo1)
    thisApplication.add_object(ravo2)
    _log.debug("    - object list: %r", thisDevice.objectList)

    _log.debug("running")

    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")
