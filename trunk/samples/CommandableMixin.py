#!/usr/bin/python

"""
This sample application demonstrates a mix-in class for commandable properties
(not useful for Binary Out or Binary Value objects that have a minimum on and off
time, or for Channel objects).
"""

import random

from bacpypes.debugging import bacpypes_debugging, ModuleLogger
from bacpypes.consolelogging import ConfigArgumentParser

from bacpypes.core import run

from bacpypes.primitivedata import Real
from bacpypes.app import LocalDeviceObject, BIPSimpleApplication
from bacpypes.object import AnalogValueObject, Property, register_object_type
from bacpypes.apdu import Error

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# globals
this_device = None
this_application = None

#
#   CommandableMixin
#

@bacpypes_debugging
class CommandableMixin(object):

    def __init__(self):
        if _debug: CommandableMixin._debug("__init__")

    def WriteProperty(self, property, value, arrayIndex=None, priority=None):
        if _debug: CommandableMixin._debug("WriteProperty %r %r arrayIndex=%r priority=%r", property, value, arrayIndex, priority)

        super(CommandableMixin, self).WriteProperty(
            property, value,
            arrayIndex=arrayIndex, priority=priority,
            )

#
#   CommandableAnalogValueObject
#

@bacpypes_debugging
class CommandableAnalogValueObject(CommandableMixin, AnalogValueObject):

    def __init__(self, **kwargs):
        if _debug: CommandableAnalogValueObject._debug("__init__ %r", kwargs)
        CommandableMixin.__init__(self)
        AnalogValueObject.__init__(self, **kwargs)

        self.presentValue = 0.0

#
#   __main__
#

try:
    # parse the command line arguments
    args = ConfigArgumentParser(description=__doc__).parse_args()

    if _debug: _log.debug("initialization")
    if _debug: _log.debug("    - args: %r", args)

    # make a device object
    this_device = LocalDeviceObject(
        objectName=args.ini.objectname,
        objectIdentifier=int(args.ini.objectidentifier),
        maxApduLengthAccepted=int(args.ini.maxapdulengthaccepted),
        segmentationSupported=args.ini.segmentationsupported,
        vendorIdentifier=int(args.ini.vendoridentifier),
        )

    # make a sample application
    this_application = BIPSimpleApplication(this_device, args.ini.address)

    # make a random input object
    cavo1 = CommandableAnalogValueObject(
        objectIdentifier=('analogValue', 1), objectName='Commandable1'
        )
    if _debug: _log.debug("    - cavo1: %r", cavo1)

    cavo2 = CommandableAnalogValueObject(
        objectIdentifier=('analogValue', 2), objectName='Commandable2'
        )
    if _debug: _log.debug("    - cavo2: %r", cavo2)

    # add it to the device
    this_application.add_object(cavo1)
    this_application.add_object(cavo2)
    if _debug: _log.debug("    - object list: %r", this_device.objectList)

    if _debug: _log.debug("running")

    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    if _debug: _log.debug("finally")

