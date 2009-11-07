
"""
VLAN
"""

import random
import logging

from Debugging import Logging

from PDU import Address
from Task import OneShotFunction
from CommunicationsCore import Server
from Exceptions import ConfigurationError

# some debugging
_log = logging.getLogger(__name__)

#
#   VLAN
#

class VLAN(Logging):

    def __init__(self, dropPercent=0):
        VLAN._debug("__init__ dropPercent=%r", dropPercent)

        self.nodes = []
        self.dropPercent = dropPercent

    def AddNode(self, node):
        VLAN._debug("AddNode %r", node)

        self.nodes.append(node)
        node.lan = self

    def RemoveNode(self, node):
        VLAN._debug("RemoveNode %r", node)

        self.nodes.remove(node)
        node.lan = None

    def ProcessPDU(self, pdu):
        VLAN._debug("ProcessPDU %r", pdu)

        if self.dropPercent != 0:
            if (random.random() * 100.0) < self.dropPercent:
                VLAN._debug("    - packet dropped")
                return

        if not pdu.pduDestination or not isinstance(pdu.pduDestination, Address):
            raise RuntimeError, "invalid destination address"
            
        elif pdu.pduDestination.addrType == Address.localBroadcastAddr:
            for n in self.nodes:
                if (pdu.pduSource != n.address):
                    n.Response(pdu)
                    
        elif pdu.pduDestination.addrType == Address.localStationAddr:
            for n in self.nodes:
                if n.promiscuous or (pdu.pduDestination == n.address):
                    n.Response(pdu)
                    
        else:
            raise RuntimeError, "invalid destination address type"

#
#   VLANNode
#

class VLANNode(Server, Logging):

    def __init__(self, addr, lan=None, promiscuous=False, sid=None):
        VLANNode._debug("__init__ %r lan=%r promiscuous=%r sid=%r", addr, lan, promiscuous, sid)
        Server.__init__(self, sid)

        if not isinstance(addr, Address):
            raise TypeError, "addr must be an address"
            
        self.lan = None
        self.address = addr

        # bind to a lan if it was provided
        if lan:
            self.Bind(lan)

        # might receive all packets
        self.promiscuous = promiscuous

    def Bind(self, lan):
        """Bind to a LAN."""
        VLANNode._debug("Bind %r", lan)

        lan.AddNode(self)

    def Indication(self, pdu):
        """Send a message."""
        VLANNode._debug("Indication %r", pdu)

        # make sure we're connected
        if not self.lan:
            raise ConfigurationError, "unbound VLAN node"

        # if the pduSource is unset, fill in our address, otherwise 
        # leave it alone to allow for simulated spoofing
        if pdu.pduSource is None:
            pdu.pduSource = self.address
            
        # build a VLAN message which will be scheduled
        OneShotFunction(self.lan.ProcessPDU, pdu)

