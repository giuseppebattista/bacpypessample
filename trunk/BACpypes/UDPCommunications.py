#!/usr/bin/env python

"""
UDPCommunications Module
"""

import sys
import asyncore
import socket
import traceback
import cPickle
import logging
import Queue

from time import time as _time

from Debugging import Logging

from Core import deferred
from Task import FunctionTask
from CommunicationsCore import PDU, Server
from CommunicationsCore import ServiceAccessPoint

# some debugging
_log = logging.getLogger(__name__)

#
#   UDPActor
#
#   Actors are helper objects for a director.  There is one actor for
#   each peer.
#

class UDPActor(Logging):

    def __init__(self, director, peer):
        UDPActor._debug("__init__ %r %r", director, peer)

        # keep track of the director
        self.director = director

        # associated with a peer
        self.peer = peer
        
        # add a timer
        self.timeout = director.timeout
        if self.timeout > 0:
            self.timer = FunctionTask(self.IdleTimeout)
            self.timer.InstallTask(_time() + self.timeout)
        else:
            self.timer = None
        
        # tell the director this is a new actor
        self.director.AddActor(self)

    def IdleTimeout(self):
        UDPActor._debug("IdleTimeout")
        
        # tell the director this is gone
        self.director.RemoveActor(self)

    def Indication(self, pdu):
        UDPActor._debug("Indication %r", pdu)

        # reschedule the timer
        if self.timer:
            self.timer.InstallTask(_time() + self.timeout)
        
        # put it in the outbound queue for the director
        self.director.request.put(pdu)

    def Response(self, pdu):
        UDPActor._debug("Response %r", pdu)

        # reschedule the timer
        if self.timer:
            self.timer.InstallTask(_time() + self.timeout)
        
        # process this as a response from the director
        self.director.Response(pdu)

#
#   UDPPickleActor
#

class UDPPickleActor(UDPActor, Logging):

    def __init__(self, *args):
        UDPPickleActor._debug("__init__ %r", args)
        UDPActor.__init__(self, *args)

    def Indication(self, pdu):
        UDPPickleActor._debug("Indication %r", pdu)

        # pickle the data
        pdu.pduData = cPickle.dumps(pdu.pduData)
        
        # continue as usual
        UDPActor.Indication(self, pdu)

    def Response(self, pdu):
        UDPPickleActor._debug("Response %r", pdu)

        # unpickle the data
        try:
            pdu.pduData = cPickle.loads(pdu.pduData)
        except:
            UDPPickleActor._exception("pickle error")
            return
            
        # continue as usual
        UDPActor.Response(self, pdu)

#
#   UDPDirector
#

class UDPDirector(asyncore.dispatcher, Server, ServiceAccessPoint, Logging):

    def __init__(self, address, timeout=0, actorClass=UDPActor, sid=None, sapID=None):
        UDPDirector._debug("__init__ %r timeout=%r actorClass=%r sid=%r sapID=%r", address, timeout, actorClass, sid, sapID)
        Server.__init__(self, sid)
        ServiceAccessPoint.__init__(self, sapID)
        
        # check the actor class
        if not issubclass(actorClass, UDPActor):
            raise TypeError, "actorClass must be a subclass of UDPActor"
        self.actorClass = actorClass
        
        # save the timeout for actors
        self.timeout = timeout
        
        # save the address
        self.address = address

        asyncore.dispatcher.__init__(self)

        # ask the dispatcher for a socket
        self.create_socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.bind(address)
        
        # allow it to send broadcasts
        self.socket.setsockopt( socket.SOL_SOCKET, socket.SO_BROADCAST, 1 )

        # create the request queue
        self.request = Queue.Queue()

        # start with an empty peer pool
        self.peers = {}

    def AddActor(self, actor):
        """Add an actor when a new one is connected."""
        UDPDirector._debug("AddActor %r", actor)

        self.peers[actor.peer] = actor
        
        # tell the ASE there is a new client
        if self.serviceElement:
            self.SAPRequest(addPeer=actor.peer)

    def RemoveActor(self, actor):
        """Remove an actor when the socket is closed."""
        UDPDirector._debug("RemoveActor %r", actor)

        del self.peers[actor.peer]

        # tell the ASE the client has gone away
        if self.serviceElement:
            self.SAPRequest(delPeer=actor.peer)

    def GetActor(self, address):
        return self.peers.get(address, None)
        
    def handle_connect(self):
        UDPDirector._debug("handle_connect")

    def readable(self):
        return 1

    def handle_read(self):
        deferred(UDPDirector._debug, "handle_read")

        try:
            msg, addr = self.socket.recvfrom(65536)
            deferred(UDPDirector._debug, "    - received %d octets from %s", len(msg), addr)

            # send the PDU up to the client
            deferred(self._Response, PDU(msg, source=addr))

        except socket.timeout, why:
            deferred(UDPDirector._error, "handle_read socket timeout: %s", why)
        except socket.error, why:
            if why[0] == 11:
                pass
            else:
                deferred(UDPDirector._error, "handle_read socket error: %s", why)

    def writable(self):
        """Return true iff there is a request pending."""
        return (not self.request.empty())

    def handle_write(self):
        """Get a PDU from the queue and send it."""
        deferred(UDPDirector._debug, "handle_write")

        try:
            pdu = self.request.get()

            sent = self.socket.sendto(pdu.pduData, pdu.pduDestination)
            deferred(UDPDirector._debug, "    - sent %d octets to %s", sent, pdu.pduDestination)

        except socket.error, why:
            print self.address, "UDPDirector.handle_write socket error:", why
            print "    - pdu.pduDestination:", pdu.pduDestination
            traceback.print_exc(file=sys.stdout)

    def handle_close(self):
        """Remove this from the monitor when it's closed."""
        UDPDirector._debug("handle_close")

        self.close()
        self.socket = None

    def Indication(self, pdu):
        """Client requests are queued for delivery."""
        UDPDirector._debug("Indication %r", pdu)
        
        # get the destination
        addr = pdu.pduDestination

        # get the peer
        peer = self.peers.get(addr, None)
        if not peer:
            peer = self.actorClass(self, addr)

        # send the message
        peer.Indication(pdu)

    def _Response(self, pdu):
        """Incoming datagrams are routed through an actor."""
        UDPDirector._debug("_Response %r", pdu)
        
        # get the destination
        addr = pdu.pduSource

        # get the peer
        peer = self.peers.get(addr, None)
        if not peer:
            peer = self.actorClass(self, addr)

        # send the message
        peer.Response(pdu)

