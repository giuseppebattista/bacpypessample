#!/usr/bin/env python

"""
CommunicationsCore Module
"""

import sys
import struct
import types
import logging

from Exceptions import *
from Debugging import DebugContents, Logging, FunctionLogging

# some debugging
_log = logging.getLogger(__name__)

def _StringToHex(x, sep=''):
    return sep.join(["%02X" % (ord(c),) for c in x])

def _HexToString(x, sep=''):
    if sep:
        parts = x.split(sep)
    else:
        parts = [x[i:i+2] for i in range(0,len(x),2)]
    
    return ''.join(chr(int(part,16)) for part in parts)

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

    def __init__(self, label=None, cid=None, sid=None):
        Client.__init__(self, cid)
        Server.__init__(self, sid)
        self.label = label
        
    def Confirmation(self, *args, **kwargs):
        print "Debug(%s).Confirmation" % (self.label,)
        for i, arg in enumerate(args):
            print "    - args[%d]:" % (i,), arg
            if hasattr(arg, 'DebugContents'):
                arg.DebugContents(2)
        for key, value in kwargs.items():
            print "    - kwargs[%r]:" % (key,), value
            if hasattr(value, 'DebugContents'):
                value.DebugContents(2)

        if self.serverPeer:
            self.Response(*args, **kwargs)
        
    def Indication(self, *args, **kwargs):
        print "Debug(%s).Indication" % (self.label,)
        for i, arg in enumerate(args):
            print "    - args[%d]:" % (i,), arg
            if hasattr(arg, 'DebugContents'):
                arg.DebugContents(2)
        for key, value in kwargs.items():
            print "    - kwargs[%r]:" % (key,), value
            if hasattr(value, 'DebugContents'):
                value.DebugContents(2)

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

class ServiceAccessPoint(Logging):

    def __init__(self, sapID=None):
        ServiceAccessPoint._debug("__init__(%s)", sapID)
            
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
        ServiceAccessPoint._debug("SAPRequest(%s) %r %r", self.serviceID, args, kwargs)
            
        if not self.serviceElement:
            raise ConfigurationError, "unbound service access point"
        self.serviceElement.Indication(*args, **kwargs)

    def SAPIndication(self, *args, **kwargs):
        raise NotImplementedError, "SAPIndication must be overridden"

    def SAPResponse(self, *args, **kwargs):
        ServiceAccessPoint._debug("SAPResponse(%s) %r %r", self.serviceID, args, kwargs)
            
        if not self.serviceElement:
            raise ConfigurationError, "unbound service access point"
        self.serviceElement.Confirmation(*args,**kwargs)

    def SAPConfirmation(self, *args, **kwargs):
        raise NotImplementedError, "SAPConfirmation must be overridden"

#
#   ApplicationServiceElement
#

class ApplicationServiceElement(Logging):

    def __init__(self, aseID=None):
        ApplicationServiceElement._debug("__init__(%s)", aseID)
            
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
        ApplicationServiceElement._debug("Request(%s)  %r %r", self.elementID, args, kwargs)
            
        if not self.elementService:
            raise ConfigurationError, "unbound application service element"

        self.elementService.SAPIndication(*args, **kwargs)

    def Indication(self, *args, **kwargs):
        raise NotImplementedError, "Indication must be overridden"

    def Response(self, *args, **kwargs):
        ApplicationServiceElement._debug("Response(%s) %r %r", self.elementID, args, kwargs)
            
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

@FunctionLogging
def Bind(*args):
    """Bind a list of clients and servers together, top down."""
    Bind._debug("Bind %r", args)
        
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
        Bind._debug("    - client: %r", client)
        Bind._debug("    - server: %r", server)

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

        Bind._debug("    - bound")
        
#
#   PDUData
#

class PDUData(object):

    def __init__(self, data=''):
        if isinstance(data, PDUData):
            self.pduData = data.pduData
        else:
            self.pduData = data

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
        self.pduData += chr(ch)

    def PutData(self, data):
        self.pduData += data

    def PutShort(self, n):
        self.pduData += struct.pack('>H',n & _shortMask)

    def PutLong(self, n):
        self.pduData += struct.pack('>L',n & _longMask)

    def DebugContents(self, indent=1, file=sys.stdout, _ids=None):
        if isinstance(self.pduData, types.StringType):
            if len(self.pduData) > 20:
                hexed = _StringToHex(self.pduData[:20],'.') + "..."
            else:
                hexed = _StringToHex(self.pduData,'.')
            file.write("%spduData = x'%s'\n" % ('    ' * indent, hexed))
        else:
            file.write("%spduData = %r\n" % ('    ' * indent, self.pduData))
    
#
#   PCI
#

class PCI(DebugContents):

    _debugContents = ('pduSource', 'pduDestination')
    
    def __init__(self, **kwargs):
        # pick up some optional kwargs
        self.pduSource = kwargs.get('source', None)
        self.pduDestination = kwargs.get('destination', None)
        
    def update(self, pci):
        """Copy the PCI fields."""
        self.pduSource = pci.pduSource
        self.pduDestination = pci.pduDestination

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

