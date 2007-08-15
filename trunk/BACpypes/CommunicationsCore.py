#! /usr/bin/env python

"""
Communications Module
"""

import sys
import asyncore
import socket
import struct
import thread
import threading
import time
import types
import traceback
import exceptions

import Queue
from itertools import count as _count, izip as _izip

from Exceptions import *

try:
    import CSThread as Thread
except:
    import Thread
if ("--debugThread" in sys.argv):
    print "CommunicationsCore imported", Thread

# some debugging
_debug = 0 or ('--debugCommunicationsCore' in sys.argv)
_debugBind = _debug or ('--debugBind' in sys.argv)
_debugUDPDirector = _debug or ('--debugUDPDirector' in sys.argv)

def _StringToHex(x,sep=''):
    return sep.join(["%02X" % (ord(c),) for c in x])

def _HexToString(x,sep=''):
    if sep:
        parts = x.split(sep)
    else:
        parts = [x[i:i+2] for i in range(0,len(x),2)]
    
    return ''.join([chr(int(part,16)) for part in parts])

# prevent short/long struct overflow
_shortMask = 0xFFFFL
_longMask = 0xFFFFFFFFL

# maps of named clients and servers
clientMap = {}
serverMap = {}

# maps of named SAPs and ASEs
serviceMap = {}
elementMap = {}

#
#   Client
#

class Client:

    def __init__(self, cid=None):
        self.clientID = cid
        self.clientPeer = None
        if cid is not None:
            if clientMap.has_key(cid):
                raise ConfigurationError, "already a client %r" % (cid,)
            clientMap[cid] = self

            # automatically bind
            if serverMap.has_key(cid):
                server = serverMap[cid]
                if server.serverPeer:
                    raise ConfigurationError, "server %r already bound" % (cid,)
                    
                Bind(self, server)
                
    def Request(self, *args, **kwargs):
        if not self.clientPeer:
            raise ConfigurationError, "unbound client"
        self.clientPeer.Indication(*args, **kwargs)

    def Confirmation(self, *args, **kwargs):
        raise NotImplementedError, "Confirmation must be overridden"

#
#   Server
#

class Server:

    def __init__(self, sid=None):
        self.serverID = sid
        self.serverPeer = None
        if sid is not None:
            if serverMap.has_key(sid):
                raise RuntimeError, "already a server %r" % (sid,)
            serverMap[sid] = self

            # automatically bind
            if clientMap.has_key(sid):
                client = clientMap[sid]
                if client.clientPeer:
                    raise ConfigurationError, "client %r already bound" % (sid,)
                    
                Bind(client, self)

    def Indication(self, *args, **kwargs):
        raise NotImplementedError, "Indication must be overridden"

    def Response(self, *args, **kwargs):
        if not self.serverPeer:
            raise ConfigurationError, "unbound server"
        self.serverPeer.Confirmation(*args, **kwargs)

#
#   Debug
#

class Debug(Client, Server):

    def __init__(self, cid=None, sid=None):
        Client.__init__(self, cid)
        Server.__init__(self, sid)
        
    def Confirmation(self, *args, **kwargs):
        print "Debug(%s).Confirmation" % (self.clientID,)
        for i, arg in _izip(_count(), args):
            print "    - args[%d]:" % (i,), args[i]
        for key, value in kwargs.items():
            print "    - kwargs[%r]:" % (key,), value

        if self.serverPeer:
            self.Response(*args, **kwargs)
        
    def Indication(self, *args, **kwargs):
        print "Debug(%s).Indication" % (self.serverID,)
        for i, arg in _izip(_count(), args):
            print "    - args[%d]:" % (i,), args[i]
        for key, value in kwargs.items():
            print "    - kwargs[%r]:" % (key,), value

        if self.clientPeer:
            self.Request(*args, **kwargs)
        
#
#   Echo
#

class Echo(Client, Server):

    def __init__(self, cid=None, sid=None):
        Client.__init__(self, cid)
        Server.__init__(self, sid)
        
    def Confirmation(self, *args, **kwargs):
        if _debug:
            print "Echo(%s).Confirmation" % (self.clientID,)
            print "    - args:", args
            print "    - kwargs:", kwargs

        if self.serverPeer:
            self.Request(*args, **kwargs)
        
    def Indication(self, *args, **kwargs):
        if _debug:
            print "Echo(%s).Indication" % (self.serverID,)
            print "    - args:", args
            print "    - kwargs:", kwargs

        if self.clientPeer:
            self.Response(*args, **kwargs)
        
#
#   ServiceAccessPoint
#
#   Note that the SAP functions have been renamed so a derived class 
#   can inherit from both Client, Service, and ServiceAccessPoint 
#   at the same time.
#

class ServiceAccessPoint:

    def __init__(self, sapID=None):
        if _debug:
            print "ServiceAccessPoint.__init__", sapID
            
        self.serviceID = sapID
        self.serviceElement = None
        
        if sapID is not None:
            if serviceMap.has_key(sapID):
                raise ConfigurationError, "already a service access point %r" % (sapID,)
            serviceMap[sapID] = self

            # automatically bind
            if elementMap.has_key(sapID):
                element = elementMap[sapID]
                if element.elementService:
                    raise ConfigurationError, "application service element %r already bound" % (sapID,)
                    
                Bind(element, self)
                
    def SAPRequest(self, *args, **kwargs):
        if _debug:
            print "ServiceAccessPoint(%s).SAPRequest" % (self.serviceID,)
            print "    - args:", args
            print "    - kwargs:", kwargs
            
        if not self.serviceElement:
            raise ConfigurationError, "unbound service access point"
        self.serviceElement.Indication(*args, **kwargs)

    def SAPIndication(self, *args, **kwargs):
        raise NotImplementedError, "SAPIndication must be overridden"

    def SAPResponse(self, *args, **kwargs):
        if _debug:
            print "ServiceAccessPoint(%s).SAPResponse" % (self.serviceID,)
            print "    - args:", args
            print "    - kwargs:", kwargs
            
        if not self.serviceElement:
            raise ConfigurationError, "unbound service access point"
        self.serviceElement.Confirmation(*args,**kwargs)

    def SAPConfirmation(self, *args, **kwargs):
        raise NotImplementedError, "SAPConfirmation must be overridden"

#
#   ApplicationServiceElement
#

class ApplicationServiceElement:

    def __init__(self, aseID=None):
        if _debug:
            print "ApplicationServiceElement.__init__", aseID
            
        self.elementID = aseID
        self.elementService = None
        
        if aseID is not None:
            if elementMap.has_key(aseID):
                raise ConfigurationError, "already an application service element %r" % (aseID,)
            elementMap[aseID] = self
        
            # automatically bind
            if serviceMap.has_key(aseID):
                service = serviceMap[aseID]
                if service.serviceElement:
                    raise ConfigurationError, "service access point %r already bound" % (aseID,)
                    
                Bind(self, service)
                
    def Request(self, *args, **kwargs):
        if _debug:
            print "ApplicationServiceElement(%s).Request" % (self.elementID,)
            print "    - args:", args
            print "    - kwargs:", kwargs
            
        if not self.elementService:
            raise ConfigurationError, "unbound application service element"

        assert self.elementService, "unbound ASE"
        self.elementService.SAPIndication(*args, **kwargs)

    def Indication(self, *args, **kwargs):
        raise NotImplementedError, "Indication must be overridden"

    def Response(self, *args, **kwargs):
        if _debug:
            print "ApplicationServiceElement(%s).Response" % (self.elementID,)
            print "    - args:", args
            print "    - kwargs:", kwargs
            print "    - elementService:", self.elementService
            
        if not self.elementService:
            raise ConfigurationError, "unbound application service element"

        self.elementService.SAPConfirmation(*args,**kwargs)

    def Confirmation(self, *args, **kwargs):
        raise NotImplementedError, "Confirmation must be overridden"

#
#   NullServiceElement
#

class NullServiceElement:

    def Indication(self, *args, **kwargs):
        pass

    def Confirmation(self, *args, **kwargs):
        pass

#
#   DebugServiceElement
#

class DebugServiceElement:

    def Indication(self, *args, **kwargs):
        print "DebugServiceElement(%s).Indication" % (self.elementID,)
        print "    - args:", args
        print "    - kwargs:", kwargs

    def Confirmation(self, *args, **kwargs):
        print "DebugServiceElement(%s).Confirmation" % (self.elementID,)
        print "    - args:", args
        print "    - kwargs:", kwargs

#
#   Bind
#

def Bind(*args):
    """Bind a list of clients and servers together, top down."""
    if _debugBind:
        print "Bind"
        
    # generic bind is pairs of names
    if not args:
        # find unbound clients and bind them
        for cid, client in clientMap.items():
            # skip those that are already bound
            if client.clientPeer:
                continue
                
            if not cid in serverMap:
                raise RuntimeError, "unmatched server %r" % (cid,)
            server = serverMap[cid]
            
            if server.serverPeer:
                raise RuntimeError, "server already bound %r" % (cid,)
                
            Bind(client, server)
            
        # see if there are any unbound servers
        for sid, server in serverMap.items():
            if server.serverPeer:
                continue
                
            if not sid in clientMap:
                raise RuntimeError, "unmatched client %r" % (sid,)
            else:
                raise RuntimeError, "mistery unbound server %r" % (sid,)
            
        # find unbound application service elements and bind them
        for eid, element in elementMap.items():
            # skip those that are already bound
            if element.elementService:
                continue
                
            if not eid in serviceMap:
                raise RuntimeError, "unmatched element %r" % (cid,)
            service = serviceMap[eid]
            
            if server.serverPeer:
                raise RuntimeError, "service already bound %r" % (cid,)
                
            Bind(element, service)
            
        # see if there are any unbound services
        for sid, service in serviceMap.items():
            if service.serviceElement:
                continue
                
            if not sid in elementMap:
                raise RuntimeError, "unmatched service %r" % (sid,)
            else:
                raise RuntimeError, "mistery unbound service %r" % (sid,)
            
    # go through the argument pairs
    for i in xrange(len(args)-1):
        client = args[i]
        server = args[i+1]
        if _debugBind:
            print "    -", client, "=>", server

        # make sure we're binding clients and servers
        if isinstance(client, Client) and isinstance(server, Server):
            client.clientPeer = server
            server.serverPeer = client

        # we could be binding application clients and servers
        elif isinstance(client, ApplicationServiceElement) and isinstance(server, ServiceAccessPoint):
            client.elementService = server
            server.serviceElement = client

        # error
        else:
            raise TypeError, "Bind() requires a client and server"

#
#   PDUData
#

class PDUData:

    def __init__(self, data=''):
        if isinstance(data, PDUData):
            self.pduData = data.pduData
        elif isinstance(data, types.StringType):
            self.pduData = data
        else:
            raise ValueError, "PDUData ctor parameter must be PDUData or a string"

    def Get(self):
        if len(self.pduData) == 0:
            raise DecodingError, "no more packet data"

        ch = self.pduData[0]
        self.pduData = self.pduData[1:]
        return ord(ch)

    def GetData(self, dlen):
        if len(self.pduData) < dlen:
            raise DecodingError, "no more packet data"

        data = self.pduData[:dlen]
        self.pduData = self.pduData[dlen:]
        return data

    def GetShort(self):
        return struct.unpack('>H',self.GetData(2))[0]

    def GetLong(self):
        return struct.unpack('>L',self.GetData(4))[0]

    def Put(self, ch):
        if _debug:
            print self, "PDUData.Put", repr(ch)
        self.pduData += chr(ch)

    def PutData(self, data):
        if _debug:
            print self, "PDUData.PutData", repr(data)
        self.pduData += data

    def PutShort(self, n):
        if _debug:
            print self, "PDUData.PutShort", repr(n)
        self.pduData += struct.pack('>H',n & _shortMask)

    def PutLong(self, n):
        if _debug:
            print self, "PDUData.PutLong", repr(n)
        self.pduData += struct.pack('>L',n & _longMask)

    def DebugContents(self):
        print "    pduData =", _StringToHex(self.pduData,'.')
    
#
#   PCI
#

class PCI:

    def __init__(self, **kwargs):
        # pick up some optional kwargs
        self.pduSource = kwargs.get('source', None)
        self.pduDestination = kwargs.get('destination', None)
        
    def update(self, pci):
        """Copy the PCI fields."""
        if _debug:
            print self, "PCI.update", pci
            
        self.pduSource = pci.pduSource
        self.pduDestination = pci.pduDestination

    def DebugContents(self):
        print self
        print "    pduSource =", repr(self.pduSource)
        print "    pduDestination =", repr(self.pduDestination)
        
#
#   PDU
#

class PDU(PCI, PDUData):

    def __init__(self, data='', **kwargs):
        PCI.__init__(self, **kwargs)
        PDUData.__init__(self, data)

        # pick up some optional kwargs
        source = kwargs.get('source', None)
        destination = kwargs.get('destination', None)
        
        # carry source and destination from another PDU
        if isinstance(data, PDU):
            # allow parameters to override values
            self.pduSource = source or data.pduSource
            self.pduDestination = destination or data.pduDestination
        else:
            self.pduSource = source
            self.pduDestination = destination

    def __str__(self):
        return '<%s %s -> %s : %s>' % (self.__class__.__name__, self.pduSource, self.pduDestination, _StringToHex(self.pduData,'.'))

    def DebugContents(self):
        PCI.DebugContents(self)
        PDUData.DebugContents(self)

#
#   Monitor
#
#   There is one monitor object running in its own thread that polls for
#   communication events via the asyncore module.
#

class Monitor(Thread.Thread):

    def __init__(self):
        Thread.Thread.__init__(self, "Monitor")
        if _debug:
            print "Monitor.__init__"

        # keep a list of things that are being monitored
        self.monitor = []
        self.mutex = Thread.Lock(self)

        # set this event when all polling has stopped
        self.finished = threading.Event()

        # runs as a daemon
        self.setDaemon(1)
        self.go = 0

    def run(self):
        self.go = 1
        while self.go:
            if not self.monitor:
                time.sleep(0.1)
            else:
                asyncore.poll2(0.5)

        self.finished.set()

    def halt(self):
        # stop the polling thread
        self.go = 0
        self.finished.wait()

        # tell everything to close
        for elem in self.monitor:
            elem.handle_close()

    def Add(self, elem):
        """Add an asyncore.dispatcher object to the list of things to be monitored."""
        self.mutex.acquire()
        if _debug:
            print "Monitor.Add", elem
            
        self.monitor.append(elem)
        self.mutex.release()

    def Remove(self, elem):
        """Remove an asyncore.dispatcher object from the list of things to be monitored."""
        self.mutex.acquire()
        if _debug:
            print "Monitor.Remove", elem
        self.monitor.remove(elem)
        self.mutex.release()

monitor = Monitor()

#
#   TCPClient
#
#   This class is a mapping between the client/server pattern and the
#   socket API.  The ctor is given the address to connect as a TCP
#   client.  Because objects of this class sit at the bottom of a
#   protocol stack they are accessed as servers.
#

class TCPClient(asyncore.dispatcher):

    def __init__(self, peer):
        asyncore.dispatcher.__init__(self)

        if _debug:
            print self, "TCPClient.__init__", peer

        # ask the dispatcher for a socket
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)

        # save the peer
        self.peer = peer
        if _debug:
            print "    - peer:", peer

        # create a request buffer
        self.request = ''

        # the buffer needs a lock
        self.lock = Thread.Lock(self)
        if _debug:
            print "    - lock:", self.lock

        # try to connect the socket
        if _debug:
            print "    - try to connect"
        self.connect(peer)
        if _debug:
            print "    - connected (maybe)"
        
        # add this to the things to be monitored
        monitor.Add(self)

    def handle_connect(self):
        if _debug:
            print self, "TCPClient.handle_connect"

    def handle_expt(self):
#        if _debug:
#            print self, "TCPClient.handle_expt"
        pass
        
    def readable(self):
        return 1

    def handle_read(self):
        if _debug:
            print self, "TCPClient.handle_read"

        try:
            msg = self.recv(65536)
            if _debug:
                print "    - received", len(msg), "octets"

            # no socket means it was closed
            if not self.socket:
                if _debug:
                    print "    - socket was closed"
            else:
                # sent the data upstream
                self.Response( PDU(msg) )

        except socket.error, why:
            print "TCPClient.handle_read socket error:", why
            traceback.print_exc(file=sys.stdout)
            
    def writable(self):
#        if _debug:
#            print self, "TCPClient.writable"
#
        return (len(self.request) != 0)

    def handle_write(self):
        if _debug:
            print self, "TCPClient.handle_write"

        self.lock.acquire()

        try:
            sent = self.send(self.request)
            if _debug:
                print "    - sent", sent, "octets,", len(self.request) - sent, "remaining"

            self.request = self.request[sent:]
        except socket.error, why:
            print "TCPClient.handle_write socket error:", why
            traceback.print_exc(file=sys.stdout)

        self.lock.release()

    def handle_close(self):
        if _debug:
            print self, "TCPClient.handle_close"

        # remove from the monitor
        monitor.Remove(self)

        # close the socket
        self.close()
        
        # make sure other routines know the socket is closed
        self.socket = None

    def Indication(self, pdu):
        """Requests are queued for delivery."""
        if _debug:
            print self, "TCPClient.Indication", pdu

        self.lock.acquire()
        self.request += pdu.pduData
        self.lock.release()

#
#   TCPClientActor
#
#   Actors are helper objects for a director.  There is one actor for
#   each connection.
#

class TCPClientActor(TCPClient):

    def __init__(self, director, peer):
        TCPClient.__init__(self, peer)
        if _debug:
            print self, "TCPClientActor.__init__", director, peer

        # keep track of the director
        self.director = director

        # tell the director this is a new actor
        self.director.AddActor(self)

    def handle_close(self):
        if _debug:
            print self, "TCPClientActor.handle_close"

        # tell the director this is gone
        self.director.RemoveActor(self)

        # pass the function along
        TCPClient.handle_close(self)
            
    def Response(self, pdu):
        if _debug:
            print self, "TCPClientActor.Response", pdu

        # put the peer address in as the source
        pdu.pduSource = self.peer

        # tell the director
        self.director.Confirmation(pdu)

#
#   TCPClientDirector
#
#   A client director presents a connection pool as one virtual
#   interface.  If a request should be sent to an address and there
#   is no connection already established for it, it will create one
#   and maintain it.  PDU's from TCP clients have no source address,
#   so one is provided by the client actor.
#

class TCPClientDirector(Server, ServiceAccessPoint):

    def __init__(self, sapID=None):
        Server.__init__(self)
        ServiceAccessPoint.__init__(self, sapID)
        if _debug:
            print self, "TCPClientDirector.__init__"

        # start with an empty client pool
        self.clients = {}

    def AddActor(self, actor):
        """Add an actor when a new one is connected."""
        if _debug:
            print self, "TCPClientDirector.AddActor", actor

        self.clients[actor.peer] = actor
        
        # tell the ASE there is a new client
        if self.serviceElement:
            self.SAPRequest(addPeer=actor.peer)

    def RemoveActor(self, actor):
        """Remove an actor when the socket is closed."""
        if _debug:
            print self, "TCPClientDirector.RemoveActor", actor

        del self.clients[actor.peer]

        # tell the ASE the client has gone away
        if self.serviceElement:
            self.SAPRequest(delPeer=actor.peer)

    def Indication(self, pdu):
        """Redirect a message to the appropriate client, create a
        connection if one hasn't already been created."""
        if _debug:
            print self, "TCPClientDirector.Indication", pdu

        # get the destination
        addr = pdu.pduDestination

        # get the client
        client = self.clients.get(addr, None)
        if not client:
            client = TCPClientActor(self, addr)

        # send the message
        client.Indication(pdu)

    def Confirmation(self, pdu):
        """Messages from actors are redirected uptream."""
        if _debug:
            print self, "TCPClientDirector.Confirmation", pdu

        # forward it upstream
        self.Response(pdu)

#
#   TCPServer
#

class TCPServer(asyncore.dispatcher):

    def __init__(self, sock, peer):
        asyncore.dispatcher.__init__(self, sock)

        if _debug:
            print self, "TCPServer.__init__", sock, peer

        # save the peer
        self.peer = peer

        # create a request buffer
        self.request = ''

        # the buffer needs a lock
        self.lock = Thread.Lock(self)

        # add this to the things to be monitored
        monitor.Add(self)

    def handle_connect(self):
        if _debug:
            print self, "TCPServer.handle_connect"

    def readable(self):
        return 1

    def handle_read(self):
        if _debug:
            print self, "TCPServer.handle_read"

        try:
            msg = self.recv(65536)
            if _debug:
                print "    - received", len(msg), "octets"

            # no socket means it was closed
            if not self.socket:
                if _debug:
                    print "    - socket was closed"
            else:
                self.Response( PDU(msg) )

        except socket.error, why:
            print "TCPServer.handle_read socket error:", why
            traceback.print_exc(file=sys.stdout)

    def writable(self):
        return (len(self.request) != 0)

    def handle_write(self):
        if _debug:
            print self, "TCPServer.handle_write"

        try:
            self.lock.acquire()

            sent = self.send(self.request)
            if _debug:
                print "    - sent", sent, "octets,", len(self.request) - sent, "remaining"

            self.request = self.request[sent:]

            self.lock.release()
        except socket.error, why:
            print "TCPServer.handle_write socket error:", why
            traceback.print_exc(file=sys.stdout)

    def handle_close(self):
        if _debug:
            print self, "TCPServer.handle_close"

        monitor.Remove(self)

        self.close()
        self.socket = None

    def Indication(self, pdu):
        """Requests are queued for delivery."""
        if _debug:
            print self, "TCPServer.Indication", pdu

        self.lock.acquire()
        self.request += pdu.pduData
        self.lock.release()

#
#   TCPServerActor
#

class TCPServerActor(TCPServer):

    def __init__(self, director, sock, peer):
        TCPServer.__init__(self, sock, peer)
        if _debug:
            print self, "TCPServerActor.__init__", director, sock, peer

        # keep track of the director
        self.director = director

        # tell the director this is a new actor
        self.director.AddActor(self)

    def handle_close(self):
        if _debug:
            print self, "TCPServerActor.handle_close"

        # tell the director this is gone
        self.director.RemoveActor(self)

        # pass it down
        TCPServer.handle_close(self)

    def Response(self, pdu):
        if _debug:
            print self, "TCPServerActor.Response", pdu

        # save the source
        pdu.pduSource = self.peer

        # tell the director, flip the model
        self.director.Indication(pdu)

#
#   TCPServerDirector
#

class TCPServerDirector(asyncore.dispatcher, Client, ServiceAccessPoint):

    def __init__(self, port, sapID=None):
        asyncore.dispatcher.__init__(self)
        Client.__init__(self)
        ServiceAccessPoint.__init__(self, sapID)

        if _debug:
            print self, "TCPServerDirector.__init__", port

        # save the port
        self.port = port

        # create a listening port
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.bind(('',port))
        self.listen(5)

        # start with an empty pool of servers
        self.servers = {}

        # add this to the things to be monitored
        monitor.Add(self)

    def handle_accept(self):
        if _debug:
            print self, "TCPServerDirector.handle_accept"

        client, addr = self.accept()
        if _debug:
            print "    - connection from", addr

        # create a server
        server = TCPServerActor(self, client, addr)

        # add it to our pool
        self.servers[addr] = server

        # return it to the dispatcher
        return server

    def handle_close(self):
        if _debug:
            print self, "TCPServerDirector.handle_close"

        # remove this director (listener)
        monitor.Remove(self)

        # close the socket
        self.close()

    def AddActor(self, actor):
        if _debug:
            print self, "TCPServerDirector.AddActor", actor

        self.servers[actor.peer] = actor

        # tell the ASE there is a new server
        if self.serviceElement:
            self.SAPRequest(addPeer=actor.peer)

    def RemoveActor(self, actor):
        if _debug:
            print self, "TCPServerDirector.RemoveActor", actor

        del self.servers[actor.peer]

        # tell the ASE the server has gone away
        if self.serviceElement:
            self.SAPRequest(delPeer=actor.peer)

    def Indication(self, pdu):
        if _debug:
            print self, "TCPServerDirector.Indication", pdu

        # forward the request
        self.Request(pdu)

    def Confirmation(self, pdu):
        """figure out which stream this should go back to."""
        if _debug:
            print self, "TCPServerDirector.Confirmation", pdu

        # get the destination
        addr = pdu.pduDestination

        # get the server
        server = self.servers.get(addr, None)
        if not server:
            raise RuntimeError, "not a connected server"

        # flip the model
        server.Indication(pdu)

#
#   UDPDirector
#

class UDPDirector(asyncore.dispatcher, Server):

    def __init__(self, address):
        asyncore.dispatcher.__init__(self)
        Server.__init__(self)

        # save the address
        self.address = address

        if _debugUDPDirector:
            print self.address, "UDPDirector.__init__", address

        # ask the dispatcher for a socket
        self.create_socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.bind(address)
        
        # allow it to send broadcasts
        self.socket.setsockopt( socket.SOL_SOCKET, socket.SO_BROADCAST, 1 )

        # create the request queue
        self.request = Queue.Queue()

        # add this to the things to be monitored
        monitor.Add(self)

    def handle_connect(self):
        if _debugUDPDirector:
            print self.address, "UDPDirector.handle_connect"

    def readable(self):
        return 1

    def handle_read(self):
        if _debugUDPDirector:
            print self.address, "UDPDirector.handle_read"

        try:
            msg, addr = self.socket.recvfrom(65536)
            if _debugUDPDirector:
                print "    - received", len(msg), "octets from", addr

            # send the PDU up to the client
            self.Response( PDU(msg, source=addr) )

        except socket.error, why:
            print "UDPDirector.handle_read socket error:", why
            traceback.print_exc(file=sys.stdout)

    def writable(self):
        """Return true iff there is a request pending."""
        if _debugUDPDirector:
            print self.address, "UDPDirector.writable"
            print "    - request:", self.request
            
        status = (not self.request.empty())
        if _debugUDPDirector:
            print "    - status:", status
            
        return status

    def handle_write(self):
        """Get a PDU from the queue and send it."""
        if _debugUDPDirector:
            print self.address, "UDPDirector.handle_write"
            print "    - request:", self.request

        try:
            pdu = self.request.get()

            sent = self.socket.sendto(pdu.pduData, pdu.pduDestination)
            if _debugUDPDirector:
                print "    - sent", sent, "octets to", pdu.pduDestination

        except socket.error, why:
            print "UDPDirector.handle_write socket error:", why
            print "    - pdu.pduDestination:", pdu.pduDestination
            traceback.print_exc(file=sys.stdout)

    def handle_close(self):
        """Remove this from the monitor when it's closed."""
        if _debugUDPDirector:
            print self.address, "UDPDirector.handle_close"

        monitor.Remove(self)

        self.close()
        self.socket = None

    def Indication(self, pdu):
        if _debugUDPDirector:
            print self.address, "UDPDirector.Indication", pdu

        """Client requests are queued for delivery."""
        self.request.put(pdu)
        if _debugUDPDirector:
            print "    - request:", self.request
            print "    - request is empty:", self.request.empty()

#
#   StreamToPacket
#

class StreamToPacket(Client, Server):

    def __init__(self, fn, cid=None, sid=None):
        Client.__init__(self, cid)
        Server.__init__(self, sid)
        
        # save the packet function
        self.packetFn = fn
        
        # start with an empty set of buffers
        self.upstreamBuffer = {}
        self.downstreamBuffer = {}
        
    def Packetize(self, pdu, streamBuffer):
        if _debug:
            print "StreamToPacket.Packetize", pdu
            
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
        if _debug:
            print "StreamToPacket.Indication", pdu
            
        # hack it up into chunks
        for packet in self.Packetize(pdu, self.downstreamBuffer):
            self.Request(packet)
            
    def Confirmation(self, pdu):
        """Message going upstream."""
        if _debug:
            print "StreamToPacket.Confirmation", pdu
            
        # hack it up into chunks
        for packet in self.Packetize(pdu, self.upstreamBuffer):
            self.Response(packet)
            
#
#   StreamToPacketSAP
#

class StreamToPacketSAP(ApplicationServiceElement, ServiceAccessPoint):

    def __init__(self, stp, aseID, sapID):
        ApplicationServiceElement.__init__(self, aseID)
        ServiceAccessPoint.__init__(self, sapID)
        
        # save a reference to the StreamToPacket object
        self.stp = stp
        
    def Indication(self, addPeer=None, delPeer=None):
        if _debug:
            print "StreamToPacketSAP.Indication"
            if addPeer:
                print "    - addPeer:", addPeer
            if delPeer:
                print "    - delPeer:", delPeer
            print "    - upstream data:", repr(self.stp.upstreamBuffer.get(delPeer, None))
            print "    - downstream data:", repr(self.stp.downstreamBuffer.get(delPeer, None))
                
        if delPeer:
            if _debug:
                print "    - delPeer:", delPeer
                
            # delete the buffer contents associated with the peer
            try:
                del self.stp.upstreamBuffer[delPeer]
            except KeyError:
                pass
            try:
                del self.stp.downstreamBuffer[delPeer]
            except KeyError:
                pass
            
        # chain this along
        if self.serviceElement:
            self.SAPRequest(addPeer=addPeer, delPeer=delPeer)

