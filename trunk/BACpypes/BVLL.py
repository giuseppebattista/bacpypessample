
import sys

from Exceptions import *

from PDU import *
from Task import OneShotTask, RecurringTask

from CommunicationsCore import Client, Server, UDPDirector, Bind

# some debuging
_debug = ('--debugBVLL' in sys.argv)
_debugUDPMultiplexer = ('--debugUDPMultiplexer' in sys.argv)

# a dictionary of message type values and classes
BVLPDUTypes = {}

def RegisterBVLPDUType(klass):
    BVLPDUTypes[klass.messageType] = klass

#
#   BVLCI
#

class BVLCI(PCI):
    result                              = 0x00
    writeBroadcastDistributionTable     = 0x01
    readBroadcastDistributionTable      = 0x02
    readBroadcastDistributionTableAck   = 0x03
    forwardedNPDU                       = 0x04
    registerForeignDevice               = 0x05
    readForeignDeviceTable              = 0x06
    readForeignDeviceTableAck           = 0x07
    deleteForeignDeviceTableEntry       = 0x08
    distributeBroadcastToNetwork        = 0x09
    originalUnicastNPDU                 = 0x0A
    originalBroadcastNPDU               = 0x0B

    def __init__(self, *args):
        PCI.__init__(self)
        self.bvlciType = 0x81
        self.bvlciFunction = None
        self.bvlciLength = None

    def update(self, bvlci):
        PCI.update(self, bvlci)
        self.bvlciType = bvlci.bvlciType
        self.bvlciFunction = bvlci.bvlciFunction
        self.bvlciLength = bvlci.bvlciLength
        
    def Encode(self, pdu):
        """Encode the contents of the BVLCI into the PDU."""
        if _debug:
            print "BVLCI.Encode", pdu

        # copy the basics
        PCI.update(pdu, self)
        
        pdu.Put( self.bvlciType )               # 0x81
        pdu.Put( self.bvlciFunction )
        
        if (self.bvlciLength != len(self.pduData) + 4):
            raise EncodingError, "invalid BVLCI length"
            
        pdu.PutShort( self.bvlciLength )

    def Decode(self, pdu):
        """Decode the contents of the PDU into the BVLCI."""
        if _debug:
            print "BVLCI.Decode", pdu

        # copy the basics
        PCI.update(self, pdu)
        
        self.bvlciType = pdu.Get()
        if self.bvlciType != 0x81:
            raise DecodingError, "invalid BVLCI type"
            
        self.bvlciFunction = pdu.Get()
        self.bvlciLength = pdu.GetShort()
        
        if (self.bvlciLength != len(pdu.pduData) + 4):
            raise DecodingError, "invalid BVLCI length"

    def DebugContents(self):
        PCI.DebugContents(self)
        if self.bvlciType is not None:
            print "    bvlciType =", "0x%02X" % (self.bvlciType,)
        if self.bvlciFunction is not None:
            print "    bvlciFunction =", self.bvlciFunction
        if self.bvlciLength is not None:
            print "    bvlciLength =", self.bvlciLength

#
#   BVLPDU
#

class BVLPDU(BVLCI, PDUData):

    def __init__(self, *args):
        BVLCI.__init__(self)
        PDUData.__init__(self, *args)

    def Encode(self, pdu):
        BVLCI.Encode(self, pdu)
        pdu.PutData(self.pduData)

    def Decode(self, pdu):
        BVLCI.Decode(self, pdu)
        self.pduData = pdu.GetData(len(pdu.pduData))

    def DebugContents(self):
        BVLCI.DebugContents(self)
        PDUData.DebugContents(self)

#------------------------------

#
#   Result
#

class Result(BVLCI):
    messageType = BVLCI.result
    
    def __init__(self, code=None):
        BVLCI.__init__(self)
        self.bvlciFunction = BVLCI.result
        self.bvlciLength = 6
        self.bvlciResultCode = code
        
    def Encode(self, bvlpdu):
        BVLCI.update(bvlpdu, self)
        bvlpdu.PutShort( self.bvlciResultCode )
    
    def Decode(self, bvlpdu):
        BVLCI.update(self, bvlpdu)
        self.bvlciResultCode = bvlpdu.GetShort()

    def DebugContents(self):
        BVLCI.DebugContents(self)
        if self.bvlciResultCode is not None:
            print "    bvlciResultCode =", self.bvlciResultCode

RegisterBVLPDUType(Result)

#
#   WriteBroadcastDistributionTable
#

class WriteBroadcastDistributionTable(BVLCI):
    messageType = BVLCI.writeBroadcastDistributionTable

    def __init__(self, bdt=[]):
        BVLCI.__init__(self)
        self.bvlciFunction = BVLCI.writeBroadcastDistributionTable
        self.bvlciLength = 4 + 10 * len(bdt)
        self.bvlciBDT = bdt
        
    def Encode(self, bvlpdu):
        BVLCI.update(bvlpdu, self)
        for bdte in self.bvlciBDT:
            bvlpdu.PutData( bdte.addrAddr )
            bvlpdu.PutData( bdte.addrMask )
        
    def Decode(self, bvlpdu):
        BVLCI.update(self, bvlpdu)
        self.bvlciBDT = []
        while bvlpdu.pduData:
            bdte = Address(IPAddrUnpack(bvlpdu.GetData(6)))
            bdte.addrMask = bvlpdu.GetLong()
            self.bvlciBDT.append(bdte)
        
    def DebugContents(self):
        BVLCI.DebugContents(self)
        if self.bvlciBDT is not None:
            print "    bvlciBDT =", self.bvlciBDT

RegisterBVLPDUType(WriteBroadcastDistributionTable)

#
#   ReadBroadcastDistributionTable
#

class ReadBroadcastDistributionTable(BVLCI):
    messageType = BVLCI.readBroadcastDistributionTable

    def __init__(self):
        BVLCI.__init__(self)
        self.bvlciFunction = BVLCI.readBroadcastDistributionTable
        self.bvlciLength = 4
        
    def Encode(self, bvlpdu):
        BVLCI.update(bvlpdu, self)
    
    def Decode(self, bvlpdu):
        BVLCI.update(self, bvlpdu)

RegisterBVLPDUType(ReadBroadcastDistributionTable)

#
#   ReadBroadcastDistributionTableAck
#

class WriteBroadcastDistributionTable(BVLCI):
    messageType = BVLCI.writeBroadcastDistributionTable

    def __init__(self, bdt=[]):
        BVLCI.__init__(self)
        self.bvlciFunction = BVLCI.writeBroadcastDistributionTable
        self.bvlciLength = 4 + 10 * len(bdt)
        self.bvlciBDT = bdt
        
    def Encode(self, bvlpdu):
        # make sure the length is correct
        self.bvlciLength = 4 + 10 * len(self.bvlciBDT)
        
        BVLCI.update(bvlpdu, self)
        
        # encode the table
        for bdte in self.bvlciBDT:
            bvlpdu.PutData( bdte.addrAddr )
            bvlpdu.PutLong( bdte.addrMask )
        
    def Decode(self, bvlpdu):
        BVLCI.update(self, bvlpdu)
        
        # decode the table
        self.bvlciBDT = []
        while bvlpdu.pduData:
            bdte = Address(IPAddrUnpack(bvlpdu.GetData(6)))
            bdte.addrMask = bvlpdu.GetLong()
            self.bvlciBDT.append(bdte)
        
    def DebugContents(self):
        BVLCI.DebugContents(self)
        if self.bvlciBDT is not None:
            print "    bvlciBDT =", self.bvlciBDT

RegisterBVLPDUType(WriteBroadcastDistributionTable)

#
#   ForwardedNPDU
#

class ForwardedNPDU(BVLPDU):
    messageType = BVLCI.forwardedNPDU

    def __init__(self, addr=None, *args):
        BVLPDU.__init__(self, *args)
        self.bvlciFunction = BVLCI.forwardedNPDU
        self.bvlciLength = 10 + len(self.pduData)
        self.bvlciAddress = addr
        
    def Encode(self, bvlpdu):
        # make sure the length is correct
        self.bvlciLength = 10 + len(self.pduData)
        
        BVLCI.update(bvlpdu, self)
        
        # encode the address
        bvlpdu.PutData( self.bvlciAddress.addrAddr )
        
        # encode the rest of the data
        bvlpdu.PutData( self.pduData )
        
    def Decode(self, bvlpdu):
        BVLCI.update(self, bvlpdu)
        
        # get the address
        self.bvlciAddress = Address(IPAddrUnpack(bvlpdu.GetData(6)))
        
        # get the rest of the data
        self.pduData = bvlpdu.GetData(len(bvlpdu.pduData))

    def DebugContents(self):
        BVLCI.DebugContents(self)
        if self.bvlciAddress is not None:
            print "    bvlciAddress =", self.bvlciAddress
        PDUData.DebugContents(self)

RegisterBVLPDUType(ForwardedNPDU)

#
#   Foreign Device Table Entry
#

class FDTEntry:

    def __init__(self):
        self.fdAddress = None
        self.fdTTL = None
        self.fdRemain = None

#
#   RegisterForeignDevice
#

class RegisterForeignDevice(BVLCI):
    messageType = BVLCI.registerForeignDevice

    def __init__(self, ttl=None):
        BVLCI.__init__(self)
        self.bvlciFunction = BVLCI.registerForeignDevice
        self.bvlciLength = 6
        self.bvlciTimeToLive = ttl
        
    def Encode(self, bvlpdu):
        BVLCI.update(bvlpdu, self)
        bvlpdu.PutShort( self.bvlciTimeToLive )
    
    def Decode(self, bvlpdu):
        BVLCI.update(self, bvlpdu)
        self.bvlciTimeToLive = bvlpdu.GetShort()

    def DebugContents(self):
        BVLCI.DebugContents(self)
        if self.bvlciTimeToLive is not None:
            print "    bvlciTimeToLive =", self.bvlciTimeToLive

RegisterBVLPDUType(RegisterForeignDevice)

#
#   ReadForeignDeviceTable
#

class ReadForeignDeviceTable(BVLCI):
    messageType = BVLCI.readForeignDeviceTable

    def __init__(self, ttl=None):
        BVLCI.__init__(self)
        self.bvlciFunction = BVLCI.readForeignDeviceTable
        self.bvlciLength = 4
        
    def Encode(self, bvlpdu):
        BVLCI.update(bvlpdu, self)
    
    def Decode(self, bvlpdu):
        BVLCI.update(self, bvlpdu)

RegisterBVLPDUType(ReadForeignDeviceTable)

#
#   ReadForeignDeviceTableAck
#

class ReadForeignDeviceTableAck(BVLCI):
    messageType = BVLCI.readForeignDeviceTableAck

    def __init__(self, fdt=[]):
        BVLCI.__init__(self)
        self.bvlciFunction = BVLCI.readForeignDeviceTableAck
        self.bvlciLength = 4 + 10 * len(fdt)
        self.bvlciFDT = fdt
        
    def Encode(self, bvlpdu):
        BVLCI.update(bvlpdu, self)
        for fdte in self.bvlciFDT:
            bvlpdu.PutData( fdte.fdAddress.addrAddr )
            bvlpdu.PutShort( fdte.fdTTL )
            bvlpdu.PutShort( fdte.fdRemain )
        
    def Decode(self, bvlpdu):
        BVLCI.update(self, bvlpdu)
        self.bvlciFDT = []
        while bvlpdu.pduData:
            fdte = FDTEntry()
            fdte.fdAddress = Address(IPAddrUnpack(bvlpdu.GetData(6)))
            fdte.fdTTL = bvlpdu.GetShort()
            fdte.fdRemain = bvlpdu.GetShort()
            self.bvlciFDT.append(fdte)
        
    def DebugContents(self):
        BVLCI.DebugContents(self)
        if self.bvlciFDT is not None:
            print "    bvlciFDT =", self.bvlciFDT

RegisterBVLPDUType(ReadForeignDeviceTableAck)

#
#   DeleteForeignDeviceTableEntry
#

class DeleteForeignDeviceTableEntry(BVLCI):
    messageType = BVLCI.deleteForeignDeviceTableEntry

    def __init__(self, addr=None):
        BVLCI.__init__(self)
        self.bvlciFunction = BVLCI.deleteForeignDeviceTableEntry
        self.bvlciLength = 10
        self.bvlciAddress = addr
        
    def Encode(self, bvlpdu):
        BVLCI.update(bvlpdu, self)
        bvlpdu.PutData( self.bvlciAddress.addrAddr )
    
    def Decode(self, bvlpdu):
        BVLCI.update(self, bvlpdu)
        self.bvlciAddress = Address(IPAddrUnpack(bvlpdu.GetData(6)))

    def DebugContents(self):
        BVLCI.DebugContents(self)
        if self.bvlciAddress is not None:
            print "    bvlciAddress =", self.bvlciAddress

RegisterBVLPDUType(DeleteForeignDeviceTableEntry)

#
#   DistributeBroadcastToNetwork
#

class DistributeBroadcastToNetwork(BVLPDU):
    messageType = BVLCI.distributeBroadcastToNetwork

    def __init__(self, *args):
        BVLPDU.__init__(self, *args)
        self.bvlciFunction = BVLCI.distributeBroadcastToNetwork
        self.bvlciLength = 4 + len(self.pduData)
        
    def Encode(self, bvlpdu):
        self.bvlciLength = 4 + len(self.pduData)
        BVLCI.update(bvlpdu, self)
        bvlpdu.PutData( self.pduData )
        
    def Decode(self, bvlpdu):
        BVLCI.update(self, bvlpdu)
        self.pduData = bvlpdu.GetData(len(bvlpdu.pduData))

RegisterBVLPDUType(DistributeBroadcastToNetwork)

#
#   OriginalUnicastNPDU
#

class OriginalUnicastNPDU(BVLPDU):
    messageType = BVLCI.originalUnicastNPDU

    def __init__(self, *args):
        BVLPDU.__init__(self, *args)
        self.bvlciFunction = BVLCI.originalUnicastNPDU
        self.bvlciLength = 4 + len(self.pduData)
        
    def Encode(self, bvlpdu):
        self.bvlciLength = 4 + len(self.pduData)
        BVLCI.update(bvlpdu, self)
        bvlpdu.PutData( self.pduData )
        
    def Decode(self, bvlpdu):
        BVLCI.update(self, bvlpdu)
        self.pduData = bvlpdu.GetData(len(bvlpdu.pduData))

RegisterBVLPDUType(OriginalUnicastNPDU)

#
#   OriginalBroadcastNPDU
#

class OriginalBroadcastNPDU(BVLPDU):
    messageType = BVLCI.originalBroadcastNPDU

    def __init__(self, *args):
        BVLPDU.__init__(self, *args)
        self.bvlciFunction = BVLCI.originalBroadcastNPDU
        self.bvlciLength = 4 + len(self.pduData)
        
    def Encode(self, bvlpdu):
        self.bvlciLength = 4 + len(self.pduData)
        BVLCI.update(bvlpdu, self)
        bvlpdu.PutData( self.pduData )
        
    def Decode(self, bvlpdu):
        BVLCI.update(self, bvlpdu)
        self.pduData = bvlpdu.GetData(len(bvlpdu.pduData))

RegisterBVLPDUType(OriginalBroadcastNPDU)

#----------

#
#   _Multiplex Client and Server
#

class _MultiplexClient(Client):

    def __init__(self, mux):
        Client.__init__(self)
        self.multiplexer = mux

    def Confirmation(self, pdu):
        self.multiplexer.Confirmation(self, pdu)
        
class _MultiplexServer(Server):

    def __init__(self, mux):
        Server.__init__(self)
        self.multiplexer = mux

    def Indication(self, pdu):
        self.multiplexer.Indication(self, pdu)
        
#
#   UDPMultiplexer
#

class UDPMultiplexer:

    def __init__(self, addr=None):
        # check for some options
        specialBroadcast = False
        if addr is None:
            self.address = Address()
            self.addrTuple = ('', 47808)
            self.addrBroadcastTuple = ('255.255.255.255', 47808)
        else:
            # allow the address to be cast
            if isinstance(addr, Address):
                self.address = addr
            else:
                self.address = Address(addr)
            
            # check for a special broadcast address
            self.addrTuple = self.address.addrTuple
            self.addrBroadcastTuple = self.address.addrBroadcastTuple
            if (self.addrTuple == self.addrBroadcastTuple):
                self.addrBroadcastTuple = ('255.255.255.255', 47808)
            else:
                specialBroadcast = True
            
        # create and bind the direct address
        self.direct = _MultiplexClient(self)
        self.directPort = UDPDirector(self.addrTuple)
        Bind(self.direct, self.directPort)
        
        # create and bind the broadcast address
        if specialBroadcast:
            self.broadcast = _MultiplexClient(self)
            self.broadcastPort = UDPDirector(self.addrBroadcastTuple)
            Bind(self.direct, self.broadcastPort)
        else:
            self.broadcast = None
        
        # create and bind the Annex H and J servers
        self.annexH = _MultiplexServer(self)
        self.annexJ = _MultiplexServer(self)
        
    def Indication(self, server, pdu):
        if _debugUDPMultiplexer:
            print "UDPMultiplexer.Indication"
            print "    - server:", server
            print "    - pdu:", pdu

        # check for a broadcast message
        if pdu.pduDestination.addrType == Address.localBroadcastAddr:
            dest = self.addrBroadcastTuple
        else:
            dest = pdu.pduDestination.addrTuple
        
        self.directPort.Indication(PDU(pdu, destination=dest))
        
    def Confirmation(self, client, pdu):
        if _debugUDPMultiplexer:
            print "UDPMultiplexer.Confirmation"
            print "    - client:", client
            print "    - pdu:", pdu

        # if this came from ourselves, dump it
        if pdu.pduSource == self.addrTuple:
            if _debugUDPMultiplexer:
                print "    - from us!"
            return
            
        # match the destination in case the stack needs it
        if client is self.direct:
            dest = self.address
        elif client is self.broadcast:
            dest = LocalBroadcast()
        else:
            raise RuntimeError, "confirmation mismatch"
            
        # check for the message type
        if not pdu.pduData:
            raise RuntimeError, "data expected"
            
        if ord(pdu.pduData[0]) == 0x01:
            if self.annexH.serverPeer:
                self.annexH.Response(PDU(pdu, source=Address(pdu.pduSource), destination=dest))
        elif ord(pdu.pduData[0]) == 0x81:
            if self.annexJ.serverPeer:
                self.annexJ.Response(PDU(pdu, source=Address(pdu.pduSource), destination=dest))
        else:
            if _debug:
                print "unsupported message"
        
#
#   AnnexJCodec
#

class AnnexJCodec(Client, Server):

    def __init__(self, cid=None, sid=None):
        Client.__init__(self, cid)
        Server.__init__(self, sid)
        
    def Indication(self, rpdu):
        if _debug:
            print "AnnexJCodec.Indication"
        
        # encode it as a generic BVLL PDU
        bvlpdu = BVLPDU()
        rpdu.Encode(bvlpdu)
        
        # encode it as a PDU
        pdu = PDU()
        bvlpdu.Encode(pdu)
        
        # send it downstream
        self.Request(pdu)

    def Confirmation(self, pdu):
        if _debug:
            print "AnnexJCodec.Confirmation"
        
        # interpret as a BVLL PDU
        bvlpdu = BVLPDU()
        bvlpdu.Decode(pdu)
        
        # get the class related to the function
        rpdu = BVLPDUTypes[bvlpdu.bvlciFunction]()
        rpdu.Decode(bvlpdu)
        
        # send it upstream
        self.Response(rpdu)
        
#
#   BTR
#

class BTR(Client, Server):

    def __init__(self, cid=None, sid=None):
        """An Annex-H BACnet Tunneling Router node."""
        Client.__init__(self, cid)
        Server.__init__(self, sid)
        
        # initialize a dicitonary of peers
        self.peers = {}
        
    def Indication(self, pdu):
        if _debug:
            print "BTR.Indication"
            pdu.DebugContents()
        
        # check for local stations
        if pdu.pduDestination.addrType == Address.localStationAddr:
            # make sure it is going to a peer
            if not self.peers.has_key(pdu.pduDestination):
                ### log this
                return
                
            # send it downstream
            self.Request(pdu)
            
        # check for broadcasts
        elif pdu.pduDestination.addrType == Address.localBroadcastAddr:
            # loop through the peers
            for peerAddr in self.peers.keys():
                xpdu = PDU(pdu.pduData, destination=peerAddr)
                
                # send it downstream
                self.Request(xpdu)
                
        else:
            raise RuntimeError, "invalid destination address type (2)"
        
    def Confirmation(self, pdu):
        if _debug:
            print "BTR.Confirmation"
            pdu.DebugContents()
        
        # make sure it came from a peer
        if not self.peers.has_key(pdu.pduSource):
            ### log this
            return
        
        # send it upstream
        self.Response(rpdu)
        
    def AddPeer(self, peerAddr, networks=None):
        """Add a peer and optionally provide a list of the reachable networks."""
        # see if this is already a peer
        if self.peers.has_key(peerAddr):
            # add the (new?) reachable networks
            if not networks:
                networks = []
            else:
                self.peers[peerAddr].extend(networks)
        else:
            if not networks:
                networks = []
            
            # save the networks
            self.peers[peerAddr] = networks
        
        ### send a control message upstream that these are reachable
        
    def DeletePeer(self, peerAddr):
        """Delete a peer."""
        # get the peer networks
        networks = self.peers[peerAddr]
        
        ### send a control message upstream that these are no longer reachable
        
        # now delete the peer
        del self.peers[peerAddr]
    
#
#   BIPSimple
#

class BIPSimple(Client, Server):

    def __init__(self, cid=None, sid=None):
        """A BIP node."""
        Client.__init__(self, cid)
        Server.__init__(self, sid)
        
    def Indication(self, pdu):
        if _debug:
            print "BIPSimple.Indication"
            print "-pdu-"
            pdu.DebugContents()
        
        # check for local stations
        if pdu.pduDestination.addrType == Address.localStationAddr:
            # make an original unicast PDU
            xpdu = OriginalUnicastNPDU(pdu)
            xpdu.pduDestination = pdu.pduDestination
            if _debug:
                print "-xpdu-"
                xpdu.DebugContents()
            
            # send it downstream
            self.Request(xpdu)
            
        # check for broadcasts
        elif pdu.pduDestination.addrType == Address.localBroadcastAddr:
            # make an original broadcast PDU
            xpdu = OriginalBroadcastNPDU(pdu)
            xpdu.pduDestination = pdu.pduDestination
            if _debug:
                print "-xpdu-"
                xpdu.DebugContents()
            
            # send it downstream
            self.Request(xpdu)
            
        else:
            print
            print "BIPSimple.Indication: Invalid destination address type"
            pdu.DebugContents()
            print

    def Confirmation(self, pdu):
        if _debug:
            print "BIPSimple.Confirmation"
            print "-pdu-"
            pdu.DebugContents()
        
        if isinstance(pdu, OriginalUnicastNPDU):
            # build a vanilla PDU
            xpdu = PDU(pdu.pduData, source=pdu.pduSource, destination=pdu.pduDestination)
            if _debug:
                print "-xpdu-"
                xpdu.DebugContents()
            
            # send it upstream
            self.Response(xpdu)
            
        elif isinstance(pdu, OriginalBroadcastNPDU):
            # build a PDU with a local broadcast address
            xpdu = PDU(pdu.pduData, source=pdu.pduSource, destination=LocalBroadcast())
            if _debug:
                print "-xpdu-"
                xpdu.DebugContents()
            
            # send it upstream
            self.Response(xpdu)
            
        elif isinstance(pdu, ForwardedNPDU):
            # build a PDU with the source from the real source
            xpdu = PDU(pdu.pduData, source=pdu.bvlciAddress, destination=LocalBroadcast())
            if _debug:
                print "-xpdu-"
                xpdu.DebugContents()
            
            # send it upstream
            self.Response(xpdu)
            
        else:
            print
            print "BIPSimple.Confirmation: Invalid PDU type"
            pdu.DebugContents()
            print
        
#
#   BIPForeign
#

class BIPForeign(Client, Server, OneShotTask):

    def __init__(self, addr=None, ttl=None, cid=None, sid=None):
        """A BIP node."""
        Client.__init__(self, cid)
        Server.__init__(self, sid)
        
        # -2=unregistered, -1=not attempted or no ack, 0=OK, >0 error
        self.registrationStatus = -1
        
        # registration provided
        if addr:
            # a little error checking
            if ttl is None:
                raise RuntimeError, "BBMD address and time-to-live must both be specified"
                
            self.Register(addr, ttl)
            
    def Indication(self, pdu):
        if _debug:
            print "BIPForeign.Indication"
            pdu.DebugContents()
        
        # check the BBMD registration status, we may not be registered
        if self.registrationStatus != 0:
            ### log this
            # drop the packet
            return
            
        # check for local stations
        if pdu.pduDestination.addrType == Address.localStationAddr:
            # make an original unicast PDU
            xpdu = OriginalUnicastNPDU(pdu)
            xpdu.pduDestination = pdu.pduDestination
            
            # send it downstream
            self.Request(xpdu)
            
        # check for broadcasts
        elif pdu.pduDestination.addrType == Address.localBroadcastAddr:
            # make an original broadcast PDU
            xpdu = DistributeBroadcastToNetwork(pdu)
            xpdu.pduDestination = self.bbmdAddress
            
            # send it downstream
            self.Request(xpdu)
            
        else:
            print
            print "BIPForeign.Indication: Invalid destination address type"
            pdu.DebugContents()
            print
        
    def Confirmation(self, pdu):
        if _debug:
            print "BIPForeign.Confirmation"
            pdu.DebugContents()
        
        # check for a registration request result
        if isinstance(pdu, Result):
            # if we are unbinding, do nothing
            if self.registrationStatus == -2:
                return
                
            ### make sure we have a bind request in process
            
            # make sure the result is from the bbmd
            if pdu.pduSource != self.bbmdAddress:
                ### log this
                # drop the message
                return
                
            # save the result code as the status
            self.registrationStatus = pdu.bvlciResultCode
            
            # check for success
            if pdu.bvlciResultCode == 0:
                # schedule for a refresh
                self.InstallTask(_time() + self.bbmdTimeToLive)
            
            return
            
        # check the BBMD registration status, we may not be registered
        if self.registrationStatus != 0:
            ### log this
            # drop the packet
            return
            
        if isinstance(pdu, OriginalUnicastNPDU):
            # build a vanilla PDU
            xpdu = PDU(pdu.pduData, source=pdu.pduSource, destination=pdu.pduDestination)
            
            # send it upstream
            self.Response(xpdu)
            
        elif isinstance(pdu, ForwardedNPDU):
            # build a PDU with the source from the real source
            xpdu = PDU(pdu.pduData, source=pdu.bvlciAddress, destination=LocalBroadcast())
            
            # send it upstream
            self.Response(xpdu)
            
        else:
            print
            print "BIPForeign.Confirmation: Invalid PDU type"
            pdu.DebugContents()
            print
        
    def Register(self, addr, ttl):
        """Initiate the process of registering with a BBMD."""
        # a little error checking
        if ttl <= 0:
            raise ValueError, "time-to-live must be greater than zero"
            
        # save the BBMD address and time-to-live
        self.bbmdAddress = addr
        self.bbmdTimeToLive = ttl
        
        # install this task to run when it gets a chance
        self.InstallTask()
        
    def Unregister(self):
        """Drop the registration with a BBMD."""
        pdu = RegisterForeignDevice(0)
        pdu.pduDestination = self.bbmdAddress
        
        # send it downstream
        self.Request(pdu)
        
        # change the status to unregistered
        self.registrationStatus = -2
        
        # clear the BBMD address and time-to-live
        self.bbmdAddress = None
        self.bbmdTimeToLive = None
        
    def ProcessTask(self):
        """Called when the registration request should be sent to the BBMD."""
        pdu = RegisterForeignDevice(self.bbmdTimeToLive)
        pdu.pduDestination = self.bbmdAddress
        
        # send it downstream
        self.Request(pdu)
        
#
#   BIPBBMD
#

_debugBBMD = ('--debugBBMD' in sys.argv)
_debugOriginalUnicastNPDU = ('--debugOriginalUnicastNPDU' in sys.argv)
_debugOriginalBroadcastNPDU = ('--debugOriginalBroadcastNPDU' in sys.argv)
_debugForwardedNPDU = ('--debugForwardedNPDU' in sys.argv)

class BIPBBMD(Client, Server, RecurringTask):

    def __init__(self, addr, cid=None, sid=None):
        """A BBMD node."""
        Client.__init__(self, cid)
        Server.__init__(self, sid)
        RecurringTask.__init__(self, 1000.0)
        
        self.bbmdAddress = addr
        self.bbmdBDT = []
        self.bbmdFDT = []

    def Indication(self, pdu):
        if _debugBBMD:
            print "BIPBBMD.Indication", pdu
        
        # check for local stations
        if pdu.pduDestination.addrType == Address.localStationAddr:
            # make an original unicast PDU
            xpdu = OriginalUnicastNPDU(pdu)
            xpdu.pduDestination = pdu.pduDestination
            if _debugBBMD:
                print "    - xpdu:", xpdu
            
            # send it downstream
            self.Request(xpdu)
            
        # check for broadcasts
        elif pdu.pduDestination.addrType == Address.localBroadcastAddr:
            # make an original broadcast PDU
            xpdu = OriginalBroadcastNPDU(pdu)
            xpdu.pduDestination = pdu.pduDestination
            if _debugBBMD:
                print "    - xpdu (broadcast):", xpdu
            
            # send it downstream
            self.Request(xpdu)
            
            # make a forwarded PDU
            xpdu = ForwardedNPDU(self.bbmdAddress, pdu)
            if _debugBBMD:
                print "    - xpdu (forwarded):", xpdu
            
            # send it to the peers
            for bdte in self.bbmdBDT:
                if bdte != self.bbmdAddress:
                    xpdu.pduDestination = Address( ((bdte.addrIP|~bdte.addrMask), bdte.addrPort) )
                    if _debugBBMD:
                        print "        - sending to peer:", xpdu.pduDestination
                    self.Request(xpdu)

            # send it to the registered foreign devices
            for fdte in self.bbmdFDT:
                xpdu.pduDestination = fdte.fdAddress
                if _debugBBMD:
                    print "        - sending to foreign device:", xpdu.pduDestination
                self.Request(xpdu)
                
        else:
            print
            print "BIPBBMD.Indication: Invalid destination address type"
            pdu.DebugContents()
            print
        
    def Confirmation(self, pdu):
        if _debugBBMD:
            print "BIPBBMD.Confirmation",  pdu
        
        # check for a registration request result
        if isinstance(pdu, Result):
            # this response should go to the service access point
            if _debugBBMD:
                print "    - send to ASE"
            return
            
        if isinstance(pdu, OriginalUnicastNPDU):
            if _debugOriginalUnicastNPDU:
                print "BIPBBMD.Confirmation - OriginalUnicastNPDU"
                pdu.DebugContents()
            
            # build a vanilla PDU
            xpdu = PDU(pdu.pduData, source=pdu.pduSource, destination=pdu.pduDestination)
            if _debugOriginalUnicastNPDU:
                print "    - xpdu (upstream):", xpdu
            
            # send it upstream
            self.Response(xpdu)
            
            if _debugOriginalUnicastNPDU:
                print
                
        elif isinstance(pdu, OriginalBroadcastNPDU):
            if _debugOriginalBroadcastNPDU:
                print "BIPBBMD.Confirmation - OriginalBroadcastNPDU"
                pdu.DebugContents()
            
            # build a PDU with a local broadcast address
            xpdu = PDU(pdu.pduData, source=pdu.pduSource, destination=LocalBroadcast())
            if _debugOriginalBroadcastNPDU:
                print "    - xpdu (upstream):", xpdu
            
            # send it upstream
            self.Response(xpdu)
            
            # make a forwarded PDU
            xpdu = ForwardedNPDU(pdu.pduSource, pdu)
            if _debugOriginalBroadcastNPDU:
                print "    - xpdu (forwarded):", xpdu
            
            # send it to the peers
            for bdte in self.bbmdBDT:
                if bdte != self.bbmdAddress:
                    xpdu.pduDestination = Address( ((bdte.addrIP|~bdte.addrMask), bdte.addrPort) )
                    if _debugOriginalBroadcastNPDU:
                        print "        - sending to peer:", xpdu.pduDestination
                    self.Request(xpdu)

            # send it to the registered foreign devices
            for fdte in self.bbmdFDT:
                xpdu.pduDestination = fdte.fdAddress
                if _debugOriginalBroadcastNPDU:
                    print "        - sending to foreign device:", xpdu.pduDestination
                self.Request(xpdu)
                
            if _debugOriginalBroadcastNPDU:
                print
            
        elif isinstance(pdu, ForwardedNPDU):
            if _debugForwardedNPDU:
                print "BIPBBMD.Confirmation - ForwardedNPDU"
                pdu.DebugContents()
            
            # build a PDU with the source from the real source
            xpdu = PDU(pdu.pduData, source=pdu.bvlciAddress, destination=LocalBroadcast())
            if _debugForwardedNPDU:
                print "    - xpdu (upstream):", xpdu
            
            # send it upstream
            self.Response(xpdu)
            
            # broadcast a copy locally
            xpdu = ForwardedNPDU(pdu.bvlciAddress, pdu)
            xpdu.pduDestination = LocalBroadcast()
            if _debugForwardedNPDU:
                print "    - xpdu (local broadcast):", xpdu
                xpdu.DebugContents()
            
            # send it downstream
            self.Request(xpdu)
            
            if _debugForwardedNPDU:
                print
                
        else:
            print
            print "BIPBBMD.Confirmation: Invalid PDU type"
            pdu.DebugContents()
            print
        
    def RegisterForeignDevice(self, addr, ttl):
        """Add a foreign device to the FDT."""
        if not isinstance(addr,Address):
            raise TypeError, "addr must be an Address"

        for fdte in self.bbmdFDT:
            if addr == fdte.fdAddress:
                break
        else:
            fdte = FDTEntry()
            fdte.fdAddress = addr
            self.bbmdFDT.append( fdte )

        fdte.fdTTL = ttl
        fdte.fdRemain = ttl + 5

        # return success
        return 0

    def DeleteForeignDevice(self, addr):
        if not isinstance(addr,Address):
            raise TypeError, "addr must be an Address"

        # find it and delete it
        for i in range(len(self.bbmdFDT)-1, -1, -1):
            if addr == self.bbmdFDT[i].fdAddress:
                del self.bbmdFDT[i]

        # return success
        return 0

    def ProcessTask(self):
        # look for foreign device registrations that have expired
        for i in range(len(self.bbmdFDT)-1, -1, -1):
            fdte = self.bbmdFDT[i]
            fdte.fdRemain -= 1

            # delete it if it expired
            if fdte.fdRemain <= 0:
                if _debug:
                    print "(foreign device expired", fdte.fdAddress, ")"
                del self.bbmdFDT[i]

    def AddPeer(self, addr):
        if not isinstance(addr, Address):
            raise TypeError, "addr must be an Address"

        # see if it's already there
        for bdte in self.bbmdBDT:
            if addr == bdte:
                break
        else:
            self.bbmdBDT.append(addr)

    def DeletePeer(self, addr):
        if isinstance(addr, LocalStation):
            pass
        elif isinstance(arg,types.StringType):
            addr = LocalStation( addr )
        else:
            raise TypeError, "addr must be a string or a LocalStation"

        # look for the peer address
        for i in range(len(self.bbmdBDT)-1, -1, -1):
            if addr == self.bbmdBDT[i]:
                del self.bbmdBDT[i]
                break
        else:
            pass
