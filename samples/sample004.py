#!/usr/bin/python

"""
sample004.py
"""

import sys
import logging
from collections import defaultdict

from ConfigParser import ConfigParser

from bacpypes.debugging import Logging, ModuleLogger
from bacpypes.consolelogging import ConsoleLogHandler

from bacpypes.core import run

from bacpypes.primativedata import Real
from bacpypes.app import BIPSimpleApplication
from bacpypes.object import LocalDeviceObject, AnalogInputObject, Property, register_object_type
from bacpypes.apdu import Error

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

class RandomAnalogValueObject(AnalogValueObject):
    properties = [
        RandomValueProperty('present-value'),
        ]

register_object_type(RandomAnalogInputObject)

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

    # make a sample application
    thisApplication = SampleApplication(thisDevice, config.get('BACpypes','address'))

    # make a random input object
    raio = RandomAnalogValueObject(objectIdentifier=('analog-value', 1), objectName='Random')

    # add it to the device
    thisApplication.AddObject(raio)

    _log.debug("running")

    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")

