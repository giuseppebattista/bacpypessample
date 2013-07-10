#!/usr/bin/python

"""
BACnet Virtual Link Layer Module
"""

from errors import EncodingError, DecodingError
from debugging import ModuleLogger, DebugContents, Logging

from pdu import *

# some debuging
_debug = 0
_log = ModuleLogger(globals())

# a dictionary of message type values and classes
bvl_pdu_types = {}

def register_bvlpdu_type(klass):
    bvl_pdu_types[klass.messageType] = klass

#
#   BVLCI
#

class BVLCI(PCI, DebugContents, Logging):

    _debug_contents = ('bvlciType', 'bvlciFunction', 'bvlciLength')
    
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
        
    def encode(self, pdu):
        """encode the contents of the BVLCI into the PDU."""
        if _debug: BVLCI._debug("encode %r", pdu)

        # copy the basics
        PCI.update(pdu, self)
        
        pdu.put( self.bvlciType )               # 0x81
        pdu.put( self.bvlciFunction )
        
        if (self.bvlciLength != len(self.pduData) + 4):
            raise EncodingError, "invalid BVLCI length"
            
        pdu.put_short( self.bvlciLength )

    def decode(self, pdu):
        """decode the contents of the PDU into the BVLCI."""
        if _debug: BVLCI._debug("decode %r", pdu)

        # copy the basics
        PCI.update(self, pdu)
        
        self.bvlciType = pdu.get()
        if self.bvlciType != 0x81:
            raise DecodingError, "invalid BVLCI type"
            
        self.bvlciFunction = pdu.get()
        self.bvlciLength = pdu.get_short()
        
        if (self.bvlciLength != len(pdu.pduData) + 4):
            raise DecodingError, "invalid BVLCI length"

#
#   BVLPDU
#

class BVLPDU(BVLCI, PDUData):

    def __init__(self, *args):
        BVLCI.__init__(self)
        PDUData.__init__(self, *args)

    def encode(self, pdu):
        BVLCI.encode(self, pdu)
        pdu.put_data(self.pduData)

    def decode(self, pdu):
        BVLCI.decode(self, pdu)
        self.pduData = pdu.get_data(len(pdu.pduData))

#------------------------------

#
#   Result
#

class Result(BVLCI):

    _debug_contents = ('bvlciResultCode',)
    
    messageType = BVLCI.result
    
    def __init__(self, code=None):
        BVLCI.__init__(self)
        self.bvlciFunction = BVLCI.result
        self.bvlciLength = 6
        self.bvlciResultCode = code
        
    def encode(self, bvlpdu):
        BVLCI.update(bvlpdu, self)
        bvlpdu.put_short( self.bvlciResultCode )
    
    def decode(self, bvlpdu):
        BVLCI.update(self, bvlpdu)
        self.bvlciResultCode = bvlpdu.get_short()

register_bvlpdu_type(Result)

#
#   WriteBroadcastDistributionTable
#

class WriteBroadcastDistributionTable(BVLCI):

    _debug_contents = ('bvlciBDT',)
    
    messageType = BVLCI.writeBroadcastDistributionTable

    def __init__(self, bdt=[]):
        BVLCI.__init__(self)
        self.bvlciFunction = BVLCI.writeBroadcastDistributionTable
        self.bvlciLength = 4 + 10 * len(bdt)
        self.bvlciBDT = bdt
        
    def encode(self, bvlpdu):
        BVLCI.update(bvlpdu, self)
        for bdte in self.bvlciBDT:
            bvlpdu.put_data( bdte.addrAddr )
            bvlpdu.put_data( bdte.addrMask )
        
    def decode(self, bvlpdu):
        BVLCI.update(self, bvlpdu)
        self.bvlciBDT = []
        while bvlpdu.pduData:
            bdte = Address(unpack_ip_addr(bvlpdu.get_data(6)))
            bdte.addrMask = bvlpdu.get_long()
            self.bvlciBDT.append(bdte)
        
register_bvlpdu_type(WriteBroadcastDistributionTable)

#
#   ReadBroadcastDistributionTable
#

class ReadBroadcastDistributionTable(BVLCI):
    messageType = BVLCI.readBroadcastDistributionTable

    def __init__(self):
        BVLCI.__init__(self)
        self.bvlciFunction = BVLCI.readBroadcastDistributionTable
        self.bvlciLength = 4
        
    def encode(self, bvlpdu):
        BVLCI.update(bvlpdu, self)
    
    def decode(self, bvlpdu):
        BVLCI.update(self, bvlpdu)

register_bvlpdu_type(ReadBroadcastDistributionTable)

#
#   ReadBroadcastDistributionTableAck
#

class ReadBroadcastDistributionTableAck(BVLCI):

    _debug_contents = ('bvlciBDT',)
    
    messageType = BVLCI.readBroadcastDistributionTableAck

    def __init__(self, bdt=[]):
        BVLCI.__init__(self)
        self.bvlciFunction = BVLCI.readBroadcastDistributionTableAck
        self.bvlciLength = 4 + 10 * len(bdt)
        self.bvlciBDT = bdt
        
    def encode(self, bvlpdu):
        # make sure the length is correct
        self.bvlciLength = 4 + 10 * len(self.bvlciBDT)
        
        BVLCI.update(bvlpdu, self)
        
        # encode the table
        for bdte in self.bvlciBDT:
            bvlpdu.put_data( bdte.addrAddr )
            bvlpdu.put_long( bdte.addrMask )
        
    def decode(self, bvlpdu):
        BVLCI.update(self, bvlpdu)
        
        # decode the table
        self.bvlciBDT = []
        while bvlpdu.pduData:
            bdte = Address(unpack_ip_addr(bvlpdu.get_data(6)))
            bdte.addrMask = bvlpdu.get_long()
            self.bvlciBDT.append(bdte)
        
register_bvlpdu_type(ReadBroadcastDistributionTableAck)

#
#   ForwardedNPDU
#

class ForwardedNPDU(BVLPDU):

    _debug_contents = ('bvlciAddress',)
    
    messageType = BVLCI.forwardedNPDU

    def __init__(self, addr=None, *args):
        BVLPDU.__init__(self, *args)
        self.bvlciFunction = BVLCI.forwardedNPDU
        self.bvlciLength = 10 + len(self.pduData)
        self.bvlciAddress = addr
        
    def encode(self, bvlpdu):
        # make sure the length is correct
        self.bvlciLength = 10 + len(self.pduData)
        
        BVLCI.update(bvlpdu, self)
        
        # encode the address
        bvlpdu.put_data( self.bvlciAddress.addrAddr )
        
        # encode the rest of the data
        bvlpdu.put_data( self.pduData )
        
    def decode(self, bvlpdu):
        BVLCI.update(self, bvlpdu)
        
        # get the address
        self.bvlciAddress = Address(unpack_ip_addr(bvlpdu.get_data(6)))
        
        # get the rest of the data
        self.pduData = bvlpdu.get_data(len(bvlpdu.pduData))

register_bvlpdu_type(ForwardedNPDU)

#
#   Foreign Device Table Entry
#

class FDTEntry(DebugContents):

    _debug_contents = ('fdAddress', 'fdTTL', 'fdRemain')
    
    def __init__(self):
        self.fdAddress = None
        self.fdTTL = None
        self.fdRemain = None

#
#   RegisterForeignDevice
#

class RegisterForeignDevice(BVLCI):

    _debug_contents = ('bvlciTimeToLive',)
    
    messageType = BVLCI.registerForeignDevice

    def __init__(self, ttl=None):
        BVLCI.__init__(self)
        self.bvlciFunction = BVLCI.registerForeignDevice
        self.bvlciLength = 6
        self.bvlciTimeToLive = ttl
        
    def encode(self, bvlpdu):
        BVLCI.update(bvlpdu, self)
        bvlpdu.put_short( self.bvlciTimeToLive )
    
    def decode(self, bvlpdu):
        BVLCI.update(self, bvlpdu)
        self.bvlciTimeToLive = bvlpdu.get_short()

register_bvlpdu_type(RegisterForeignDevice)

#
#   ReadForeignDeviceTable
#

class ReadForeignDeviceTable(BVLCI):

    messageType = BVLCI.readForeignDeviceTable

    def __init__(self, ttl=None):
        BVLCI.__init__(self)
        self.bvlciFunction = BVLCI.readForeignDeviceTable
        self.bvlciLength = 4
        
    def encode(self, bvlpdu):
        BVLCI.update(bvlpdu, self)
    
    def decode(self, bvlpdu):
        BVLCI.update(self, bvlpdu)

register_bvlpdu_type(ReadForeignDeviceTable)

#
#   ReadForeignDeviceTableAck
#

class ReadForeignDeviceTableAck(BVLCI):

    _debug_contents = ('bvlciFDT',)
    
    messageType = BVLCI.readForeignDeviceTableAck

    def __init__(self, fdt=[]):
        BVLCI.__init__(self)
        self.bvlciFunction = BVLCI.readForeignDeviceTableAck
        self.bvlciLength = 4 + 10 * len(fdt)
        self.bvlciFDT = fdt
        
    def encode(self, bvlpdu):
        BVLCI.update(bvlpdu, self)
        for fdte in self.bvlciFDT:
            bvlpdu.put_data( fdte.fdAddress.addrAddr )
            bvlpdu.put_short( fdte.fdTTL )
            bvlpdu.put_short( fdte.fdRemain )
        
    def decode(self, bvlpdu):
        BVLCI.update(self, bvlpdu)
        self.bvlciFDT = []
        while bvlpdu.pduData:
            fdte = FDTEntry()
            fdte.fdAddress = Address(unpack_ip_addr(bvlpdu.get_data(6)))
            fdte.fdTTL = bvlpdu.get_short()
            fdte.fdRemain = bvlpdu.get_short()
            self.bvlciFDT.append(fdte)
        
register_bvlpdu_type(ReadForeignDeviceTableAck)

#
#   DeleteForeignDeviceTableEntry
#

class DeleteForeignDeviceTableEntry(BVLCI):

    _debug_contents = ('bvlciAddress',)
    
    messageType = BVLCI.deleteForeignDeviceTableEntry

    def __init__(self, addr=None):
        BVLCI.__init__(self)
        self.bvlciFunction = BVLCI.deleteForeignDeviceTableEntry
        self.bvlciLength = 10
        self.bvlciAddress = addr
        
    def encode(self, bvlpdu):
        BVLCI.update(bvlpdu, self)
        bvlpdu.put_data( self.bvlciAddress.addrAddr )
    
    def decode(self, bvlpdu):
        BVLCI.update(self, bvlpdu)
        self.bvlciAddress = Address(unpack_ip_addr(bvlpdu.get_data(6)))

register_bvlpdu_type(DeleteForeignDeviceTableEntry)

#
#   DistributeBroadcastToNetwork
#

class DistributeBroadcastToNetwork(BVLPDU):

    messageType = BVLCI.distributeBroadcastToNetwork

    def __init__(self, *args):
        BVLPDU.__init__(self, *args)
        self.bvlciFunction = BVLCI.distributeBroadcastToNetwork
        self.bvlciLength = 4 + len(self.pduData)
        
    def encode(self, bvlpdu):
        self.bvlciLength = 4 + len(self.pduData)
        BVLCI.update(bvlpdu, self)
        bvlpdu.put_data( self.pduData )
        
    def decode(self, bvlpdu):
        BVLCI.update(self, bvlpdu)
        self.pduData = bvlpdu.get_data(len(bvlpdu.pduData))

register_bvlpdu_type(DistributeBroadcastToNetwork)

#
#   OriginalUnicastNPDU
#

class OriginalUnicastNPDU(BVLPDU):
    messageType = BVLCI.originalUnicastNPDU

    def __init__(self, *args):
        BVLPDU.__init__(self, *args)
        self.bvlciFunction = BVLCI.originalUnicastNPDU
        self.bvlciLength = 4 + len(self.pduData)
        
    def encode(self, bvlpdu):
        self.bvlciLength = 4 + len(self.pduData)
        BVLCI.update(bvlpdu, self)
        bvlpdu.put_data( self.pduData )
        
    def decode(self, bvlpdu):
        BVLCI.update(self, bvlpdu)
        self.pduData = bvlpdu.get_data(len(bvlpdu.pduData))

register_bvlpdu_type(OriginalUnicastNPDU)

#
#   OriginalBroadcastNPDU
#

class OriginalBroadcastNPDU(BVLPDU):
    messageType = BVLCI.originalBroadcastNPDU

    def __init__(self, *args):
        BVLPDU.__init__(self, *args)
        self.bvlciFunction = BVLCI.originalBroadcastNPDU
        self.bvlciLength = 4 + len(self.pduData)
        
    def encode(self, bvlpdu):
        self.bvlciLength = 4 + len(self.pduData)
        BVLCI.update(bvlpdu, self)
        bvlpdu.put_data( self.pduData )
        
    def decode(self, bvlpdu):
        BVLCI.update(self, bvlpdu)
        self.pduData = bvlpdu.get_data(len(bvlpdu.pduData))

register_bvlpdu_type(OriginalBroadcastNPDU)

