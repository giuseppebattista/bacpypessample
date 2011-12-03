#!/usr/bin/python

"""
sample016.py
"""

import sys
import logging

from ConfigParser import ConfigParser

from bacpypes.debugging import Logging, ModuleLogger
from bacpypes.consolelogging import ConsoleLogHandler
from bacpypes.consolecmd import ConsoleCmd

from bacpypes.core import run

from bacpypes.pdu import Address, GlobalBroadcast
from bacpypes.app import LocalDeviceObject, BIPSimpleApplication
from bacpypes.object import get_object_class, get_datatype

from bacpypes.apdu import Error, AbortPDU, \
    AtomicReadFileRequest, \
        AtomicReadFileRequestAccessMethodChoice, \
            AtomicReadFileRequestAccessMethodChoiceRecordAccess, \
            AtomicReadFileRequestAccessMethodChoiceStreamAccess, \
    AtomicReadFileACK, \
    AtomicWriteFileRequest, \
        AtomicWriteFileRequestAccessMethodChoice, \
            AtomicWriteFileRequestAccessMethodChoiceRecordAccess, \
            AtomicWriteFileRequestAccessMethodChoiceStreamAccess, \
    AtomicWriteFileACK
from bacpypes.basetypes import ServicesSupported

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# reference a simple application
thisApplication = None

#
#   TestApplication
#

class TestApplication(BIPSimpleApplication, Logging):

    def request(self, apdu):
        if _debug: TestApplication._debug("request %r", apdu)

        # save a copy of the request
        self._request = apdu

        # forward it along
        BIPSimpleApplication.request(self, apdu)

    def confirmation(self, apdu):
        if _debug: TestApplication._debug("confirmation %r", apdu)

        if isinstance(apdu, Error):
            sys.stdout.write("error: %s\n" % (apdu.errorCode,))
            sys.stdout.flush()

        elif isinstance(apdu, AbortPDU):
            apdu.debug_contents()

        elif (isinstance(self._request, AtomicReadFileRequest)) and (isinstance(apdu, AtomicReadFileACK)):
            # suck out the record data
            if apdu.accessMethod.recordAccess:
                value = apdu.accessMethod.recordAccess.fileRecordData
            elif apdu.accessMethod.streamAccess:
                value = apdu.accessMethod.streamAccess.fileData
            TestApplication._debug("    - value: %r", value)

            sys.stdout.write(repr(value) + '\n')
            sys.stdout.flush()

        elif (isinstance(self._request, AtomicWriteFileRequest)) and (isinstance(apdu, AtomicWriteFileACK)):
            # suck out the record data
            if apdu.fileStartPosition is not None:
                value = apdu.fileStartPosition
            elif apdu.fileStartRecord is not None:
                value = apdu.fileStartRecord
            TestApplication._debug("    - value: %r", value)

            sys.stdout.write(repr(value) + '\n')
            sys.stdout.flush()

#
#   isint
#

def isint(s):
    """Return true if s is all digits."""
    for c in s:
        if c not in '0123456789':
            return False
    return True

#
#   TestConsoleCmd
#

class TestConsoleCmd(ConsoleCmd, Logging):

    def do_readrecord(self, args):
        """readrecord <addr> <inst> <start> <count>"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_readrecord %r", args)

        try:
            addr, obj_inst, start_record, record_count = args

            obj_type = 'file'
            obj_inst = int(obj_inst)
            start_record = int(start_record)
            record_count = int(record_count)

            # build a request
            request = AtomicReadFileRequest(
                fileIdentifier=(obj_type, obj_inst),
                accessMethod=AtomicReadFileRequestAccessMethodChoice(
                    recordAccess=AtomicReadFileRequestAccessMethodChoiceRecordAccess(
                        fileStartRecord=start_record,
                        requestedRecordCount=record_count,
                        ),
                    ),
                )
            request.pduDestination = Address(addr)
            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # give it to the application
            thisApplication.request(request)

        except Exception, e:
            TestConsoleCmd._exception("exception: %r", e)

    def do_readstream(self, args):
        """readstream <addr> <inst> <start> <count>"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_readstream %r", args)

        try:
            addr, obj_inst, start_position, octet_count = args

            obj_type = 'file'
            obj_inst = int(obj_inst)
            start_position = int(start_position)
            octet_count = int(octet_count)

            # build a request
            request = AtomicReadFileRequest(
                fileIdentifier=(obj_type, obj_inst),
                accessMethod=AtomicReadFileRequestAccessMethodChoice(
                    streamAccess=AtomicReadFileRequestAccessMethodChoiceStreamAccess(
                        fileStartPosition=start_position,
                        requestedOctetCount=octet_count,
                        ),
                    ),
                )
            request.pduDestination = Address(addr)
            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # give it to the application
            thisApplication.request(request)

        except Exception, e:
            TestConsoleCmd._exception("exception: %r", e)

    def do_writerecord(self, args):
        """writerecord <addr> <inst> <start> <count> [ <data> ... ]"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_writerecord %r", args)

        try:
            addr, obj_inst, start_record, record_count = args[0:4]

            obj_type = 'file'
            obj_inst = int(obj_inst)
            start_record = int(start_record)
            record_count = int(record_count)
            record_data = list(args[4:])

            # build a request
            request = AtomicWriteFileRequest(
                fileIdentifier=(obj_type, obj_inst),
                accessMethod=AtomicWriteFileRequestAccessMethodChoice(
                    recordAccess=AtomicWriteFileRequestAccessMethodChoiceRecordAccess(
                        fileStartRecord=start_record,
                        recordCount=record_count,
                        fileRecordData=record_data,
                        ),
                    ),
                )
            request.pduDestination = Address(addr)
            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # give it to the application
            thisApplication.request(request)

        except Exception, e:
            TestConsoleCmd._exception("exception: %r", e)

    def do_writestream(self, args):
        """writestream <addr> <inst> <start> <data>"""
        args = args.split()
        if _debug: TestConsoleCmd._debug("do_writestream %r", args)

        try:
            addr, obj_inst, start_position, data = args

            obj_type = 'file'
            obj_inst = int(obj_inst)
            start_position = int(start_position)

            # build a request
            request = AtomicWriteFileRequest(
                fileIdentifier=(obj_type, obj_inst),
                accessMethod=AtomicWriteFileRequestAccessMethodChoice(
                    streamAccess=AtomicWriteFileRequestAccessMethodChoiceStreamAccess(
                        fileStartPosition=start_position,
                        fileData=data,
                        ),
                    ),
                )
            request.pduDestination = Address(addr)
            if _debug: TestConsoleCmd._debug("    - request: %r", request)

            # give it to the application
            thisApplication.request(request)

        except Exception, e:
            TestConsoleCmd._exception("exception: %r", e)

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

    # get the address from the config file
    addr = config.get('BACpypes', 'address')

    # maybe use a different port
    if '--port' in sys.argv:
        i = sys.argv.index('--port')
        addr += ':' + sys.argv[i+1]
    _log.debug("    - addr: %r", addr)

    # make a device object
    thisDevice = \
        LocalDeviceObject( objectName=config.get('BACpypes','objectName')
            , objectIdentifier=config.getint('BACpypes','objectIdentifier')
            , maxApduLengthAccepted=config.getint('BACpypes','maxApduLengthAccepted')
            , segmentationSupported=config.get('BACpypes','segmentationSupported')
            , vendorIdentifier=config.getint('BACpypes','vendorIdentifier')
            )

    # build a bit string that knows about the bit names
    pss = ServicesSupported()
    pss['whoIs'] = 1
    pss['iAm'] = 1
    pss['readProperty'] = 1
    pss['writeProperty'] = 1
    pss['atomicReadFile'] = 1

    # set the property value to be just the bits
    thisDevice.protocolServicesSupported = pss.value

    # make a simple application
    thisApplication = TestApplication(thisDevice, addr)
    TestConsoleCmd()

    _log.debug("running")

    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")
