#!/usr/bin/python

"""
TCP Communications Module
"""

import asyncore
import socket
import cPickle
from time import time as _time, sleep as _sleep
from StringIO import StringIO

from errors import *
from debugging import ModuleLogger, DebugContents, bacpypes_debugging

from core import deferred
from task import FunctionTask, OneShotFunction
from comm import PDU, Client, Server
from comm import ServiceAccessPoint, ApplicationServiceElement

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# globals
REBIND_SLEEP_INTERVAL = 2.0

#
#   PickleActorMixIn
#

@bacpypes_debugging
class PickleActorMixIn:

    def __init__(self, *args):
        if _debug: PickleActorMixIn._debug("__init__ %r", args)
        super(PickleActorMixIn, self).__init__(*args)

        # keep an upstream buffer
        self.pickleBuffer = ''

    def indication(self, pdu):
        if _debug: PickleActorMixIn._debug("indication %r", pdu)

        # pickle the data
        pdu.pduData = cPickle.dumps(pdu.pduData)

        # continue as usual
        super(PickleActorMixIn, self).indication(pdu)

    def response(self, pdu):
        if _debug: PickleActorMixIn._debug("response %r", pdu)

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

            super(PickleActorMixIn, self).response(rpdu)

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

@bacpypes_debugging
class TCPClient(asyncore.dispatcher):

    def __init__(self, peer):
        if _debug: TCPClient._debug("__init__ %r", peer)
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
        if _debug: TCPClient._debug("    - try to connect")
        self.connect(peer)
        if _debug: TCPClient._debug("    - connected (maybe)")
        
    def handle_connect(self):
        if _debug: deferred(TCPClient._debug, "handle_connect")

    def handle_expt(self):
        pass
        
    def readable(self):
        return 1

    def handle_read(self):
        if _debug: deferred(TCPClient._debug, "handle_read")

        try:
            msg = self.recv(65536)
            if _debug: deferred(TCPClient._debug, "    - received %d octets", len(msg))
            self.socketError = None

            # no socket means it was closed
            if not self.socket:
                if _debug: deferred(TCPClient._debug, "    - socket was closed")
            else:
                # sent the data upstream
                deferred(self.response, PDU(msg))

        except socket.error as err:
            if (err.args[0] == 111):
                deferred(TCPClient._error, "connection to %r refused", self.peer)
            else:
                deferred(TCPClient._error, "TCPClient.handle_read socket error: %r", err)
            self.socketError = err
            
    def writable(self):
        return (len(self.request) != 0)

    def handle_write(self):
        if _debug: deferred(TCPClient._debug, "handle_write")

        try:
            sent = self.send(self.request)
            if _debug: deferred(TCPClient._debug, "    - sent %d octets, %d remaining", sent, len(self.request) - sent)
            self.socketError = None

            self.request = self.request[sent:]
        except socket.error as err:
            if (err.args[0] == 111):
                deferred(TCPClient._error, "connection to %r refused", self.peer)
            else:
                deferred(TCPClient._error, "handle_write socket error: %s", err)
            self.socketError = err

    def handle_close(self):
        if _debug: deferred(TCPClient._debug, "handle_close")

        # close the socket
        self.close()
        
        # make sure other routines know the socket is closed
        self.socket = None

    def indication(self, pdu):
        """Requests are queued for delivery."""
        if _debug: TCPClient._debug("indication %r", pdu)

        self.request += pdu.pduData

#
#   TCPClientActor
#
#   Actors are helper objects for a director.  There is one actor for
#   each connection.
#

@bacpypes_debugging
class TCPClientActor(TCPClient):

    def __init__(self, director, peer):
        if _debug: TCPClientActor._debug("__init__ %r %r", director, peer)
        TCPClient.__init__(self, peer)

        # keep track of the director
        self.director = director

        # add a timer
        self.timeout = director.timeout
        if self.timeout > 0:
            self.timer = FunctionTask(self.idle_timeout)
            self.timer.install_task(_time() + self.timeout)
        else:
            self.timer = None
        
        # this may have a flush state
        self.flushTask = None
        
        # tell the director this is a new actor
        self.director.add_actor(self)

    def handle_close(self):
        if _debug: TCPClientActor._debug("handle_close")

        # if there's a flush task, cancel it
        if self.flushTask:
            self.flushTask.suspend_task()
            
        # cancel the timer
        if self.timer:
            self.timer.suspend_task()
        
        # tell the director this is gone
        self.director.remove_actor(self)

        # pass the function along
        TCPClient.handle_close(self)
        
    def idle_timeout(self):
        if _debug: TCPClientActor._debug("idle_timeout")
        
        # shut it down
        self.handle_close()

    def indication(self, pdu):
        if _debug: TCPClientActor._debug("indication %r", pdu)

        # additional downstream data is tossed while flushing
        if self.flushTask:
            if _debug: TCPServerActor._debug("    - flushing")
            return
            
        # reschedule the timer
        if self.timer:
            self.timer.install_task(_time() + self.timeout)
        
        # continue as usual
        TCPClient.indication(self, pdu)

    def response(self, pdu):
        if _debug: TCPClientActor._debug("response %r", pdu)

        # put the peer address in as the source
        pdu.pduSource = self.peer

        # reschedule the timer
        if self.timer:
            self.timer.install_task(_time() + self.timeout)
        
        # process this as a response from the director
        self.director.response(pdu)

    def flush(self):
        if _debug: TCPClientActor._debug("flush")
        
        # clear out the old task
        self.flushTask = None

        # if the outgoing buffer has data, re-schedule another attempt
        if self.request:
            self.flushTask = OneShotFunction(self.flush)
            return
            
        # close up shop, all done
        self.handle_close()

#
#   TCPPickleClientActor
#

class TCPPickleClientActor(PickleActorMixIn, TCPClientActor):
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

@bacpypes_debugging
class TCPClientDirector(Server, ServiceAccessPoint, DebugContents):

    _debug_contents = ('timeout', 'actorClass', 'clients', 'reconnect')

    def __init__(self, timeout=0, actorClass=TCPClientActor, sid=None, sapID=None):
        if _debug: TCPClientDirector._debug("__init__ timeout=%r actorClass=%r sid=%r sapID=%r", timeout, actorClass, sid, sapID)
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

        # no clients automatically reconnecting
        self.reconnect = {}

    def add_actor(self, actor):
        """Add an actor when a new one is connected."""
        if _debug: TCPClientDirector._debug("add_actor %r", actor)

        self.clients[actor.peer] = actor
        
        # tell the ASE there is a new client
        if self.serviceElement:
            self.sap_request(addPeer=actor.peer)

    def remove_actor(self, actor):
        """Remove an actor when the socket is closed."""
        if _debug: TCPClientDirector._debug("remove_actor %r", actor)

        del self.clients[actor.peer]

        # tell the ASE the client has gone away
        if self.serviceElement:
            self.sap_request(delPeer=actor.peer)

        # see if it should be reconnected
        if actor.peer in self.reconnect:
            connect_task = FunctionTask(self.connect, actor.peer)
            connect_task.install_task(_time() + self.reconnect[actor.peer])

    def get_actor(self, address):
        """ Get the actor associated with an address or None. """
        return self.clients.get(address, None)

    def connect(self, address, reconnect=0):
        if _debug: TCPClientDirector._debug("connect %r reconnect=%r", address, reconnect)
        if address in self.clients:
            return
            
        # create an actor, which will eventually call add_actor
        client = self.actorClass(self, address)
        if _debug: TCPClientDirector._debug("    - client: %r", client)

        # if it should automatically reconnect, save the timer value
        if reconnect:
            self.reconnect[address] = reconnect

    def disconnect(self, address):
        if _debug: TCPClientDirector._debug("disconnect %r", address)
        if address not in self.clients:
            return

        # if it would normally reconnect, don't bother
        if address in self.reconnect:
            del self.reconnect[address]

        # close it
        self.clients[address].handle_close()

    def indication(self, pdu):
        """Direct this PDU to the appropriate server, create a
        connection if one hasn't already been created."""
        if _debug: TCPClientDirector._debug("indication %r", pdu)

        # get the destination
        addr = pdu.pduDestination

        # get the client
        client = self.clients.get(addr, None)
        if not client:
            client = self.actorClass(self, addr)

        # send the message
        client.indication(pdu)

#
#   TCPServer
#

@bacpypes_debugging
class TCPServer(asyncore.dispatcher):

    def __init__(self, sock, peer):
        if _debug: TCPServer._debug("__init__ %r %r", sock, peer)
        asyncore.dispatcher.__init__(self, sock)

        # save the peer
        self.peer = peer

        # create a request buffer
        self.request = ''
        
        # hold the socket error if there was one
        self.socketError = None
        
    def handle_connect(self):
        if _debug: deferred(TCPServer._debug, "handle_connect")

    def readable(self):
        return 1

    def handle_read(self):
        if _debug: deferred(TCPServer._debug, "handle_read")

        try:
            msg = self.recv(65536)
            if _debug: deferred(TCPServer._debug, "    - received %d octets", len(msg))
            self.socketError = None

            # no socket means it was closed
            if not self.socket:
                if _debug: deferred(TCPServer._debug, "    - socket was closed")
            else:
                deferred(self.response, PDU(msg))

        except socket.error as err:
            if (err.args[0] == 111):
                deferred(TCPServer._error, "connection to %r refused", self.peer)
            else:
                deferred(TCPServer._error, "handle_read socket error: %s", err)
            self.socketError = err

    def writable(self):
        return (len(self.request) != 0)

    def handle_write(self):
        if _debug: deferred(TCPServer._debug, "handle_write")

        try:
            sent = self.send(self.request)
            if _debug: deferred(TCPServer._debug, "    - sent %d octets, %d remaining", sent, len(self.request) - sent)
            self.socketError = None

            self.request = self.request[sent:]
        except socket.error as why:
            if (why.args[0] == 111):
                deferred(TCPServer._error, "connection to %r refused", self.peer)
            else:
                deferred(TCPServer._error, "handle_write socket error: %s", why)
            self.socketError = why

    def handle_close(self):
        if _debug: deferred(TCPServer._debug, "handle_close")

        if not self:
            deferred(TCPServer._warning, "handle_close: self is None")
            return
        if not self.socket:
            deferred(TCPServer._warning, "handle_close: socket already closed")
            return

        self.close()
        self.socket = None

    def indication(self, pdu):
        """Requests are queued for delivery."""
        if _debug: TCPServer._debug("indication %r", pdu)

        self.request += pdu.pduData

#
#   TCPServerActor
#

@bacpypes_debugging
class TCPServerActor(TCPServer):

    def __init__(self, director, sock, peer):
        if _debug: TCPServerActor._debug("__init__ %r %r %r", director, sock, peer)
        TCPServer.__init__(self, sock, peer)

        # keep track of the director
        self.director = director

        # add a timer
        self.timeout = director.timeout
        if self.timeout > 0:
            self.timer = FunctionTask(self.idle_timeout)
            self.timer.install_task(_time() + self.timeout)
        else:
            self.timer = None
        
        # this may have a flush state
        self.flushTask = None
        
        # tell the director this is a new actor
        self.director.add_actor(self)

    def handle_close(self):
        if _debug: TCPServerActor._debug("handle_close")

        # if there's a flush task, cancel it
        if self.flushTask:
            self.flushTask.suspend_task()
            
        # tell the director this is gone
        self.director.remove_actor(self)

        # pass it down
        TCPServer.handle_close(self)

    def idle_timeout(self):
        if _debug: TCPServerActor._debug("idle_timeout")
        
        # shut it down
        self.handle_close()

    def indication(self, pdu):
        if _debug: TCPServerActor._debug("indication %r", pdu)

        # additional downstream data is tossed while flushing
        if self.flushTask:
            if _debug: TCPServerActor._debug("    - flushing")
            return
            
        # reschedule the timer
        if self.timer:
            self.timer.install_task(_time() + self.timeout)
        
        # continue as usual
        TCPServer.indication(self, pdu)

    def response(self, pdu):
        if _debug: TCPServerActor._debug("response %r", pdu)

        # upstream data is tossed while flushing
        if self.flushTask:
            if _debug: TCPServerActor._debug("    - flushing")
            return
            
        # save the source
        pdu.pduSource = self.peer

        # reschedule the timer
        if self.timer:
            self.timer.install_task(_time() + self.timeout)
        
        # process this as a response from the director
        self.director.response(pdu)

    def flush(self):
        if _debug: TCPServerActor._debug("flush")
            
        # clear out the old task
        self.flushTask = None

        # if the outgoing buffer has data, re-schedule another attempt
        if self.request:
            self.flushTask = OneShotFunction(self.flush)
            return
            
        # close up shop, all done
        self.handle_close()

#
#   TCPPickleServerActor
#

class TCPPickleServerActor(PickleActorMixIn, TCPServerActor):
    pass

#
#   TCPServerDirector
#

@bacpypes_debugging
class TCPServerDirector(asyncore.dispatcher, Server, ServiceAccessPoint, DebugContents):

    _debug_contents = ('port', 'timeout', 'actorClass', 'servers')

    def __init__(self, address, listeners=5, timeout=0, reuse=False, actorClass=TCPServerActor, cid=None, sapID=None):
        if _debug:
            TCPServerDirector._debug("__init__ %r listeners=%r timeout=%r reuse=%r actorClass=%r cid=%r sapID=%r"
                , address, listeners, timeout, reuse, actorClass, cid, sapID
                )
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
        if reuse:
            self.set_reuse_addr()

        # try to bind, keep trying for a while if its already in use
        hadBindErrors = False
        for i in range(30):
            try:
                self.bind(address)
                break
            except socket.error as err:
                hadBindErrors = True
                TCPServerDirector._warning('bind error %r, sleep and try again', err)
                _sleep(REBIND_SLEEP_INTERVAL)
        else:
            TCPServerDirector._error('unable to bind')
            raise RuntimeError, "unable to bind"

        # if there were some bind errors, generate a meesage that all is OK now
        if hadBindErrors:
            TCPServerDirector._info('bind successful')

        self.listen(listeners)

    def handle_accept(self):
        if _debug: TCPServerDirector._debug("handle_accept")

        try:
            client, addr = self.accept()
        except socket.error:
            TCPServerDirector._warning('accept() threw an exception')
            return
        except TypeError:
            TCPServerDirector._warning('accept() threw EWOULDBLOCK')
            return
        if _debug: TCPServerDirector._debug("    - connection %r, %r", client, addr)

        # create a server
        server = self.actorClass(self, client, addr)

        # add it to our pool
        self.servers[addr] = server

        # return it to the dispatcher
        return server

    def handle_close(self):
        if _debug: TCPServerDirector._debug("handle_close")

        # close the socket
        self.close()

    def add_actor(self, actor):
        if _debug: TCPServerDirector._debug("add_actor %r", actor)

        self.servers[actor.peer] = actor

        # tell the ASE there is a new server
        if self.serviceElement:
            self.sap_request(addPeer=actor.peer)

    def remove_actor(self, actor):
        if _debug: TCPServerDirector._debug("remove_actor %r", actor)

        try:
            del self.servers[actor.peer]
        except KeyError:
            TCPServerDirector._warning("remove_actor: %r not an actor", actor)

        # tell the ASE the server has gone away
        if self.serviceElement:
            self.sap_request(delPeer=actor.peer)

    def get_actor(self, address):
        """ Get the actor associated with an address or None. """
        return self.servers.get(address, None)

    def indication(self, pdu):
        """Direct this PDU to the appropriate server."""
        if _debug: TCPServerDirector._debug("indication %r", pdu)

        # get the destination
        addr = pdu.pduDestination

        # get the server
        server = self.servers.get(addr, None)
        if not server:
            raise RuntimeError, "not a connected server"

        # pass the indication to the actor
        server.indication(pdu)

#
#   StreamToPacket
#

@bacpypes_debugging
class StreamToPacket(Client, Server):

    def __init__(self, fn, cid=None, sid=None):
        if _debug: StreamToPacket._debug("__init__ %r cid=%r, sid=%r", fn, cid, sid)
        Client.__init__(self, cid)
        Server.__init__(self, sid)
        
        # save the packet function
        self.packetFn = fn
        
        # start with an empty set of buffers
        self.upstreamBuffer = {}
        self.downstreamBuffer = {}
        
    def packetize(self, pdu, streamBuffer):
        if _debug: StreamToPacket._debug("packetize %r", pdu)
        
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
            
    def indication(self, pdu):
        """Message going downstream."""
        if _debug: StreamToPacket._debug("indication %r", pdu)
        
        # hack it up into chunks
        for packet in self.packetize(pdu, self.downstreamBuffer):
            self.request(packet)
            
    def confirmation(self, pdu):
        """Message going upstream."""
        if _debug: StreamToPacket._debug("StreamToPacket.confirmation %r", pdu)
        
        # hack it up into chunks
        for packet in self.packetize(pdu, self.upstreamBuffer):
            self.response(packet)
            
#
#   StreamToPacketSAP
#

@bacpypes_debugging
class StreamToPacketSAP(ApplicationServiceElement, ServiceAccessPoint):

    def __init__(self, stp, aseID=None, sapID=None):
        if _debug: StreamToPacketSAP._debug("__init__ %r aseID=%r, sapID=%r", stp, aseID, sapID)
        ApplicationServiceElement.__init__(self, aseID)
        ServiceAccessPoint.__init__(self, sapID)
        
        # save a reference to the StreamToPacket object
        self.stp = stp
        
    def indication(self, addPeer=None, delPeer=None):
        if _debug: StreamToPacketSAP._debug("indication addPeer=%r delPeer=%r", addPeer, delPeer)
        
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
            self.sap_request(addPeer=addPeer, delPeer=delPeer)

