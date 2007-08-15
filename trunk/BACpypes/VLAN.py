
"""
VLAN
"""

import random

from PDU import Address, LocalBroadcast, PDU
from Task import OneShotDeleteTask
from CommunicationsCore import Server

# some debugging
_debug = 0

#
#   VLANMessage
#

class VLANMessage(OneShotDeleteTask):
    """VLANMessage objects are used to transfer content from the VLAN port threads
    to the task manager thread."""

    def __init__(self, lan, pdu):
        OneShotDeleteTask.__init__(self, 0)

        # save the LAN reference and PDU
        self.lan = lan
        self.pdu = pdu

    def ProcessTask(self):
        self.lan.ProcessPDU(pdu)

#
#   VLAN
#

class VLAN:

    def __init__(self, dropPercent=0):
        if _debug:
            print self, "VLAN.__init__"

        self.nodes = []
        self.dropPercent = dropPercent

    def AddNode(self, node):
        if _debug:
            print self, "VLAN.AddNode", node

        self.nodes.append(node)
        node.lan = self

    def RemoveNode(self, node):
        if _debug:
            print self, "VLAN.RemoveNode", node

        self.nodes.remove(node)
        node.lan = None

    def ProcessPDU(self, pdu):
        """Process a PDU from a station."""
        if _debug:
            print self, "VLAN.ProcessPDU", pdu

        if self.dropPercent != 0:
            if (random.random() * 100.0) < self.dropPercent:
                if _debug:
                    print "    - *** packet dropped ***"
                return

        if pdu.pduDestination.addrType == Address.localBroadcastAddr:
            for n in self.nodes:
                if (pdu.pduSource != n.address):
                    n.Response(pdu)
        else:
            for n in self.nodes:
                if n.promiscuous or (pdu.pduDestination == n.address):
                    n.Response(pdu)

#
#   VLANNode
#

class VLANNode(Server):

    def __init__(self, addr, lan=None, promiscuous=False, sid=None):
        Server.__init__(self, sid)
        if _debug:
            print self, "VLANNode.__init__", addr, lan, sid

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
        if _debug:
            print self, "VLANNode.Bind", lan

        lan.AddNode(self)

    def Indication(self, pdu):
        """Send a message."""
        if _debug:
            print self, "VLANNode.Indication", pdu

        # make sure we're connected
        if not self.lan:
            raise ConfigurationError, "unbound VLAN node"

        # if the pduSource is unset, fill in our address, otherwise 
        # leave it alone to allow for simulated spoofing
        if pdu.pduSource is None:
            pdu.pduSource = self.address
            
        # build a VLAN message which will be scheduled
        newpdu = VLANMessage(self.lan, pdu)

        # install it
        newpdu.InstallTask()
