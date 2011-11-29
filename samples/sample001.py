#!/usr/bin/python

"""
sample001.py
"""

import sys
import logging
from ConfigParser import ConfigParser

from bacpypes.debugging import Logging, ModuleLogger
from bacpypes.consolelogging import ConsoleLogHandler

from bacpypes.core import run

from bacpypes.app import LocalDeviceObject, BIPSimpleApplication

# some debugging
_debug = 0
_log = ModuleLogger(globals())

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
    if ('--buggers' in sys.argv):
        loggers = logging.Logger.manager.loggerDict.keys()
        loggers.sort()
        for loggerName in loggers:
            sys.stdout.write(loggerName + '\n')
        sys.exit(0)

    if ('--debug' in sys.argv):
        indx = sys.argv.index('--debug')
        i = indx + 1
        while (i < len(sys.argv)) and (not sys.argv[i].startswith('--')):
            ConsoleLogHandler(sys.argv[i])
            i += 1
        del sys.argv[indx:i]

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

    # make a device object
    thisDevice = \
        LocalDeviceObject( objectName=config.get('BACpypes','objectName')
            , objectIdentifier=config.getint('BACpypes','objectIdentifier')
            , maxApduLengthAccepted=config.getint('BACpypes','maxApduLengthAccepted')
            , segmentationSupported=config.get('BACpypes','segmentationSupported')
            , vendorIdentifier=config.getint('BACpypes','vendorIdentifier')
            )

    # make a sample application
    SampleApplication(thisDevice, config.get('BACpypes','address'))

    _log.debug("running")

    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")

