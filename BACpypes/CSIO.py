#!/usr/bin/python

"""
IO Module
"""

import sys
import logging

import time
import threading
import cPickle
from bisect import bisect_left
from collections import deque

from Debugging import DebugContents, Logging, FunctionLogging
from Singleton import SingletonLogging

from Core import deferred
from CommunicationsCore import PDU, Client, Bind
from UDPCommunications import UDPDirector
from Task import FunctionTask

# import CSStat - uncomment for IOQueue statistics

# some debugging
_log = logging.getLogger(__name__)
_commlog = logging.getLogger(__name__ + "._commlog")

#
#   IOCB states
#

IDLE = 0        # has not been submitted
PENDING = 1     # queued, waiting for processing
ACTIVE = 2      # being processed
COMPLETED = 3   # finished
ABORTED = 4     # finished in a bad way

_stateNames = {0:'IDLE', 1:'PENDING', 2:'ACTIVE', 3:'COMPLETED', 4:'ABORTED'}

# dictionary of local controllers
_localControllers = {}
_proxyServer = None

# special abort error
TimeoutError = RuntimeError("timeout")

#
#   IOCB - Input Output Control Block
#

_identNext = 1

class IOCB(DebugContents, Logging):

    _debugContents = \
        ( 'args', 'kwargs'
        , 'ioState', 'ioResponse-', 'ioError'
        , 'ioController', 'ioServerRef', 'ioControllerRef', 'ioClientID', 'ioClientAddr'
        , 'ioComplete', 'ioCallback+', 'ioQueue', 'ioPriority', 'ioTimeout'
        )
        
    def __init__(self, *args, **kwargs):
        IOCB._debug("__init__ %r %r", args, kwargs)
        global _identNext

        # generate a unique identity for this block
        self.ioID = _identNext
        _identNext += 1
        
        # save the request parameters
        self.args = args
        self.kwargs = kwargs

        # start with an idle request
        self.ioState = IDLE
        self.ioResponse = None
        self.ioError = None

        # blocks are bound to a controller
        self.ioController = None

        # blocks could reference a local or remote server
        self.ioServerRef = None
        self.ioControllerRef = None
        self.ioClientID = None
        self.ioClientAddr = None

        # each block gets a completion event
        self.ioComplete = threading.Event()
        self.ioComplete.clear()

        # applications can set a callback functions
        self.ioCallback = []

        # request is not currently queued
        self.ioQueue = None

        # extract the priority if it was given
        self.ioPriority = kwargs.get('_priority', 0)
        if '_priority' in kwargs:
            IOCB._debug("    - ioPriority: %r", self.ioPriority)
            del kwargs['_priority']
        
        # request has no timeout
        self.ioTimeout = None

    def AddCallback(self, fn, *args, **kwargs):
        """Pass a function to be called when IO is complete."""
        IOCB._debug("AddCallback %r %r %r", fn, args, kwargs)

        # store it
        self.ioCallback.append((fn, args, kwargs))

        # already complete?
        if self.ioComplete.isSet():
            self.Trigger()
        
    def Wait(self, *args):
        """Wait for the completion event to be set."""
        IOCB._debug("Wait %r", args)
        
        # waiting from a non-daemon thread could be trouble
        self.ioComplete.wait(*args)

    def Trigger(self):
        """Set the event and make the callback."""
        IOCB._debug("Trigger")

        # if it's queued, remove it from its queue
        if self.ioQueue:
            IOCB._debug("    - dequeue")
            self.ioQueue.Remove(self)

        # if there's a timer, cancel it
        if self.ioTimeout:
            IOCB._debug("    - cancel timeout")
            self.ioTimeout.SuspendTask()

        # set the completion event
        self.ioComplete.set()

        # make the callback
        for fn, args, kwargs in self.ioCallback:
            IOCB._debug("    - callback fn: %r %r %r", fn, args, kwargs)
            fn(self, *args, **kwargs)

    def Complete(self, msg):
        """Called to complete a transaction, usually when ProcessIO has
        shipped the IOCB off to some other thread or function."""
        IOCB._debug("Complete %r", msg)

        if self.ioController:
            # pass to controller
            self.ioController.CompleteIO(self, msg)
        else:
            # just fill in the data
            self.ioState = COMPLETED
            self.ioResponse = msg
            self.Trigger()

    def Abort(self, err):
        """Called by a client to abort a transaction."""
        IOCB._debug("Abort %r", err)

        if self.ioController:
            # pass to controller
            self.ioController.AbortIO(self, err)
        elif self.ioState < COMPLETED:
            # just fill in the data
            self.ioState = ABORTED
            self.ioError = err
            self.Trigger()

    def SetTimeout(self, delay, err=TimeoutError):
        """Called to set a transaction timer."""
        IOCB._debug("SetTimeout %r err=%r", delay, err)

        # if one has already been created, cancel it
        if self.ioTimeout:
            self.ioTimeout.SuspendTask()
        else:
            self.ioTimeout = FunctionTask(self.Abort, err)

        # (re)schedule it
        self.ioTimeout.InstallTask(time.time() + delay)

    def __repr__(self):
        xid = id(self)
        if (xid < 0): xid += (1L << 32)

        sname = self.__module__ + '.' + self.__class__.__name__
        desc = "(%d)" % (self.ioID)

        return '<' + sname + desc + ' instance at 0x%08x' % (xid,) + '>'

#
#   StringIOCB
#

class StringIOCB(IOCB, Logging):

    def __str__(self):
        if self.ioState == COMPLETED:
            s = str(self.ioResponse)
        elif self.ioState == ABORTED:
            s = "Error: " + str(self.ioError)
        else:
            s = "Error: invalid state %s" % (self.ioState,)
        StringIOCB._debug("__str__ : %r", s)
    
        return s

#
#   IOChainMixIn
#

class IOChainMixIn(DebugContents, Logging):

    _debugContents = ( 'ioChain++', )
    
    def __init__(self, iocb):
        IOChainMixIn._debug("__init__ %r", iocb)

        # save a refence back to the iocb
        self.ioChain = iocb

        # set the callback to follow the chain
        self.AddCallback(self.ChainCallback)

        # if we're not chained, there's no notification to do
        if not self.ioChain:
            return

        # this object becomes its controller
        iocb.ioController = self

        # consider the parent active
        iocb.ioState = ACTIVE

        try:
            IOChainMixIn._debug("    - encoding")
                
            # let the derived class set the args and kwargs
            self.Encode()
            
            IOChainMixIn._debug("    - encode complete")
        except:
            # extract the error and abort the request
            err = sys.exc_info()[1]
            IOChainMixIn._exception("    - encoding exception: %r", err)
                
            iocb.Abort(err)

    def ChainCallback(self, iocb):
        """Callback when this iocb completes."""
        IOChainMixIn._debug("ChainCallback %r", iocb)

        # if we're not chained, there's no notification to do
        if not self.ioChain:
            return

        # refer to the chained iocb
        iocb = self.ioChain

        try:
            IOChainMixIn._debug("    - decoding")
                
            # let the derived class transform the data
            self.Decode()
            
            IOChainMixIn._debug("    - decode complete")
        except:
            # extract the error and abort
            err = sys.exc_info()[1]
            IOChainMixIn._exception("    - decoding exception: %r", err)
                
            iocb.ioState = ABORTED
            iocb.ioError = err

        # break the references
        self.ioChain = None
        iocb.ioController = None

        # notify the client
        iocb.Trigger()

    def AbortIO(self, iocb, err):
        """Forward the abort downstream."""
        IOChainMixIn._debug("AbortIO %r %r", iocb, err)

        # make sure we're being notified of an abort request from
        # the iocb we are chained from
        if iocb is not self.ioChain:
            raise RuntimeError, "broken chain"

        # call my own Abort(), which may forward it to a controller or
        # be overridden by IOGroup
        self.Abort(err)

    def Encode(self):
        """Hook to transform the request, called when this IOCB is
        chained."""
        IOChainMixIn._debug("Encode (pass)")

        # by default do nothing, the arguments have already been supplied

    def Decode(self):
        """Hook to transform the response, called when this IOCB is
        completed."""
        IOChainMixIn._debug("Decode")

        # refer to the chained iocb
        iocb = self.ioChain

        # if this has completed successfully, pass it up
        if self.ioState == COMPLETED:
            IOChainMixIn._debug("    - completed: %r", self.ioResponse)
                
            # change the state and transform the content
            iocb.ioState = COMPLETED
            iocb.ioResponse = self.ioResponse

        # if this aborted, pass that up too
        elif self.ioState == ABORTED:
            IOChainMixIn._debug("    - aborted: %r", self.ioError)
                
            # change the state
            iocb.ioState = ABORTED
            iocb.ioError = self.ioError

        else:
            raise RuntimeError, "invalid state: %d" % (self.ioState,)

#
#   IOChain
#

class IOChain(IOCB, IOChainMixIn):

    def __init__(self, chain, *args, **kwargs):
        """Initialize a chained control block."""
        IOChain._debug("__init__ %r %r %r", chain, args, kwargs)
        
        # initialize IOCB part to pick up the ioID
        IOCB.__init__(self, *args, **kwargs)
        IOChainMixIn.__init__(self, chain)
        
#
#   IOGroup
#

class IOGroup(IOCB, DebugContents, Logging):

    _debugContents = ('ioMembers',)
        
    def __init__(self):
        """Initialize a group."""
        IOGroup._debug("__init__")
        IOCB.__init__(self)

        # start with an empty list of members
        self.ioMembers = []

        # start out being done.  When an IOCB is added to the 
        # group that is not already completed, this state will 
        # change to PENDING.
        self.ioState = COMPLETED
        self.ioComplete.set()

    def Add(self, iocb):
        """Add an IOCB to the group, you can also add other groups."""
        IOGroup._debug("Add %r", iocb)

        # add this to our members
        self.ioMembers.append(iocb)

        # assume all of our members have not completed yet
        self.ioState = PENDING
        self.ioComplete.clear()

        # when this completes, call back to the group.  If this
        # has already completed, it will trigger
        iocb.AddCallback(self.GroupCallback)

    def GroupCallback(self, iocb):
        """Callback when a child iocb completes."""
        IOGroup._debug("GroupCallback %r", iocb)

        # check all the members
        for iocb in self.ioMembers:
            if not iocb.ioComplete.isSet():
                IOGroup._debug("    - waiting for child: %r", iocb)
                break
        else:
            IOGroup._debug("    - all children complete")
            # everything complete
            self.ioState = COMPLETED
            self.Trigger()

    def Abort(self, err):
        """Called by a client to abort all of the member transactions.
        When the last pending member is aborted the group callback
        function will be called."""
        IOGroup._debug("Abort %r", err)

        # change the state to reflect that it was killed
        self.ioState = ABORTED
        self.ioError = err

        # abort all the members
        for iocb in self.ioMembers:
            iocb.Abort(err)

        # notify the client
        self.Trigger()

#
#   IOQueue - Input Output Queue
#

class IOQueue(Logging):

    def __init__(self, name):
        IOQueue._debug("__init__ %r", name)

        self.notempty = threading.Event()
        self.notempty.clear()
        
        self.queue = []
#       self.queuesize = CSStat.Statistics(name + "/Queue",load=1)
#       self.queuesize.Record( 0, time.time() )

    def Put(self, iocb):
        """Add an IOCB to a queue.  This is usually called by the function
        that filters requests and passes them out to the correct processing
        thread."""
        IOQueue._debug("Put %r", iocb)

        # requests should be pending before being queued
        if iocb.ioState != PENDING:
            raise RuntimeError, "invalid state transition"

        # save that it might have been empty
        wasempty = not self.notempty.isSet()

        # add the request to the end of the list of iocb's at same priority
        priority = iocb.ioPriority
        item = (priority, iocb)
        self.queue.insert(bisect_left(self.queue, (priority+1,)), item)

        # point the iocb back to this queue
        iocb.ioQueue = self

        # record the new length
#       self.queuesize.Record( len(self.queue), time.time() )

        # set the event, queue is no longer empty
        self.notempty.set()

        return wasempty

    def Get(self, block=1, delay=None):
        """Get a request from a queue, optionally block until a request
        is available."""
        IOQueue._debug("Get block=%r delay=%r", block, delay)

        # if the queue is empty and we do not block return None
        if not block and not self.notempty.isSet():
            return None

        # wait for something to be in the queue
        if delay:
            self.notempty.wait(delay)
            if not self.notempty.isSet():
                return None
        else:
            self.notempty.wait()

        # extract the first element
        priority, iocb = self.queue[0]
        del self.queue[0]
        iocb.ioQueue = None

        # if the queue is empty, clear the event
        qlen = len(self.queue)
        if not qlen:
            self.notempty.clear()

        # record the new length
#       self.queuesize.Record( qlen, time.time() )

        # return the request
        return iocb

    def Remove(self, iocb):
        """Remove a control block from the queue, called if the request
        is canceled/aborted."""
        IOQueue._debug("Remove %r", iocb)

        # remove the request from the queue
        for i, item in enumerate(self.queue):
            if iocb is item[1]:
                IOQueue._debug("    - found at %d", i)
                del self.queue[i]

                # if the queue is empty, clear the event
                qlen = len(self.queue)
                if not qlen:
                    self.notempty.clear()

                # record the new length
                # self.queuesize.Record( qlen, time.time() )
                break
        else:
            IOQueue._debug("    - not found")

    def Abort(self, err):
        """Abort all of the control blocks in the queue."""
        IOQueue._debug("Abort %r", err)

        # send aborts to all of the members
        try:
            for iocb in self.queue:
                iocb.ioQueue = None
                iocb.Abort(err)

            # flush the queue
            self.queue = []

            # the queue is now empty, clear the event
            self.notempty.clear()

            # record the new length
#           self.queuesize.Record( 0, time.time() )
        except ValueError:
            pass

#
#   IOController
#

class IOController(Logging):

    def __init__(self, name=None):
        """Initialize a controller."""
        IOController._debug("__init__ name=%r", name)

        # register the name
        if name is not None:
            if name in _localControllers:
                raise RuntimeError, "already a local controller called '%s': %r" % (name, _localControllers[name])
            _localControllers[name] = self

    def Abort(self, err):
        """Abort all requests, no default implementation."""
        pass

    def RequestIO(self, iocb):
        """Called by a client to start processing a request."""
        IOController._debug("RequestIO %r", iocb)

        # bind the iocb to this controller
        iocb.ioController = self

        try:
            # hopefully there won't be an error
            err = None

            # change the state
            iocb.ioState = PENDING

            # let derived class figure out how to process this
            self.ProcessIO(iocb)
        except:
            # extract the error
            err = sys.exc_info()[1]

        # if there was an error, abort the request
        if err:
            self.AbortIO(iocb, err)

    def ProcessIO(self, iocb):
        """Figure out how to respond to this request.  This must be
        provided by the derived class."""
        raise NotImplementedError, "IOController must implement ProcessIO()"

    def ActiveIO(self, iocb):
        """Called by a handler to notify the controller that a request is
        being processed."""
        IOController._debug("ActiveIO %r", iocb)

        # requests should be idle or pending before coming active
        if (iocb.ioState != IDLE) and (iocb.ioState != PENDING):
            raise RuntimeError, "invalid state transition (currently %d)" % (iocb.ioState,)

        # change the state
        iocb.ioState = ACTIVE

    def CompleteIO(self, iocb, msg):
        """Called by a handler to return data to the client."""
        IOController._debug("CompleteIO %r %r", iocb, msg)

        # if it completed, leave it alone
        if iocb.ioState == COMPLETED:
            pass

        # if it already aborted, leave it alone
        elif iocb.ioState == ABORTED:
            pass

        else:
            # change the state
            iocb.ioState = COMPLETED
            iocb.ioResponse = msg

            # notify the client
            iocb.Trigger()

    def AbortIO(self, iocb, err):
        """Called by a handler or a client to abort a transaction."""
        IOController._debug("AbortIO %r %r", iocb, err)

        # if it completed, leave it alone
        if iocb.ioState == COMPLETED:
            pass

        # if it already aborted, leave it alone
        elif iocb.ioState == ABORTED:
            pass

        else:
            # change the state
            iocb.ioState = ABORTED
            iocb.ioError = err

            # notify the client
            iocb.Trigger()

#
#   IOQController
#

class IOQController(IOController, Logging):

    def __init__(self, name=None):
        """Initialize a queue controller."""
        IOQController._debug("__init__ name=%r", name)
        IOController.__init__(self, name)

        # not busy, create an IOQueue for iocb's requested when busy
        self.busy = False
        self.ioQueue = IOQueue(str(name) + "/Queue")
        
    def Abort(self, err):
        """Abort all pending requests."""
        IOQController._debug("Abort %r", err)
        if self.busy:
            IOQController._debug("    - busy before aborts")
        
        while True:
            iocb = self.ioQueue.Get()
            if not iocb:
                break
                
            # change the state
            iocb.ioState = ABORTED
            iocb.ioError = err

            # notify the client
            iocb.Trigger()

        if self.busy:
            IOQController._debug("    - busy after aborts")
            
    def RequestIO(self, iocb):
        """Called by a client to start processing a request."""
        IOQController._debug("RequestIO %r", iocb)

        # bind the iocb to this controller
        iocb.ioController = self

        # if we're busy, queue it
        if self.busy:
            iocb.ioState = PENDING
            self.ioQueue.Put(iocb)
            return
            
        try:
            # hopefully there won't be an error
            err = None
            self.busy = True

            # let derived class figure out how to process this
            self.ProcessIO(iocb)
        except:
            # extract the error
            err = sys.exc_info()[1]

        # if there was an error, abort the request
        if err:
            self.AbortIO(iocb, err)

    def ProcessIO(self, iocb):
        """Figure out how to respond to this request.  This must be
        provided by the derived class."""
        raise NotImplementedError, "IOController must implement ProcessIO()"

    def CompleteIO(self, iocb, msg):
        """Called by a handler to return data to the client."""
        IOQController._debug("CompleteIO %r %r", iocb, msg)

        # normal completion
        IOController.CompleteIO(self, iocb, msg)
        
        # no longer busy
        self.busy = False
        
        # look for more to do
        deferred(self._Trigger)

    def AbortIO(self, iocb, err):
        """Called by a handler or a client to abort a transaction."""
        IOQController._debug("AbortIO %r %r", iocb, err)

        # normal abort
        IOController.AbortIO(self, iocb, err)
        
        # no longer busy
        self.busy = False
        
        # look for more to do
        deferred(self._Trigger)

    def _Trigger(self):
        """Called after an iocb is processed."""
        
        # if we're busy or there is nothing to do, return
        if self.busy or (not self.ioQueue.queue):
            return
        
        # get the next iocb
        iocb = self.ioQueue.Get()
        
        try:
            # hopefully there won't be an error
            err = None
            self.busy = True

            # let derived class figure out how to process this
            self.ProcessIO(iocb)
        except:
            # extract the error
            err = sys.exc_info()[1]

        # if there was an error, abort the request
        if err:
            self.AbortIO(iocb, err)
            
        # if we're not busy, call again
        if not self.busy:
            deferred(self._Trigger)
        
#
#   IOProxy
#

class IOProxy(Logging):

    def __init__(self, controllerName, serverName=None, requestLimit=None):
        """Create a client.  It implements RequestIO like a controller, but
        passes requests on to a local controller or the IOProxy for processing."""
        IOProxy._debug("__init__ %r serverName=%r, requestLimit=%r", controllerName, serverName, requestLimit)
        
        # save the server reference
        self.ioControllerRef = controllerName
        self.ioServerRef = serverName

        # set a limit on how many requests can be submitted
        self.ioRequestLimit = requestLimit
        self.ioPending = set()
        self.ioBlocked = deque()

        # bind to a local controller if possible
        if not serverName:
            self.ioBind = _localControllers.get(controllerName, None)
            if self.ioBind:
                IOProxy._debug("    - local bind successful")
            else:
                IOProxy._debug("    - local bind deferred")
        else:
            self.ioBind = None
            IOProxy._debug("    - bind deferred")

    def RequestIO(self, iocb, urgent=False):
        """Called by a client to start processing a request."""
        global _proxyServer
        IOProxy._debug("RequestIO %r urgent=%r", iocb, urgent)

        # save the server and controller reference
        iocb.ioServerRef = self.ioServerRef
        iocb.ioControllerRef = self.ioControllerRef

        # check to see if it needs binding
        if not self.ioBind:
            # if the server is us, look for a local controller
            if not self.ioServerRef:
                self.ioBind = _localControllers.get(self.ioControllerRef, None)
                if not self.ioBind:
                    iocb.Abort("no local controller %s" % (self.ioControllerRef,))
                    return
                IOProxy._debug("    - local bind successful")
            else:
                if not _proxyServer:
                    _proxyServer = IOProxyServer()
                    
                self.ioBind = _proxyServer
                IOProxy._debug("    - proxy bind successful: %r", self.ioBind)

        # if this isn't urgent and there is a limit, see if we've reached it
        if (not urgent) and self.ioRequestLimit:
            # call back when this is completed
            iocb.AddCallback(self._Trigger)

            # check for the limit
            if len(self.ioPending) < self.ioRequestLimit:
                IOProxy._debug("    - cleared for launch")

                self.ioPending.add(iocb)
                self.ioBind.RequestIO(iocb)
            else:
                # save it for later
                IOProxy._debug("    - save for later")
                self.ioBlocked.append(iocb)
        else:
            # just pass it along
            self.ioBind.RequestIO(iocb)

    def _Trigger(self, iocb):
        """This has completed, remove it from the set of pending requests 
        and see if it's OK to start up the next one."""
        IOProxy._debug("_Trigger %r", iocb)

        if iocb not in self.ioPending:
            IOProxy._warning("iocb not pending: %r", iocb)
        else:
            self.ioPending.remove(iocb)
            
            # check to send another one
            if (len(self.ioPending) < self.ioRequestLimit) and self.ioBlocked:
                nextio = self.ioBlocked.popleft()
                IOProxy._debug("    - cleared for launch: %r", nextio)

                # this one is now pending
                self.ioPending.add(nextio)
                self.ioBind.RequestIO(nextio)

#
#   IOServer
#

PORT = 8002
SERVER_TIMEOUT = 60

class IOServer(IOController, Client, SingletonLogging):

    def __init__(self, addr=('',PORT)):
        """Initialize the remote IO handler."""
        IOServer._debug("__init__ %r", addr)
        IOController.__init__(self)
        
        # create a UDP director
        self.server = UDPDirector(addr)
        Bind(self, self.server)
        
        # dictionary of IOCBs as a server
        self.remoteIOCB = {}

    def Confirmation(self, pdu):
        IOServer._debug('Confirmation %r', pdu)
        
        addr = pdu.pduSource
        request = pdu.pduData
        
        try:
            # parse the request
            request = cPickle.loads(request)
            _commlog.debug("S >>> " + str(addr) + " " + repr(request))

            # pick the message
            if (request[0] == 0):
                self.NewIOCB(addr, *request[1:])
            elif (request[0] == 1):
                self.CompleteIOCB(addr, *request[1:])
            elif (request[0] == 2):
                self.AbortIOCB(addr, *request[1:])
        except:
            # extract the error
            err = sys.exc_info()[1]
            IOServer._exception("error %r processing %r from %r", err, request, addr)

    def Callback(self, iocb):
        """Callback when an iocb is completed by a local controller and the
        result needs to be sent back to the client."""
        IOServer._debug("Callback %r", iocb)

        # make sure it's one of ours
        if not self.remoteIOCB.has_key(iocb):
            IOServer._warning("IOCB not owned by server: %r", iocb)
            return

        # get the client information
        clientID, clientAddr = self.remoteIOCB[iocb]

        # we're done with this
        del self.remoteIOCB[iocb]

        # build a response
        if iocb.ioState == COMPLETED:
            response = (1, clientID, iocb.ioResponse)
        elif iocb.ioState == ABORTED:
            response = (2, clientID, iocb.ioError)
        else:
            raise RuntimeError, "IOCB invalid state"

        _commlog.debug("S <<< " + str(clientAddr) + " " + repr(response))

        response = cPickle.dumps( response, 1 )

        # send it to the client
        self.Request(PDU(response, destination=clientAddr))

    def Abort(self, err):
        """Called by a local application to abort all transactions."""
        IOServer._debug("Abort %r", err)

        for iocb in self.remoteIOCB.keys():
            self.AbortIO(iocb, err)

    def AbortIO(self, iocb, err):
        """Called by a local client or a local controlled to abort a transaction."""
        IOServer._debug("AbortIO %r %r", iocb, err)

        # if it completed, leave it alone
        if iocb.ioState == COMPLETED:
            pass

        # if it already aborted, leave it alone
        elif iocb.ioState == ABORTED:
            pass

        elif self.remoteIOCB.has_key(iocb):
            # get the client information
            clientID, clientAddr = self.remoteIOCB[iocb]

            # we're done with this
            del self.remoteIOCB[iocb]

            # build an abort response
            response = (2, clientID, err)
            _commlog.debug("S <<< " + str(clientAddr) + " " + repr(response))

            response = cPickle.dumps( response, 1 )

            # send it to the client
            self.socket.sendto( response, clientAddr )
            
        else:
            IOServer._error("no reference to aborting iocb: %r", iocb)

        # change the state
        iocb.ioState = ABORTED
        iocb.ioError = err

        # notify the client
        iocb.Trigger()
                
    def NewIOCB(self, clientAddr, iocbid, controllerName, args, kwargs):
        """Called when the server receives a new request."""
        IOServer._debug("NewIOCB %r %r %r %r %r", clientAddr, iocbid, controllerName, args, kwargs)

        # look for a controller
        controller = _localControllers.get(controllerName, None)
        if not controller:
            # create a nice error message
            err = RuntimeError("no local controller '%s'" % (controllerName, ))

            # build an abort response
            response = (2, iocbid, err)
            _commlog.debug("S <<< " + str(clientAddr) + " " + repr(response))

            response = cPickle.dumps( response, 1 )

            # send it to the server
            self.Request(PDU(response, destination=clientAddr))
            
        else:
            # create an IOCB
            iocb = IOCB(*args, **kwargs)
            IOServer._debug("    - local IOCB %r bound to remote %r", iocb.ioID, iocbid)

            # save a reference to it
            self.remoteIOCB[iocb] = (iocbid, clientAddr)

            # make sure we're notified when it completes
            iocb.AddCallback(self.Callback)

            # pass it along
            controller.RequestIO(iocb)

    def AbortIOCB(self, addr, iocbid, err):
        """Called when the client or server receives an abort request."""
        IOServer._debug("AbortIOCB %r %r %r", addr, iocbid, err)

        # see if this came from a client
        for iocb in self.remoteIOCB.keys():
            clientID, clientAddr = self.remoteIOCB[iocb]
            if (addr == clientAddr) and (clientID == iocbid):
                break
        else:
            IOServer._error("no reference to aborting iocb %r from %r", iocbid, addr)
            return
        IOServer._debug("    - local IOCB %r bound to remote %r", iocb.ioID, iocbid)

        # we're done with this
        del self.remoteIOCB[iocb]

        # clear the callback, we already know
        iocb.ioCallback = []

        # tell the local controller about the abort
        iocb.Abort(err)
        
#
#   IOProxyServer
#

SERVER_TIMEOUT = 60

class IOProxyServer(IOController, Client, Logging):

    def __init__(self, addr=('', 0)):
        """Initialize the remote IO handler."""
        IOProxyServer._debug("__init__")
        IOController.__init__(self)
        
        # create a UDP director
        self.server = UDPDirector(addr)
        Bind(self, self.server)
        IOProxyServer._debug("    - bound to %r", self.server.socket.getsockname())
        
        # dictionary of IOCBs as a client
        self.localIOCB = {}

    def Confirmation(self, pdu):
        IOProxyServer._debug('Confirmation %r', pdu)
        
        addr = pdu.pduSource
        request = pdu.pduData
        
        try:
            # parse the request
            request = cPickle.loads(request)
            _commlog.debug("    >>> " + str(addr) + " " + repr(request))

            # pick the message
            if (request[0] == 1):
                self.CompleteIOCB(addr, *request[1:])
            elif (request[0] == 2):
                self.AbortIOCB(addr, *request[1:])
        except:
            # extract the error
            err = sys.exc_info()[1]
            IOProxyServer._exception("error %r processing %r from %r", err, request, addr)

    def ProcessIO(self, iocb):
        """Package up the local IO request and send it to the server."""
        IOProxyServer._debug("ProcessIO %r", iocb)

        # save a reference in our dictionary
        self.localIOCB[iocb.ioID] = iocb

        # start a default timer if one hasn't already been set
        if not iocb.ioTimeout:
            iocb.SetTimeout( SERVER_TIMEOUT, RuntimeError("no response from " + iocb.ioServerRef))

        # build a message
        request = (0, iocb.ioID, iocb.ioControllerRef, iocb.args, iocb.kwargs)
        _commlog.debug("    <<< " + str(iocb.ioServerRef) + " " + repr(request))

        request = cPickle.dumps( request, 1 )

        # send it to the server
        self.Request(PDU(request, destination=(iocb.ioServerRef, PORT)))

    def Abort(self, err):
        """Called by a local application to abort all transactions, local
        and remote."""
        IOProxyServer._debug("Abort %r", err)

        for iocb in self.localIOCB.values():
            self.AbortIO(iocb, err)

    def AbortIO(self, iocb, err):
        """Called by a local client or a local controlled to abort a transaction."""
        IOProxyServer._debug("AbortIO %r %r", iocb, err)

        # if it completed, leave it alone
        if iocb.ioState == COMPLETED:
            pass

        # if it already aborted, leave it alone
        elif iocb.ioState == ABORTED:
            pass

        elif self.localIOCB.has_key(iocb.ioID):
            # delete the dictionary reference
            del self.localIOCB[iocb.ioID]

            # build an abort request
            request = (2, iocb.ioID, err)
            _commlog.debug("    <<< " + str(iocb.ioServerRef) + " " + repr(request))

            request = cPickle.dumps( request, 1 )

            # send it to the server
            self.Request(PDU(request, destination=(iocb.ioServerRef, PORT)))
            
        else:
            raise RuntimeError, "no reference to aborting iocb: %r" % (iocb.ioID,)

        # change the state
        iocb.ioState = ABORTED
        iocb.ioError = err

        # notify the client
        iocb.Trigger()
                
    def CompleteIOCB(self, serverAddr, iocbid, msg):
        """Called when the client receives a response to a request."""
        IOProxyServer._debug("CompleteIOCB %r %r %r", serverAddr, iocbid, msg)

        # assume nothing
        iocb = None
        
        # make sure this is a local request
        if not self.localIOCB.has_key(iocbid):
            IOProxyServer._error("no reference to IOCB %r", iocbid)
            IOProxyServer._debug("    - localIOCB: %r", self.localIOCB)
        else:
            # get the iocb
            iocb = self.localIOCB[iocbid]

            # delete the dictionary reference
            del self.localIOCB[iocbid]

        if iocb:
            # change the state
            iocb.ioState = COMPLETED
            iocb.ioResponse = msg
    
            # notify the client
            iocb.Trigger()

    def AbortIOCB(self, addr, iocbid, err):
        """Called when the client or server receives an abort request."""
        IOProxyServer._debug("AbortIOCB %r %r %r", addr, iocbid, err)

        if not self.localIOCB.has_key(iocbid):
            raise RuntimeError, "no reference to aborting iocb: %r" % (iocbid,)
        
        # get the iocb
        iocb = self.localIOCB[iocbid]

        # delete the dictionary reference
        del self.localIOCB[iocbid]

        # change the state
        iocb.ioState = ABORTED
        iocb.ioError = err
        
        # notify the client
        iocb.Trigger()
        
#
#   Abort
#

@FunctionLogging
def Abort(err):
    """Abort everything, everywhere."""
    Abort._debug("Abort %r", err)

    # start with the server
    if IOServer._highlander:
        IOServer._highlander.Abort(err)

    # now do everything local
    for controller in _localControllers.values():
        controller.Abort(err)

