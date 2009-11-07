#!/usr/bin/python

"""
TCPCommunications Module
"""

import asyncore
import socket
import logging
import cPickle
from time import time as _time, sleep as _sleep
from StringIO import StringIO

from Exceptions import *
from Debugging import Logging

from Core import deferred
from Task import FunctionTask, OneShotFunction
from CommunicationsCore import PDU, Client, Server, Bind
from CommunicationsCore import ServiceAccessPoint, ApplicationServiceElement
from CommandLogging import CommandLoggingClient

# some debugging
_log = logging.getLogger(__name__)

#
#   PickleServerMixin
#

class PickleServerMixin(Logging):

    def __init__(self, *args):
        PickleServerMixin._debug("__init__ %r", args)
        super(PickleServerMixin, self).__init__(*args)

        # keep an upstream buffer
        self.pickleBuffer = ''

    def Indication(self, pdu):
        PickleServerMixin._debug("Indication %r", pdu)

        # pickle the data
        pdu.pduData = cPickle.dumps(pdu.pduData)
        
        # continue as usual
        super(PickleServerMixin, self).Indication(pdu)

    def Response(self, pdu):
        PickleServerMixin._debug("Response %r", pdu)

        # add the data to our buffer
        self.pickleBuffer += pdu.pduData
        
        # build a file-like object around the buffer
        strm = StringIO(self.pickleBuffer)
        
        pos = 0
        while (pos < strm.len):
            try:
                # try to load something
                msg = cPickle.load(strm)
            except:
                break
                
            # got a message
            rpdu = PDU(msg)
            rpdu.update(pdu)
            
            super(PickleServerMixin, self).Response(rpdu)
            
            # see where we are
            pos = strm.tell()
            
        # save anything left over, if there is any
        if (pos < strm.len):
            self.pickleBuffer = self.pickleBuffer[pos:]
        else:
            self.pickleBuffer = ''

#
#   TCPClient
#
#   This class is a mapping between the client/server pattern and the
#   socket API.  The ctor is given the address to connect as a TCP
#   client.  Because objects of this class sit at the bottom of a
#   protocol stack they are accessed as servers.
#

class TCPClient(asyncore.dispatcher, Logging):

    def __init__(self, peer):
        TCPClient._debug("__init__ %r", peer)
        asyncore.dispatcher.__init__(self)

        # ask the dispatcher for a socket
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)

        # save the peer
        self.peer = peer

        # create a request buffer
        self.request = ''

        # hold the socket error if there was one
        self.socketError = None
        
        # try to connect the socket
        TCPClient._debug("    - try to connect")
        self.connect(peer)
        TCPClient._debug("    - connected (maybe)")
        
    def handle_connect(self):
        TCPClient._debug("handle_connect")

    def handle_expt(self):
        pass
        
    def readable(self):
        return 1

    def handle_read(self):
        deferred(TCPClient._debug, "handle_read")

        try:
            msg = self.recv(65536)
            deferred(TCPClient._debug, "    - received %d octets", len(msg))
            self.socketError = None

            # no socket means it was closed
            if not self.socket:
                deferred(TCPClient._debug, "    - socket was closed")
            else:
                # sent the data upstream
                deferred(self.Response, PDU(msg))

        except socket.error, err:
            if (err.args[0] == 111):
                deferred(TCPClient._error, "connection to %r refused", self.peer)
            else:
                deferred(TCPClient._error, "TCPClient.handle_read socket error: %r", err)
            self.socketError = err
            
    def writable(self):
        return (len(self.request) != 0)

    def handle_write(self):
        deferred(TCPClient._debug, "handle_write")

        try:
            sent = self.send(self.request)
            deferred(TCPClient._debug, "    - sent %d octets, %d remaining", sent, len(self.request) - sent)
            self.socketError = None

            self.request = self.request[sent:]
        except socket.error, err:
            if (err.args[0] == 111):
                deferred(TCPClient._error, "connection to %r refused", self.peer)
            else:
                deferred(TCPClient._error, "handle_write socket error: %s", err)
            self.socketError = err

    def handle_close(self):
        TCPClient._debug("handle_close")

        # close the socket
        self.close()
        
        # make sure other routines know the socket is closed
        self.socket = None

    def Indication(self, pdu):
        """Requests are queued for delivery."""
        TCPClient._debug("Indication %r", pdu)

        self.request += pdu.pduData

#
#   TCPClientActor
#
#   Actors are helper objects for a director.  There is one actor for
#   each connection.
#

class TCPClientActor(TCPClient, Logging):

    def __init__(self, director, peer):
        TCPClientActor._debug("__init__ %r %r", director, peer)
        TCPClient.__init__(self, peer)

        # keep track of the director
        self.director = director

        # add a timer
        self.timeout = director.timeout
        if self.timeout > 0:
            self.timer = FunctionTask(self.IdleTimeout)
            self.timer.InstallTask(_time() + self.timeout)
        else:
            self.timer = None
        
        # this may have a flush state
        self.flushTask = None
        
        # tell the director this is a new actor
        self.director.AddActor(self)

    def handle_close(self):
        TCPClientActor._debug("handle_close")

        # if there's a flush task, cancel it
        if self.flushTask:
            self.flushTask.SuspendTask()
            
        # cancel the timer
        if self.timer:
            self.timer.SuspendTask()
        
        # tell the director this is gone
        self.director.RemoveActor(self)

        # pass the function along
        TCPClient.handle_close(self)
        
    def IdleTimeout(self):
        TCPClientActor._debug("IdleTimeout")
        
        # shut it down
        self.handle_close()

    def Indication(self, pdu):
        TCPClientActor._debug("Indication %r", pdu)

        # additional downstream data is tossed while flushing
        if self.flushTask:
            TCPServerActor._debug("    - flushing")
            return
            
        # reschedule the timer
        if self.timer:
            self.timer.InstallTask(_time() + self.timeout)
        
        # continue as usual
        TCPClient.Indication(self, pdu)

    def Response(self, pdu):
        TCPClientActor._debug("Response %r", pdu)

        # put the peer address in as the source
        pdu.pduSource = self.peer

        # reschedule the timer
        if self.timer:
            self.timer.InstallTask(_time() + self.timeout)
        
        # process this as a response from the director
        self.director.Response(pdu)

    def Flush(self):
        TCPClientActor._debug("Flush")
        
        # clear out the old task
        self.flushTask = None

        # if the outgoing buffer has data, re-schedule another attempt
        if self.request:
            self.flushTask = OneShotFunction(self.Flush)
            return
            
        # close up shop, all done
        self.handle_close()

#
#   TCPPickleClientActor
#

class TCPPickleClientActor(PickleServerMixin, TCPClientActor):
    pass

#
#   TCPClientDirector
#
#   A client director presents a connection pool as one virtual
#   interface.  If a request should be sent to an address and there
#   is no connection already established for it, it will create one
#   and maintain it.  PDU's from TCP clients have no source address,
#   so one is provided by the client actor.
#

class TCPClientDirector(Server, ServiceAccessPoint, Logging):

    def __init__(self, timeout=0, actorClass=TCPClientActor, sid=None, sapID=None):
        TCPClientDirector._debug("__init__ timeout=%r actorClass=%r sid=%r sapID=%r", timeout, actorClass, sid, sapID)
        Server.__init__(self, sid)
        ServiceAccessPoint.__init__(self, sapID)

        # check the actor class
        if not issubclass(actorClass, TCPClientActor):
            raise TypeError, "actorClass must be a subclass of TCPClientActor"
        self.actorClass = actorClass
        
        # save the timeout for actors
        self.timeout = timeout
        
        # start with an empty client pool
        self.clients = {}

    def AddActor(self, actor):
        """Add an actor when a new one is connected."""
        TCPClientDirector._debug("AddActor %r", actor)

        self.clients[actor.peer] = actor
        
        # tell the ASE there is a new client
        if self.serviceElement:
            self.SAPRequest(addPeer=actor.peer)

    def RemoveActor(self, actor):
        """Remove an actor when the socket is closed."""
        TCPClientDirector._debug("RemoveActor %r", actor)

        del self.clients[actor.peer]

        # tell the ASE the client has gone away
        if self.serviceElement:
            self.SAPRequest(delPeer=actor.peer)

    def GetActor(self, address):
        return self.clients.get(address, None)
        
    def Connect(self, address):
        TCPClientDirector._debug("Connect %r", address)
        if address in self.clients:
            return
            
        # create an actor
        client = self.actorClass(self, address)
        
    def Disconnect(self, address):
        TCPClientDirector._debug("Disconnect %r", address)
        if address not in self.clients:
            return
            
        # close it
        self.clients[address].handle_close()
        
    def Indication(self, pdu):
        """Direct this PDU to the appropriate server, create a
        connection if one hasn't already been created."""
        TCPClientDirector._debug("Indication %r", pdu)

        # get the destination
        addr = pdu.pduDestination

        # get the client
        client = self.clients.get(addr, None)
        if not client:
            client = self.actorClass(self, addr)

        # send the message
        client.Indication(pdu)

#
#   TCPServer
#

class TCPServer(asyncore.dispatcher, Logging):

    def __init__(self, sock, peer):
        TCPServer._debug("__init__ %r %r", sock, peer)
        asyncore.dispatcher.__init__(self, sock)

        # save the peer
        self.peer = peer

        # create a request buffer
        self.request = ''
        
        # hold the socket error if there was one
        self.socketError = None
        
    def handle_connect(self):
        TCPServer._debug("handle_connect")

    def readable(self):
        return 1

    def handle_read(self):
        deferred(TCPServer._debug, "handle_read")

        try:
            msg = self.recv(65536)
            deferred(TCPServer._debug, "    - received %d octets", len(msg))
            self.socketError = None

            # no socket means it was closed
            if not self.socket:
                deferred(TCPServer._debug, "    - socket was closed")
            else:
                deferred(self.Response, PDU(msg))

        except socket.error, err:
            if (err.args[0] == 111):
                deferred(TCPServer._error, "connection to %r refused", self.peer)
            else:
                deferred(TCPServer._error, "handle_read socket error: %s", err)
            self.socketError = err

    def writable(self):
        return (len(self.request) != 0)

    def handle_write(self):
        deferred(TCPServer._debug, "handle_write")

        try:
            sent = self.send(self.request)
            deferred(TCPServer._debug, "    - sent %d octets, %d remaining", sent, len(self.request) - sent)
            self.socketError = None

            self.request = self.request[sent:]
        except socket.error, why:
            if (err.args[0] == 111):
                deferred(TCPServer._error, "connection to %r refused", self.peer)
            else:
                deferred(TCPServer._error, "handle_write socket error: %s", why)
            self.socketError = why

    def handle_close(self):
        TCPServer._debug("handle_close")
        if not self:
            deferred(TCPServer._warning, "handle_close: self is None")
            return
        if not self.socket:
            deferred(TCPServer._warning, "handle_close: socket already closed")
            return

        self.close()
        self.socket = None

    def Indication(self, pdu):
        """Requests are queued for delivery."""
        TCPServer._debug("Indication %r", pdu)

        self.request += pdu.pduData

#
#   TCPServerActor
#

class TCPServerActor(TCPServer, Logging):

    def __init__(self, director, sock, peer):
        TCPServerActor._debug("__init__ %r %r %r", director, sock, peer)
        TCPServer.__init__(self, sock, peer)

        # keep track of the director
        self.director = director

        # add a timer
        self.timeout = director.timeout
        if self.timeout > 0:
            self.timer = FunctionTask(self.IdleTimeout)
            self.timer.InstallTask(_time() + self.timeout)
        else:
            self.timer = None
        
        # this may have a flush state
        self.flushTask = None
        
        # tell the director this is a new actor
        self.director.AddActor(self)

    def handle_close(self):
        TCPServerActor._debug("handle_close")

        # if there's a flush task, cancel it
        if self.flushTask:
            self.flushTask.SuspendTask()
            
        # tell the director this is gone
        self.director.RemoveActor(self)

        # pass it down
        TCPServer.handle_close(self)

    def IdleTimeout(self):
        TCPServerActor._debug("IdleTimeout")
        
        # shut it down
        self.handle_close()

    def Indication(self, pdu):
        TCPServerActor._debug("Indication %r", pdu)

        # additional downstream data is tossed while flushing
        if self.flushTask:
            TCPServerActor._debug("    - flushing")
            return
            
        # reschedule the timer
        if self.timer:
            self.timer.InstallTask(_time() + self.timeout)
        
        # continue as usual
        TCPServer.Indication(self, pdu)

    def Response(self, pdu):
        TCPServerActor._debug("Response %r", pdu)

        # upstream data is tossed while flushing
        if self.flushTask:
            TCPServerActor._debug("    - flushing")
            return
            
        # save the source
        pdu.pduSource = self.peer

        # reschedule the timer
        if self.timer:
            self.timer.InstallTask(_time() + self.timeout)
        
        # process this as a response from the director
        self.director.Response(pdu)

    def Flush(self):
        TCPServerActor._debug("Flush")
            
        # clear out the old task
        self.flushTask = None

        # if the outgoing buffer has data, re-schedule another attempt
        if self.request:
            self.flushTask = OneShotFunction(self.Flush)
            return
            
        # close up shop, all done
        self.handle_close()

#
#   TCPPickleServerActor
#

class TCPPickleServerActor(PickleServerMixin, TCPServerActor):
    pass

#
#   TCPServerDirector
#

class TCPServerDirector(asyncore.dispatcher, Server, ServiceAccessPoint, Logging):

    def __init__(self, address, listeners=5, timeout=0, actorClass=TCPServerActor, cid=None, sapID=None):
        TCPServerDirector._debug("__init__ %r listeners=%r timeout=%r actorClass=%r cid=%r sapID=%r", address, listeners, timeout, actorClass, cid, sapID)
        Server.__init__(self, cid)
        ServiceAccessPoint.__init__(self, sapID)

        # save the address and timeout
        self.port = address
        self.timeout = timeout

        # check the actor class
        if not issubclass(actorClass, TCPServerActor):
            raise TypeError, "actorClass must be a subclass of TCPServerActor"
        self.actorClass = actorClass
        
        # start with an empty pool of servers
        self.servers = {}

        # continue with initialization
        asyncore.dispatcher.__init__(self)
        
        # create a listening port
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # try to bind, keep trying for a while if its already in use
        hadBindErrors = False
        for i in range(12):
            try:
                self.bind(address)
                break
            except socket.error, err:
                hadBindErrors = True
                TCPServerDirector._info('bind error %r, sleep and try again', err)
                _sleep(5.0)
        else:
            TCPServerDirector._error('unable to bind')
            raise RuntimeError, "unable to bind"
        
        # if there were some bind errors, generate a meesage that all is OK now
        if hadBindErrors:
            TCPServerDirector._info('bind successful')

        self.listen(listeners)

    def handle_accept(self):
        TCPServerDirector._debug("handle_accept")

        try:
            client, addr = self.accept()
        except socket.error:
            TCPServerDirector._warning('accept() threw an exception')
            return
        except TypeError:
            TCPServerDirector._warning('accept() threw EWOULDBLOCK')
            return
        TCPServerDirector._debug("    - connection %r, %r", client, addr)

        # create a server
        server = self.actorClass(self, client, addr)

        # add it to our pool
        self.servers[addr] = server

        # return it to the dispatcher
        return server

    def handle_close(self):
        TCPServerDirector._debug("handle_close")

        # close the socket
        self.close()

    def AddActor(self, actor):
        TCPServerDirector._debug("AddActor %r", actor)

        self.servers[actor.peer] = actor

        # tell the ASE there is a new server
        if self.serviceElement:
            self.SAPRequest(addPeer=actor.peer)

    def RemoveActor(self, actor):
        TCPServerDirector._debug("RemoveActor %r", actor)

        try:
            del self.servers[actor.peer]
        except KeyError:
            TCPServerDirector._warning("RemoveActor: %r not an actor", actor)

        # tell the ASE the server has gone away
        if self.serviceElement:
            self.SAPRequest(delPeer=actor.peer)

    def GetActor(self, address):
        return self.servers.get(address, None)
        
    def Indication(self, pdu):
        """Direct this PDU to the appropriate server."""
        TCPServerDirector._debug("Indication %r", pdu)

        # get the destination
        addr = pdu.pduDestination

        # get the server
        server = self.servers.get(addr, None)
        if not server:
            raise RuntimeError, "not a connected server"

        # pass the indication to the actor
        server.Indication(pdu)

#
#   StreamToPacket
#

class StreamToPacket(Client, Server, Logging):

    def __init__(self, fn, cid=None, sid=None):
        StreamToPacket._debug("__init__ %r cid=%r, sid=%r", fn, cid, sid)
        Client.__init__(self, cid)
        Server.__init__(self, sid)
        
        # save the packet function
        self.packetFn = fn
        
        # start with an empty set of buffers
        self.upstreamBuffer = {}
        self.downstreamBuffer = {}
        
    def Packetize(self, pdu, streamBuffer):
        StreamToPacket._debug("Packetize %r", pdu)
        
        def Chop(addr):
            # get the current downstream buffer
            buff = streamBuffer.get(addr, '') + pdu.pduData
            
            # look for a packet
            while 1:
                packet = self.packetFn(buff)
                if packet is None:
                    break
                
                yield PDU(packet[0], source=pdu.pduSource, destination=pdu.pduDestination)
                buff = packet[1]
                
            # save what didn't get sent
            streamBuffer[addr] = buff
        
        # buffer related to the addresses
        if pdu.pduSource:
            for pdu in Chop(pdu.pduSource):
                yield pdu
        if pdu.pduDestination:
            for pdu in Chop(pdu.pduDestination):
                yield pdu
            
    def Indication(self, pdu):
        """Message going downstream."""
        StreamToPacket._debug("Indication %r", pdu)
        
        # hack it up into chunks
        for packet in self.Packetize(pdu, self.downstreamBuffer):
            self.Request(packet)
            
    def Confirmation(self, pdu):
        """Message going upstream."""
        StreamToPacket._debug("StreamToPacket.Confirmation %r", pdu)
        
        # hack it up into chunks
        for packet in self.Packetize(pdu, self.upstreamBuffer):
            self.Response(packet)
            
#
#   StreamToPacketSAP
#

class StreamToPacketSAP(ApplicationServiceElement, ServiceAccessPoint, Logging):

    def __init__(self, stp, aseID=None, sapID=None):
        StreamToPacketSAP._debug("__init__ %r aseID=%r, sapID=%r", stp, aseID, sapID)
        ApplicationServiceElement.__init__(self, aseID)
        ServiceAccessPoint.__init__(self, sapID)
        
        # save a reference to the StreamToPacket object
        self.stp = stp
        
    def Indication(self, addPeer=None, delPeer=None):
        StreamToPacketSAP._debug("Indication addPeer=%r delPeer=%r", addPeer, delPeer)
        
        if addPeer:
            # create empty buffers associated with the peer
            self.stp.upstreamBuffer[addPeer] = ''
            self.stp.downstreamBuffer[addPeer] = ''
            
        if delPeer:
            # delete the buffer contents associated with the peer
            del self.stp.upstreamBuffer[delPeer]
            del self.stp.downstreamBuffer[delPeer]
            
        # chain this along
        if self.serviceElement:
            self.SAPRequest(addPeer=addPeer, delPeer=delPeer)

#
#   TCPLogging
#

class TCPLogging(CommandLoggingClient, Logging):

    server_addr = ('', 9001)
    
    def __init__(self):
        TCPLogging._debug("__init__")
        CommandLoggingClient.__init__(self)
        
        self.director = TCPServerDirector(self.server_addr)
        Bind(self, self.director)
