#!/usr/bin/python

"""
sample005.py
"""

import sys
import logging

import threading
import simplejson
import urlparse

import SocketServer
import SimpleHTTPServer

from ConfigParser import ConfigParser

from bacpypes.debugging import Logging, ModuleLogger
from bacpypes.consolelogging import ConsoleLogHandler

from bacpypes.core import run

from bacpypes.pdu import Address
from bacpypes.app import LocalDeviceObject, BIPSimpleApplication
from bacpypes.object import get_object_class, get_datatype

from bacpypes.apdu import ReadPropertyRequest, Error, AbortPDU, ReadPropertyACK
from bacpypes.primitivedata import Unsigned
from bacpypes.constructeddata import Array
from bacpypes.basetypes import ServicesSupported

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# reference a simple application
thisApplication = None

#
#   IOCB
#

class IOCB:

    def __init__(self):
        # requests and responses
        self.ioRequest = None
        self.ioResponse = None

        # each block gets a completion event
        self.ioComplete = threading.Event()
        self.ioComplete.clear()

#
#   WebServerApplication
#

class WebServerApplication(BIPSimpleApplication, Logging):

    def __init__(self, *args):
        if _debug: WebServerApplication._debug("__init__ %r", args)
        BIPSimpleApplication.__init__(self, *args)

        # assigning invoke identifiers
        self.nextInvokeID = 1

        # keep track of requests to line up responses
        self.iocb = {}

    def get_next_invoke_id(self, addr):
        """Called to get an unused invoke ID."""
        if _debug: WebServerApplication._debug("get_next_invoke_id %r", addr)

        initialID = self.nextInvokeID
        while 1:
            invokeID = self.nextInvokeID
            self.nextInvokeID = (self.nextInvokeID + 1) % 256

            # see if we've checked for them all
            if initialID == self.nextInvokeID:
                raise RuntimeError, "no available invoke ID"

            # see if this one is used
            if (addr, invokeID) not in self.iocb:
                break

        if _debug: WebServerApplication._debug("    - invokeID: %r", invokeID)
        return invokeID

    def request(self, apdu, iocb):
        if _debug: WebServerApplication._debug("request %r", apdu)

        # assign an invoke identifier
        apdu.apduInvokeID = self.get_next_invoke_id(apdu.pduDestination)

        # build a key to reference the IOCB when the response comes back
        invoke_key = (apdu.pduDestination, apdu.apduInvokeID)
        if _debug: WebServerApplication._debug("    - invoke_key: %r", invoke_key)

        # keep track of the request
        self.iocb[invoke_key] = iocb

        # forward it along, apduInvokeID set by stack
        BIPSimpleApplication.request(self, apdu)

    def confirmation(self, apdu):
        if _debug: WebServerApplication._debug("confirmation %r", apdu)

        # build a key to look for the IOCB
        invoke_key = (apdu.pduSource, apdu.apduInvokeID)
        if _debug: WebServerApplication._debug("    - invoke_key: %r", invoke_key)

        # find the request
        iocb = self.iocb.get(invoke_key, None)
        if not iocb:
            raise RuntimeError, "no matching request"
        del self.iocb[invoke_key]

        if isinstance(apdu, Error):
            if _debug: WebServerApplication._debug("    - error")
            iocb.ioResponse = apdu

        elif isinstance(apdu, AbortPDU):
            if _debug: WebServerApplication._debug("    - abort")
            iocb.ioResponse = apdu

        elif (isinstance(iocb.ioRequest, ReadPropertyRequest)) and (isinstance(apdu, ReadPropertyACK)):
            # find the datatype
            datatype = get_datatype(apdu.objectIdentifier[0], apdu.propertyIdentifier)
            if _debug: WebServerApplication._debug("    - datatype: %r", datatype)
            if not datatype:
                raise TypeError, "unknown datatype"

            # special case for array parts, others are managed by cast_out
            if issubclass(datatype, Array) and (apdu.propertyArrayIndex is not None):
                if apdu.propertyArrayIndex == 0:
                    value = apdu.propertyValue.cast_out(Unsigned)
                else:
                    value = apdu.propertyValue.cast_out(datatype.subtype)
            else:
                value = apdu.propertyValue.cast_out(datatype)
            if _debug: WebServerApplication._debug("    - value: %r", value)

            # assume primitive values for now, JSON would be better
            iocb.ioResponse = value

        # trigger the completion event
        iocb.ioComplete.set()

#
#   ThreadedHTTPequestHandler
#

class ThreadedHTTPequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler, Logging):

    def do_GET(self):
        if _debug: ThreadedHTTPequestHandler._debug("do_GET")

        # get the thread
        cur_thread = threading.current_thread()
        if _debug: ThreadedHTTPequestHandler._debug("    - cur_thread: %r", cur_thread)

        # parse query data and params to find out what was passed
        parsed_params = urlparse.urlparse(self.path)
        if _debug: ThreadedHTTPequestHandler._debug("    - parsed_params: %r", parsed_params)
        parsed_query = urlparse.parse_qs(parsed_params.query)
        if _debug: ThreadedHTTPequestHandler._debug("    - parsed_query: %r", parsed_query)

        # find the pieces
        args = parsed_params.path.split('/')
        if _debug: ThreadedHTTPequestHandler._debug("    - args: %r", args)

        try:
            _, addr, obj_type, obj_inst = args[:4]

            if not get_object_class(obj_type):
                raise ValueError, "unknown object type"

            obj_inst = int(obj_inst)

            # implement a default property, the bain of committee meetings
            if len(args) == 5:
                prop_id = args[4]
            else:
                prop_id = "presentValue"

            # look for its datatype, an easy way to see if the property is
            # appropriate for the object
            datatype = get_datatype(obj_type, prop_id)
            if not datatype:
                raise ValueError, "invalid property for object type"

            # build a request
            request = ReadPropertyRequest(
                objectIdentifier=(obj_type, obj_inst),
                propertyIdentifier=prop_id,
                )
            request.pduDestination = Address(addr)

            if len(args) == 6:
                request.propertyArrayIndex = int(args[5])
            if _debug: ThreadedHTTPequestHandler._debug("    - request: %r", request)

            # build an IOCB, save the request
            iocb = IOCB()
            iocb.ioRequest = request

            # give it to the application to send
            thisApplication.request(request, iocb)

            # wait for the response
            iocb.ioComplete.wait()

            # filter out errors and aborts
            if isinstance(iocb.ioResponse, Error):
                result = { "error": str(iocb.ioResponse) }
            elif isinstance(iocb.ioResponse, AbortPDU):
                result = { "abort": str(iocb.ioResponse) }
            else:
                result = { "value": iocb.ioResponse }

        except Exception, err:
            ThreadedHTTPequestHandler._exception("exception: %r", err)
            result = { "exception": str(err) }

        # write the result
        simplejson.dump(result, self.wfile)

class ThreadedTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    pass

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

    if _debug: _log.debug("initialization")

    # assume we don't have a server yet
    server = None

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
    if _debug: _log.debug("    - addr: %r", addr)

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

    # set the property value to be just the bits
    thisDevice.protocolServicesSupported = pss.value

    # make a simple application
    thisApplication = WebServerApplication(thisDevice, addr)

    # local host, custom port
    HOST, PORT = "", 9000

    server = ThreadedTCPServer((HOST, PORT), ThreadedHTTPequestHandler)
    if _debug: _log.debug("    - server: %r", server)

    # Start a thread with the server -- that thread will then start a thread for each request
    server_thread = threading.Thread(target=server.serve_forever)
    if _debug: _log.debug("    - server_thread: %r", server_thread)

    # exit the server thread when the main thread terminates
    server_thread.daemon = True
    server_thread.start()

    if _debug: _log.debug("running")

    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)

finally:
    if server:
        server.shutdown()

    if _debug: _log.debug("finally")
