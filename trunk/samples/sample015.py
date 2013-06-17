#!/usr/bin/python

"""
sample015.py
"""

import sys
import logging
import random
import string

from ConfigParser import ConfigParser

from bacpypes.debugging import bacpypes_debugging, DebugContents, ModuleLogger
from bacpypes.consolelogging import ConsoleLogHandler

from bacpypes.core import run

from bacpypes.primitivedata import Real
from bacpypes.app import LocalDeviceObject, BIPSimpleApplication
from bacpypes.object import FileObject, register_object_type
from bacpypes.apdu import Error

from bacpypes.basetypes import ServicesSupported

# some debugging
_debug = 0
_log = ModuleLogger(globals())

#
#   Local Record Access File Object Type
#

@bacpypes_debugging
class LocalRecordAccessFileObject(FileObject):

    def __init__(self, **kwargs):
        """ Initialize a record accessed file object. """
        if _debug:
            LocalRecordAccessFileObject._debug("__init__ %r",
                kwargs,
                )
        FileObject.__init__(self,
            fileAccessMethod='recordAccess',
             **kwargs
             )

        self._record_data = [
            ''.join(random.choice(string.ascii_letters)
            for i in range(random.randint(10, 20)))
            for j in range(random.randint(10, 20))
            ]
        if _debug: LocalRecordAccessFileObject._debug("    - %d records",
                len(self._record_data),
                )

    def __len__(self):
        """ Return the number of records. """
        if _debug: LocalRecordAccessFileObject._debug("__len__")

        return len(self._record_data)

    def ReadFile(self, start_record, record_count):
        """ Read a number of records starting at a specific record. """
        if _debug: LocalRecordAccessFileObject._debug("ReadFile %r %r",
                start_record, record_count,
                )

        # end of file is true if last record is returned
        end_of_file = (start_record+record_count) >= len(self._record_data)

        return end_of_file, \
            self._record_data[start_record:start_record + record_count]

    def WriteFile(self, start_record, record_count, record_data):
        """ Write a number of records, starting at a specific record. """
        # check for append
        if (start_record < 0):
            start_record = len(self._record_data)
            self._record_data.extend(record_data)

        # check to extend the file out to start_record records
        elif (start_record > len(self._record_data)):
            self._record_data.extend(['' for i in range(start_record - len(self._record_data))])
            start_record = len(self._record_data)
            self._record_data.extend(record_data)

        # slice operation works for other cases
        else:
            self._record_data[start_record:start_record + record_count] = record_data

        # return where the 'writing' actually started
        return start_record

register_object_type(LocalRecordAccessFileObject)

#
#   Local Stream Access File Object Type
#

@bacpypes_debugging
class LocalStreamAccessFileObject(FileObject):

    def __init__(self, **kwargs):
        """ Initialize a stream accessed file object. """
        if _debug:
            LocalStreamAccessFileObject._debug("__init__ %r",
                kwargs,
                )
        FileObject.__init__(self,
            fileAccessMethod='streamAccess',
             **kwargs
             )

        self._file_data = ''.join(random.choice(string.ascii_letters)
            for i in range(random.randint(100, 200)))
        if _debug: LocalRecordAccessFileObject._debug("    - %d octets",
                len(self._file_data),
                )

    def __len__(self):
        """ Return the number of octets in the file. """
        if _debug: LocalStreamAccessFileObject._debug("__len__")

        return len(self._file_data)

    def ReadFile(self, start_position, octet_count):
        """ Read a chunk of data out of the file. """
        if _debug: LocalStreamAccessFileObject._debug("ReadFile %r %r",
                start_position, octet_count,
                )

        # end of file is true if last record is returned
        end_of_file = (start_position+octet_count) >= len(self._file_data)

        return end_of_file, \
            self._file_data[start_position:start_position + octet_count]

    def WriteFile(self, start_position, data):
        """ Write a number of octets, starting at a specific offset. """
        # check for append
        if (start_position < 0):
            start_position = len(self._file_data)
            self._file_data += data

        # check to extend the file out to start_record records
        elif (start_position > len(self._file_data)):
            self._file_data += '\0' * (start_position - len(self._file_data))
            start_position = len(self._file_data)
            self._file_data += data

        # no slice assignment, strings are immutable 
        else:
            data_len = len(data)
            prechunk = self._file_data[:start_position]
            postchunk = self._file_data[start_position + data_len:]
            self._file_data = prechunk + data + postchunk

        # return where the 'writing' actually started
        return start_position

register_object_type(LocalStreamAccessFileObject)

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
    this_device = LocalDeviceObject(
        objectName=config.get('BACpypes','objectName'),
        objectIdentifier=config.getint('BACpypes','objectIdentifier'),
        maxApduLengthAccepted=config.getint('BACpypes','maxApduLengthAccepted'),
        segmentationSupported=config.get('BACpypes','segmentationSupported'),
        vendorIdentifier=config.getint('BACpypes','vendorIdentifier'),
        )

    # build a bit string that knows about the bit names
    pss = ServicesSupported()
    pss['whoIs'] = 1
    pss['iAm'] = 1
    pss['readProperty'] = 1
    pss['writeProperty'] = 1
    pss['atomicReadFile'] = 1

    # set the property value to be just the bits
    this_device.protocolServicesSupported = pss.value

    # make a sample application
    this_application = BIPSimpleApplication(
        this_device,
        config.get('BACpypes','address'),
        )

    # make a record access file
    f1 = LocalRecordAccessFileObject(
        objectIdentifier=('file', 1),
        objectName='RecordAccessFile1'
        )
    _log.debug("    - f1: %r", f1)

    # make a stream access file
    f2 = LocalStreamAccessFileObject(
        objectIdentifier=('file', 2),
        objectName='StreamAccessFile2'
        )
    _log.debug("    - f2: %r", f2)

    # add them to the device
    this_application.add_object(f1)
    this_application.add_object(f2)

    _log.debug("running")

    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")
