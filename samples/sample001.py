#!/usr/bin/python

"""
sample001.py
"""

import sys
import logging

from ConfigParser import ConfigParser

from bacpypes.debugging import Logging, ModuleLogger
from bacpypes.consolelogging import ArgumentParser

from bacpypes.core import run

from bacpypes.app import LocalDeviceObject, BIPSimpleApplication

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# globals
this_application = None

#
#   SampleApplication
#

class SampleApplication(BIPSimpleApplication, Logging):

    def __init__(self, device, address):
        if _debug: SampleApplication._debug("__init__ %r %r", device, address)
        BIPSimpleApplication.__init__(self, device, address)

    def request(self, apdu):
        if _debug: SampleApplication._debug("request %r", apdu)
        BIPSimpleApplication.request(self, apdu)

    def indication(self, apdu):
        if _debug: SampleApplication._debug("indication %r", apdu)
        BIPSimpleApplication.indication(self, apdu)

    def response(self, apdu):
        if _debug: SampleApplication._debug("response %r", apdu)
        BIPSimpleApplication.response(self, apdu)

    def confirmation(self, apdu):
        if _debug: SampleApplication._debug("confirmation %r", apdu)
        BIPSimpleApplication.confirmation(self, apdu)

#
#   __main__
#

try:
    # parse the command line arguments
    args = ArgumentParser().parse_args()

    if _debug: _log.debug("initialization")
    if _debug: _log.debug("    - args: %r", args)

    # read in the configuration file
    config = ConfigParser()
    config.read(args.ini)
    if _debug: _log.debug("    - config: %r", config.items('BACpypes'))

    # make a device object
    this_device = LocalDeviceObject(
        objectName=config.get('BACpypes','objectName'),
        objectIdentifier=config.getint('BACpypes','objectIdentifier'),
        maxApduLengthAccepted=config.getint('BACpypes','maxApduLengthAccepted'),
        segmentationSupported=config.get('BACpypes','segmentationSupported'),
        vendorIdentifier=config.getint('BACpypes','vendorIdentifier'),
        )

    # make a sample application
    this_application = SampleApplication(this_device, config.get('BACpypes','address'))

    _log.debug("running")

    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")

