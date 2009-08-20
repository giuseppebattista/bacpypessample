
from Exceptions import *

from PDU import *

# some debuging
_debug = 0

# a dictionary of message type values and classes
NPDUTypes = {}

def RegisterNPDUType(klass):
    NPDUTypes[klass.messageType] = klass

#
#  NPCI
#

class NPCI(PCI):
    whoIsRouterToNetwork            = 0x00
    iAmRouterToNetwork              = 0x01
    iCouldBeRouterToNetwork         = 0x02
    rejectMessageToNetwork          = 0x03
    routerBusyToNetwork             = 0x04
    routerAvailableToNetwork        = 0x05
    initializeRoutingTable          = 0x06
    initializeRoutingTableAck       = 0x07
    establishConnectionToNetwork    = 0x08
    disconnectConnectionToNetwork   = 0x09

    def __init__(self, *args):
        PCI.__init__(self, *args)
        self.npduVersion = 1
        self.npduControl = None
        self.npduDADR = None
        self.npduSADR = None
        self.npduHopCount = None
        self.npduNetMessage = None
        self.npduVendorID = None

    def update(self, npci):
        PCI.update(self, npci)
        self.npduVersion = npci.npduVersion
        self.npduControl = npci.npduControl
        self.npduDADR = npci.npduDADR
        self.npduSADR = npci.npduSADR
        self.npduHopCount = npci.npduHopCount
        self.npduNetMessage = npci.npduNetMessage
        self.npduVendorID = npci.npduVendorID

    def Encode(self, pdu):
        """Encode the contents of the NPCI into the PDU."""
        if _debug:
            print "NPDU.Encode"

        PCI.update(pdu, self)
        
        # only version 1 messages supported
        pdu.Put(self.npduVersion)

        # build the flags
        if self.npduNetMessage is not None:
            if _debug:
                print "    - network layer message"
            netLayerMessage = 0x80
        else:
            if _debug:
                print "    - application layer message"
            netLayerMessage = 0x00

        if _debug:
            print "    - npduDADR", self.npduDADR

        # map the destination address
        dnetPresent = 0x00
        if self.npduDADR is not None:
            if _debug:
                print "    - dnet/dlen/dadr present"
            dnetPresent = 0x20

        # map the source address
        snetPresent = 0x00
        if self.npduSADR is not None:
            if _debug:
                print "    - dnet/dlen/dadr present"
            snetPresent = 0x08

        # encode the control octet
        control = netLayerMessage | dnetPresent | snetPresent
        if self.pduExpectingReply:
            control |= 0x04
        control |= (self.pduNetworkPriority & 0x03)
        if _debug:
            print "    - control 0x%02X" % (control,)
        self.npduControl = control
        pdu.Put(control)

        # make sure expecting reply and priority get passed down
        pdu.pduExpectingReply = self.pduExpectingReply
        pdu.pduNetworkPriority = self.pduNetworkPriority

        # encode the destination address
        if dnetPresent:
            if self.npduDADR.addrType == Address.remoteStationAddr:
                pdu.PutShort(self.npduDADR.addrNet)
                pdu.Put(self.npduDADR.addrLen)
                pdu.PutData(self.npduDADR.addrAddr)
            elif self.npduDADR.addrType == Address.remoteBroadcastAddr:
                pdu.PutShort(self.npduDADR.addrNet)
                pdu.Put(0)
            elif self.npduDADR.addrType == Address.globalBroadcastAddr:
                pdu.PutShort(0xFFFF)
                pdu.Put(0)

        # encode the source address
        if snetPresent:
            pdu.PutShort(self.npduSADR.addrNet)
            pdu.Put(self.npduSADR.addrLen)
            pdu.PutData(self.npduSADR.addrAddr)

        # put the hop count
        if dnetPresent:
            pdu.Put(self.npduHopCount)

        # put the network layer message type (if present)
        if netLayerMessage:
            pdu.Put(self.npduNetMessage)
            # put the vendor ID
            if (self.npduNetMessage >= 0x80) and (self.npduNetMessage <= 0xFF):
                pdu.PutShort(self.npduVendorID)

    def Decode(self, pdu):
        """Decode the contents of the PDU and put them into the NPDU."""
        if _debug:
            print "NPDU.Decode"

        PCI.update(self, pdu)

        # check the length
        if len(pdu.pduData) < 2:
            raise DecodingError, "invalid length"

        # only version 1 messages supported
        self.npduVersion = pdu.Get()
        if (self.npduVersion != 0x01):
            raise DecodingError, "only version 1 messages supported"

        # decode the control octet
        self.npduControl = control = pdu.Get()
        netLayerMessage = control & 0x80
        dnetPresent = control & 0x20
        snetPresent = control & 0x08
        self.pduExpectingReply = (control & 0x04) != 0
        self.pduNetworkPriority = control & 0x03

        # extract the destination address
        if dnetPresent:
            dnet = pdu.GetShort()
            dlen = pdu.Get()
            dadr = pdu.GetData(dlen)

            if dnet == 0xFFFF:
                self.npduDADR = GlobalBroadcast()
            elif dlen == 0:
                self.npduDADR = RemoteBroadcast(dnet)
            else:
                self.npduDADR = RemoteStation(dnet, dadr)

        # extract the source address
        if snetPresent:
            snet = pdu.GetShort()
            slen = pdu.Get()
            sadr = pdu.GetData(slen)

            if snet == 0xFFFF:
                raise DecodingError, "SADR can't be a global broadcast"
            elif slen == 0:
                raise DecodingError, "SADR can't be a remote broadcast"

            self.npduSADR = RemoteStation(snet, sadr)

        # extract the hop count
        if dnetPresent:
            self.npduHopCount = pdu.Get()

        # extract the network layer message type (if present)
        if netLayerMessage:
            self.npduNetMessage = pdu.Get()
            if (self.npduNetMessage >= 0x80) and (self.npduNetMessage <= 0xFF):
                # extract the vendor ID
                self.npduVendorID = pdu.GetShort()
        else:
            # application layer message
            self.npduNetMessage = None

    def DebugContents(self):
        PCI.DebugContents(self)
        if self.npduVersion is not None:
            print "    npduVersion =", self.npduVersion
        if self.npduControl is not None:
            print "    npduControl =", self.npduControl
        if self.npduDADR is not None:
            print "    npduDADR =", self.npduDADR
        if self.npduSADR is not None:
            print "    npduSADR =", self.npduSADR
        if self.npduHopCount is not None:
            print "    npduHopCount =", self.npduHopCount
        if self.npduNetMessage is not None:
            print "    npduNetMessage =", self.npduNetMessage, NPDUTypes.get(self.npduNetMessage, '?')
        if self.npduVendorID is not None:
            print "    npduVendorID =", self.npduVendorID

#
#   NPDU
#

class NPDU(NPCI, PDUData):

    def __init__(self, *args):
        NPCI.__init__(self)
        PDUData.__init__(self, *args)

    def Encode(self, pdu):
        NPCI.Encode(self, pdu)
        pdu.PutData(self.pduData)

    def Decode(self, pdu):
        NPCI.Decode(self, pdu)
        self.pduData = pdu.GetData(len(pdu.pduData))

    def DebugContents(self):
        NPCI.DebugContents(self)
        PDUData.DebugContents(self)

#------------------------------

#
#   WhoIsRouterToNetwork
#

class WhoIsRouterToNetwork(NPCI):
    messageType = 0x00

    def __init__(self, net=None):
        NPCI.__init__(self)
        self.npduNetMessage = WhoIsRouterToNetwork.messageType
        self.wirtnNetwork = net
        
    def Encode(self, npdu):
        if _debug:
            print self, "WhoIsRouterToNetwork.Encode", npdu
            
        NPCI.update(npdu, self)
        if self.wirtnNetwork is not None:
            npdu.PutShort( self.wirtnNetwork )
    
    def Decode(self, npdu):
        NPCI.update(self, npdu)
        if npdu.pduData:
            self.wirtnNetwork = npdu.GetShort()
        else:
            self.wirtnNetwork = None

    def DebugContents(self):
        NPCI.DebugContents(self)
        if self.wirtnNetwork is not None:
            print "    wirtnNetwork =", self.wirtnNetwork
            
RegisterNPDUType(WhoIsRouterToNetwork)

#
#   IAmRouterToNetwork
#

class IAmRouterToNetwork(NPCI):
    messageType = 0x01

    def __init__(self, netList=[]):
        NPCI.__init__(self)
        self.npduNetMessage = IAmRouterToNetwork.messageType
        self.iartnNetworkList = netList
        
    def Encode(self, npdu):
        NPCI.update(npdu, self)
        for net in self.iartnNetworkList:
            npdu.PutShort(net)
    
    def Decode(self, npdu):
        NPCI.update(self, npdu)
        self.iartnNetworkList = []
        while npdu.pduData:
            self.iartnNetworkList.append(npdu.GetShort())

    def DebugContents(self):
        NPCI.DebugContents(self)
        if self.iartnNetworkList is not None:
            print "    iartnNetworkList =", self.iartnNetworkList
            
RegisterNPDUType(IAmRouterToNetwork)

#
#   ICouldBeRouterToNetwork
#

class ICouldBeRouterToNetwork(NPCI):
    messageType = 0x02

    def __init__(self, net=None, perf=None):
        NPCI.__init__(self)
        self.npduNetMessage = ICouldBeRouterToNetwork.messageType
        self.icbrtnNetwork = net
        self.icbrtnPerformanceIndex = perf
        
    def Encode(self, npdu):
        NPCI.update(npdu, self)
        npdu.PutShort( self.icbrtnNetwork )
        npdu.Put( self.icbrtnPerformanceIndex )
    
    def Decode(self, npdu):
        NPCI.update(self, npdu)
        self.icbrtnNetwork = npdu.GetShort()
        self.icbrtnPerformanceIndex = npdu.Get()

    def DebugContents(self):
        NPCI.DebugContents(self)
        if self.icbrtnNetwork is not None:
            print "    icbrtnNetwork =", self.icbrtnNetwork
        if self.icbrtnPerformanceIndex is not None:
            print "    icbrtnPerformanceIndex =", self.icbrtnPerformanceIndex
            
RegisterNPDUType(ICouldBeRouterToNetwork)

#
#   RejectMessageToNetwork
#

class RejectMessageToNetwork(NPCI):
    messageType = 0x03

    def __init__(self, reason=None, dnet=None):
        NPCI.__init__(self)
        self.npduNetMessage = RejectMessageToNetwork.messageType
        self.rmtnRejectionReason = reason
        self.rmtnDNET = dnet
        
    def Encode(self, npdu):
        NPCI.update(npdu, self)
        npdu.Put( self.rmtnRejectionReason )
        npdu.PutShort( self.rmtnDNET )
    
    def Decode(self, npdu):
        NPCI.update(self, npdu)
        self.rmtnRejectionReason = npdu.Get()
        self.rmtnDNET = npdu.GetShort()

    def DebugContents(self):
        NPCI.DebugContents(self)
        if self.rmtnRejectionReason is not None:
            print "    rmtnRejectionReason =", self.rmtnRejectionReason
        if self.rmtnDNET is not None:
            print "    rmtnDNET =", self.rmtnDNET
            
RegisterNPDUType(RejectMessageToNetwork)

#
#   RouterBusyToNetwork
#

class RouterBusyToNetwork(NPCI):
    messageType = 0x04

    def __init__(self, netList=[]):
        NPCI.__init__(self)
        self.npduNetMessage = RouterBusyToNetwork.messageType
        self.rbtnNetworkList = netList
        
    def Encode(self, npdu):
        NPCI.update(npdu, self)
        for net in self.ratnNetworkList:
            npdu.PutShort(net)
    
    def Decode(self, npdu):
        NPCI.update(self, npdu)
        self.rbtnNetworkList = []
        while npdu.pduData:
            self.rbtnNetworkList.append(npdu.GetShort())

    def DebugContents(self):
        NPCI.DebugContents(self)
        if self.rbtnNetworkList is not None:
            print "    rbtnNetworkList =", self.rbtnNetworkList
            
RegisterNPDUType(RouterBusyToNetwork)

#
#   RouterAvailableToNetwork
#

class RouterAvailableToNetwork(NPCI):
    messageType = 0x05

    def __init__(self, netList=[]):
        NPCI.__init__(self)
        self.npduNetMessage = RouterAvailableToNetwork.messageType
        self.ratnNetworkList = netList
        
    def Encode(self, npdu):
        NPCI.update(npdu, self)
        for net in self.ratnNetworkList:
            npdu.PutShort(net)
    
    def Decode(self, npdu):
        NPCI.update(self, npdu)
        self.ratnNetworkList = []
        while npdu.pduData:
            self.ratnNetworkList.append(npdu.GetShort())

    def DebugContents(self):
        NPCI.DebugContents(self)
        if self.ratnNetworkList is not None:
            print "    ratnNetworkList =", self.ratnNetworkList
            
RegisterNPDUType(RouterAvailableToNetwork)

#
#   Routing Table Entry
#

class RTEntry:

    def __init__(self, dnet=None, portID=None, portInfo=None):
        self.rtDNET = dnet
        self.rtPortID = portID
        self.rtPortInfo = portInfo

#
#   InitializeRoutingTable
#

class InitializeRoutingTable(NPCI):
    messageType = 0x06

    def __init__(self, routingTable=[]):
        NPCI.__init__(self)
        self.npduNetMessage = InitializeRoutingTable.messageType
        self.irtTable = routingTable
        
    def Encode(self, npdu):
        NPCI.update(npdu, self)
        npdu.Put(len(self.irtTable))
        for rte in self.irtTable:
            npdu.PutShort(rte.rtDNET)
            npdu.Put(rte.rtPortID)
            npdu.Put(len(rte.rtPortInfo))
            npdu.PutData(rte.rtPortInfo)
    
    def Decode(self, npdu):
        NPCI.update(self, npdu)
        self.irtTable = []
        
        rtLength = npdu.Get()
        for i in range(rtLength):
            dnet = npdu.GetShort()
            portID = npdu.Get()
            portInfoLen = npdu.Get()
            portInfo = npdu.GetData(portInfoLen)
            rte = RTEntry(dnet, portID, portInfo)
            self.irtTable.append(rte)

RegisterNPDUType(InitializeRoutingTable)

#
#   InitializeRoutingTableAck
#

class InitializeRoutingTableAck(NPCI):
    messageType = 0x07

    def __init__(self, routingTable=[]):
        NPCI.__init__(self)
        self.npduNetMessage = InitializeRoutingTableAck.messageType
        self.irtaTable = routingTable
        
    def Encode(self, npdu):
        NPCI.update(npdu, self)
        npdu.Put(len(self.irtaTable))
        for rte in self.irtaTable:
            npdu.PutShort(rte.rtDNET)
            npdu.Put(rte.rtPortID)
            npdu.Put(len(rte.rtPortInfo))
            npdu.PutData(rte.rtPortInfo)
    
    def Decode(self, npdu):
        NPCI.update(self, npdu)
        self.irtaTable = []
        
        rtLength = npdu.Get()
        for i in range(rtLength):
            dnet = npdu.GetShort()
            portID = npdu.Get()
            portInfoLen = npdu.Get()
            portInfo = npdu.GetData(portInfoLen)
            rte = RTEntry(dnet, portID, portInfo)
            self.irtaTable.append(rte)

RegisterNPDUType(InitializeRoutingTableAck)

#
#   EstablishConnectionToNetwork
#

class EstablishConnectionToNetwork(NPCI):
    messageType = 0x08

    def __init__(self, dnet=None, terminationTime=None):
        NPCI.__init__(self)
        self.npduNetMessage = EstablishConnectionToNetwork.messageType
        self.ectnDNET = dnet
        self.ectnTerminationTime = terminationTime
        
    def Encode(self, npdu):
        NPCI.update(npdu, self)
        npdu.PutShort( self.ectnDNET )
        npdu.Put( self.ectnTerminationTime )
    
    def Decode(self, npdu):
        NPCI.update(self, npdu)
        self.ectnDNET = npdu.GetShort()
        self.ectnTerminationTime = npdu.Get()

    def DebugContents(self):
        NPCI.DebugContents(self)
        if self.ectnDNET is not None:
            print "    ectnDNET =", self.ectnDNET
        if self.ectnTerminationTime is not None:
            print "    ectnTerminationTime =", self.ectnTerminationTime
            
RegisterNPDUType(EstablishConnectionToNetwork)

#
#   DisconnectConnectionToNetwork
#

class DisconnectConnectionToNetwork(NPCI):
    messageType = 0x09

    def __init__(self, dnet=None):
        NPCI.__init__(self)
        self.npduNetMessage = DisconnectConnectionToNetwork.messageType
        self.dctnDNET = dnet
        
    def Encode(self, npdu):
        NPCI.update(npdu, self)
        npdu.PutShort( self.dctnDNET )
    
    def Decode(self, npdu):
        NPCI.update(self, npdu)
        self.dctnDNET = npdu.GetShort()

    def DebugContents(self):
        NPCI.DebugContents(self)
        if self.dctnDNET is not None:
            print "    dctnDNET =", self.dctnDNET
            
RegisterNPDUType(DisconnectConnectionToNetwork)