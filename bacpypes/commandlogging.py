#!/usr/bin/python

"""
Command Logging
"""

import types
import logging
import cStringIO

from debugging import DebugContents, Logging, ModuleLogger
from comm import PDU, Client, Server

# some debugging
_debug = 0
_log = ModuleLogger(globals())

#
#   LoggingFormatter
#

class LoggingFormatter(logging.Formatter):

    def __init__(self):
        logging.Formatter.__init__(self, logging.BASIC_FORMAT, None)
        
    def format(self, record):
        try:
            # use the basic formatting
            msg = logging.Formatter.format(self, record) + '\n'
            
            # look for detailed arguments
            for arg in record.args:
                if isinstance(arg, DebugContents):
                    if msg:
                        sio = cStringIO.StringIO()
                        sio.write(msg)
                        msg = None
                    sio.write("    %r\n" % (arg,))
                    arg.DebugContents(indent=2, file=sio)
                    
            # get the message from the StringIO buffer
            if not msg:
                msg = sio.getvalue()
        
            # trim off the last '\n'
            msg = msg[:-1]
        except Exception, e:
            msg = "LoggingFormatter exception: " + str(e)
        
        return msg
        
#
#   ConsoleLogHandler
#

def ConsoleLogHandler(loggerRef='', level=logging.DEBUG):
    """Add a stream handler to stderr with our custom formatter to a logger."""
    if isinstance(loggerRef, logging.Logger):
        pass

    elif isinstance(loggerRef, types.StringType):
        # check for root
        if not loggerRef:
            loggerRef = _log

        # check for a valid logger name
        elif loggerRef not in logging.Logger.manager.loggerDict:
            raise RuntimeError, "not a valid logger name: %r" % (loggerRef,)

        # get the logger
        loggerRef = logging.getLogger(loggerRef)

    else:
        raise RuntimeError, "not a valid logger reference: %r" % (loggerRef,)

    # see if this (or its parent) is a module level logger
    if hasattr(loggerRef, 'globs'):
        loggerRef.globs['_debug'] += 1
    elif hasattr(loggerRef.parent, 'globs'):
        loggerRef.parent.globs['_debug'] += 1

    # make a debug handler
    hdlr = logging.StreamHandler()
    hdlr.setLevel(level)

    # use our formatter
    hdlr.setFormatter(LoggingFormatter())

    # add it to the logger
    loggerRef.addHandler(hdlr)

    # make sure the logger has at least this level
    loggerRef.setLevel(level)

#
#   LoggingHandler
#

class LoggingHandler(logging.Handler):

    def __init__(self, commander, destination, loggerName):
        logging.Handler.__init__(self, logging.DEBUG)
        self.setFormatter(LoggingFormatter())
        
        # save where this stuff goes
        self.commander = commander
        self.destination = destination
        self.loggerName = loggerName
        
    def emit(self, record):
        # use the basic formatting
        msg = self.format(record) + '\n'

        # tell the commander
        self.commander.request(PDU(msg, destination=self.destination))

#
#   commandlogging
#

class commandlogging(Logging):

    def __init__(self):
        if _debug: commandlogging._debug("__init__")
        
        # handlers, self.handlers[addr][logger] = handler
        self.handlers = {}
        
    def process_pdu(self, pdu):
        if _debug: commandlogging._debug("process_pdu %r", pdu)
        
        # get the address, find the list of handlers
        addr = pdu.pduSource
        if addr not in self.handlers:
            handlers = self.handlers[addr] = {}
        else:
            handlers = self.handlers[addr]
            
        args = pdu.pduData.strip().split()
        
        # get the +/- and logger name
        if (len(pdu.pduData) > 1):
            cmd, loggerName = pdu.pduData[0], pdu.pduData[1:-1]
        else:
            cmd, loggerName = '?', ''
        
        # get the logger name and logger
        if len(args) > 1:
            loggerName = args[1]
            if loggerName in logging.Logger.manager.loggerDict:
                logger = logging.getLogger(loggerName)
            else:
                logger = None
        else:
            loggerName = '__root__'
            logger = logging.getLogger()
        
        if not args:
            response = '-'
            
        elif args[0] == '?':
            if len(args) == 1:
                if not handlers:
                    response = 'no handlers'
                else:
                    response = "handlers: " + ', '.join(loggerName or 'root' for loggerName in handlers)
            elif not logger:
                response = 'not a valid logger name'
            elif loggerName in handlers:
                response = 'yes'
            else:
                response = 'no'
            
        elif args[0] == '+':
            if not logger:
                response = 'not a valid logger name'
            elif loggerName in handlers:
                response = loggerName + ' already has a handler'
            else:
                handler = LoggingHandler(self, addr, loggerName)
                handlers[loggerName] = handler
                
                # add it to the logger
                logger.addHandler(handler)
                if not addr:
                    response = "handler to %s added" % (loggerName,)
                else:
                    response = "handler from %s to %s added" % (addr, loggerName)
            
        elif args[0] == '-':
            if not logger:
                response = 'not a valid logger name'
            elif loggerName not in handlers:
                response = 'no handler for ' + loggerName
            else:
                handler = handlers[loggerName]
                del handlers[loggerName]
                
                # remove it from the logger
                logger.removeHandler(handler)
                if not addr:
                    response = "handler to %s removed" % (loggerName,)
                else:
                    response = "handler from %s to %s removed" % (addr, loggerName)

        else:
            if _debug: commandlogging._warning("bad command %r", pdu.pduData)
            response = 'bad command'
        
        # return the response
        return PDU(response+'\n', destination=pdu.pduSource)

#
#   CommandLoggingServer
#

class CommandLoggingServer(commandlogging, Server, Logging):

    def __init__(self):
        if _debug: CommandLoggingServer._debug("__init__")
        commandlogging.__init__(self)
        
    def indication(self, pdu):
        if _debug: CommandLoggingServer._debug("indication %r", pdu)
        resp = self.process_pdu(pdu)
        self.response(resp)

#
#   CommandLoggingClient
#

class CommandLoggingClient(commandlogging, Client, Logging):

    def __init__(self):
        if _debug: CommandLoggingClient._debug("__init__")
        commandlogging.__init__(self)
        
    def confirmation(self, pdu):
        if _debug: CommandLoggingClient._debug("confirmation %r", pdu)
        resp = self.process_pdu(pdu)
        self.request(resp)

