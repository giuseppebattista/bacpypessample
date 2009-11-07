#!/usr/bin/env python

"""
ConsoleCommunications Module
"""

import sys
import asyncore
import types
import os
import gc
import readline
import signal
import cmd
import logging

from Exceptions import *
from Debugging import Logging, FunctionLogging

from Core import stop, deferred
from Task import OneShotFunction
from CommunicationsCore import PDU, Client, Server, Bind
from CommandLogging import ConsoleLogHandler, CommandLoggingServer

from threading import Thread
from CSIO import IOCB, IOController, COMPLETED, ABORTED

# some debugging
_log = logging.getLogger(__name__)
_log.setLevel(logging.WARNING)

try:
    asyncore.file_dispatcher
except:
    class _barf: pass
    asyncore.file_dispatcher = _barf
    
#
#   ConsoleClient
#

class ConsoleClient(asyncore.file_dispatcher, Client, Logging):

    def __init__(self, cid=None):
        ConsoleClient._debug("__init__ cid=%r", cid)
        asyncore.file_dispatcher.__init__(self, sys.stdin)
        Client.__init__(self, cid)
        
    def readable(self):
        return True     # We are always happy to read

    def writable(self):
        return False    # we don't have anything to write
        
    def handle_read(self):
        deferred(ConsoleClient._debug, "handle_read")
        data = sys.stdin.read()
        deferred(ConsoleClient._debug, "    - data: %r", data)
        deferred(self.Request, PDU(data))

    def Confirmation(self, pdu):
        deferred(ConsoleClient._debug, "Confirmation %r", pdu)
        try:
#            print pdu.pduData,
#            sys.stdout.flush()
            sys.stdout.write(pdu.pduData)
        except Exception, e:
            ConsoleClient._exception("Confirmation sys.stdout.write exception: %r", e)

#
#   ConsoleServer
#

class ConsoleServer(asyncore.file_dispatcher, Server, Logging):

    def __init__(self, sid=None):
        ConsoleServer._debug("__init__ sid=%r", sid)
        asyncore.file_dispatcher.__init__(self, sys.stdin)
        Server.__init__(self, sid)
        
    def readable(self):
        return True     # We are always happy to read

    def writable(self):
        return False    # we don't have anything to write
        
    def handle_read(self):
        deferred(ConsoleServer._debug, "handle_read")
        data = sys.stdin.read()
        deferred(ConsoleServer._debug, "    - data: %r", data)
        deferred(self.Response, PDU(data))

    def Indication(self, pdu):
        deferred(ConsoleServer._debug, "Indication %r", pdu)
        try:
            sys.stdout.write(pdu.pduData)
        except Exception, e:
            ConsoleServer._exception("Indication sys.stdout.write exception: %r", e)

#
#   ConsoleLogging
#

class ConsoleLogging(CommandLoggingServer):

    def __init__(self):
        ConsoleLogging._debug("__init__")
        CommandLoggingServer.__init__(self)
        
        self.console = ConsoleClient()
        Bind(self.console, self)

#
#   ConsoleSignalInterrupt
#

@FunctionLogging
def ConsoleSignalInterrupt(*args):
    _log.debug("ConsoleSignalInterrupt %r", args)
    sys.stderr.write("Keyboard interrupt trapped - use EOF to end\n")
    
#
#   ConsoleCmd
#

class ConsoleCmd(cmd.Cmd, Thread, IOController, Logging):

    def __init__(self, prompt="> "):
        ConsoleCmd._debug("__init__")
        
        cmd.Cmd.__init__(self)
        self.prompt = prompt
        
        Thread.__init__(self, name="ConsoleCmd")
        IOController.__init__(self)
        
        # gc counters
        self.type2count = {}
        self.type2all = {}
        
        # logging handlers
        self.handlers = {}
        
        # set a INT signal handler, ^C will only get sent to the 
        # main thread and there's no way to break the readline
        # call initiated by this thread - sigh
        signal.signal(signal.SIGINT, ConsoleSignalInterrupt)

        # let it run
        self.start()
        
    def run(self):
        ConsoleCmd._debug("run")
        self.cmdloop()
        stop()
        ConsoleCmd._debug("    - done running")
    
    def onecmd(self, cmdString):
        ConsoleCmd._debug('onecmd %r', cmdString)
        
        # create an IO request
        iocb = IOCB(cmdString)
        
        # post it to the main thread asynchronously
        OneShotFunction(self.ProcessIO, iocb)
        ConsoleCmd._debug('    - deferred')
        
        # wait for it to complete
        iocb.Wait()
        ConsoleCmd._debug('    - iocb: %r', iocb)
        
        # check the result
        if iocb.ioState == COMPLETED:
            return iocb.ioResponse
        elif iocb.ioState == ABORTED:
            raise iocb.ioError
        else:
            raise RuntimeError, "invalid state"
            
    def ProcessIO(self, iocb):
        ConsoleCmd._debug('ProcessIO %r', iocb)
        
        # let the real command run, return the result
        try:
            rslt = cmd.Cmd.onecmd(self, iocb.args[0])
            self.CompleteIO(iocb, rslt)
        except Exception, e:
            ConsoleCmd._exception("exception: %r", e)
            self.AbortIO(iocb, e)

    #-----
    
    def do_gc(self, args):
        """gc - print out garbage collection information"""
        
        # snapshot of counts
        type2count = {}
        type2all = {}
        for o in gc.get_objects():
            if type(o) == types.InstanceType:
                type2count[o.__class__] = type2count.get(o.__class__,0) + 1
                type2all[o.__class__] = type2all.get(o.__class__,0) + sys.getrefcount(o)
            
        # count the things that have changed
        ct = [ ( t.__module__
            , t.__name__
            , type2count[t]
            , type2count[t] - self.type2count.get(t,0)
            , type2all[t] - self.type2all.get(t,0)
            ) for t in type2count.iterkeys()
            ]
            
        # ready for the next time
        self.type2count = type2count
        self.type2all = type2all
        
        fmt = "%-30s %-30s %6s %6s %6s"
        print fmt % ("Module", "Type", "Count", "dCount", "dRef")
        
        # sorted by count
        ct.sort(lambda x, y: cmp(y[2], x[2]))
        for i in range(min(10,len(ct))):
            m, n, c, delta1, delta2 = ct[i]
            print fmt % (m, n, c, delta1, delta2)
        print
            
        print fmt % ("Module", "Type", "Count", "dCount", "dRef")
        
        # sorted by module and class
        ct.sort()
        for m, n, c, delta1, delta2 in ct:
            if delta1 or delta2:
                print fmt % (m, n, c, delta1, delta2)
        print
            
    def do_bugin(self, args):
        """bugin [ <logger> ]  - add a console logging handler to a logger"""
        args = args.split()
        ConsoleCmd._debug("do_bugin %r", args)
        
        # get the logger name and logger
        if args:
            loggerName = args[0]
            if loggerName in logging.Logger.manager.loggerDict:
                logger = logging.getLogger(loggerName)
            else:
                logger = None
        else:
            loggerName = '__root__'
            logger = logging.getLogger()
        
        # add a logging handler
        if not logger:
            print 'not a valid logger name'
        elif loggerName in self.handlers:
            print loggerName, 'already has a handler'
        else:
            handler = ConsoleLogHandler(logger)
            self.handlers[loggerName] = handler
            print "handler to", loggerName, "added"
        print
        
    def do_bugout(self, args):
        """bugout [ <logger> ]  - remove a console logging handler from a logger"""
        args = args.split()
        ConsoleCmd._debug("do_bugout %r", args)
        
        # get the logger name and logger
        if args:
            loggerName = args[0]
            if loggerName in logging.Logger.manager.loggerDict:
                logger = logging.getLogger(loggerName)
            else:
                logger = None
        else:
            loggerName = '__root__'
            logger = logging.getLogger()
        
        # remove the logging handler
        if not logger:
            print 'not a valid logger name'
        elif not loggerName in self.handlers:
            print 'no handler for', loggerName
        else:
            handler = self.handlers[loggerName]
            del self.handlers[loggerName]
            
            # remove it from the logger
            logger.removeHandler(handler)
            print "handler to", loggerName, "removed"
        print
        
    def do_buggers(self, args):
        """buggers  - list the console logging handlers"""
        args = args.split()
        ConsoleCmd._debug("do_buggers %r", args)
        
        if not self.handlers:
            print "no handlers"
        else:
            print "handlers:", ', '.join(loggerName or '__root__' for loggerName in self.handlers)
            
        loggers = logging.Logger.manager.loggerDict.keys()
        loggers.sort()
        for loggerName in loggers:
            if args and (not args[0] in loggerName):
                continue
                
            if loggerName in self.handlers:
                print '*', loggerName
            else:
                print ' ', loggerName
        print
        
    #-----
    
    def do_exit(self, args):
        """Exits from the console."""
        ConsoleCmd._debug("do_exit %r", args)
        return -1

    def do_EOF(self, args):
        """Exit on system end of file character"""
        ConsoleCmd._debug("do_EOF %r", args)
        return self.do_exit(args)

    def do_shell(self, args):
        """Pass command to a system shell when line begins with '!'"""
        os.system(args)

    def do_help(self, args):
        """Get help on commands
        'help' or '?' with no arguments prints a list of commands for which help is available
        'help <command>' or '? <command>' gives help on <command>
        """
        ## The only reason to define this method is for the help text in the doc string
        cmd.Cmd.do_help(self, args)

    def preloop(self):
        """Initialization before prompting user for commands.
        Despite the claims in the Cmd documentaion, Cmd.preloop() is not a stub.
        """
        cmd.Cmd.preloop(self)   ## sets up command completion
#        self._locals  = {}      ## Initialize execution namespace for user
#        self._globals = {}

        try:
            readline.read_history_file(sys.argv[0]+".history")
        except Exception, e:
            if not isinstance(e, IOError):
                print "history error:", e
            
    def postloop(self):
        """Take care of any unfinished business.
        Despite the claims in the Cmd documentaion, Cmd.postloop() is not a stub.
        """
        try:
            readline.write_history_file(sys.argv[0]+".history")
        except Exception, e:
            print "history error:", e
            
        cmd.Cmd.postloop(self)   ## Clean up command completion
        print "Exiting..."
        stop()

    def precmd(self, line):
        """ This method is called after the line has been input but before
            it has been interpreted. If you want to modifdy the input line
            before execution (for example, variable substitution) do it here.
        """
        return line.strip()

    def postcmd(self, stop, line):
        """If you want to stop the console, return something that evaluates to true.
        If you want to do some post command processing, do it here.
        """
        return stop

    def emptyline(self):
        """Do nothing on empty input line"""
        pass

#    def default(self, line):
#        """Called on an input line when the command prefix is not recognized.
#        In that case we execute the line as Python code.
#        """
#        try:
#            exec(line) in self._locals, self._globals
#        except Exception, e:
#            print e.__class__, ":", e
#            print

