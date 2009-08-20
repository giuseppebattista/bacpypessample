
import sys
import logging

from Exceptions import *
from Debugging import DebugContents, Logging

from PDU import *
from PrimativeData import *
from ConstructedData import *
from BaseTypes import *

# some debuging
_log = logging.getLogger(__name__)

# a dictionary of message type values and classes
APDUTypes = {}

def RegisterAPDUType(klass):
    APDUTypes[klass.pduType] = klass

# a dictionary of confirmed request choices and classes
ConfirmedRequestTypes = {}

def RegisterConfirmedRequestType(klass):
    ConfirmedRequestTypes[klass.serviceChoice] = klass

# a dictionary of complex ack choices and classes
ComplexAckTypes = {}

def RegisterComplexAckType(klass):
    ComplexAckTypes[klass.serviceChoice] = klass

# a dictionary of unconfirmed request choices and classes
UnconfirmedRequestTypes = {}

def RegisterUnconfirmedRequestType(klass):
    UnconfirmedRequestTypes[klass.serviceChoice] = klass

# a dictionary of unconfirmed request choices and classes
ErrorTypes = {}

def RegisterErrorType(klass):
    ErrorTypes[klass.serviceChoice] = klass

#
#   MaxAPDUSegmentsEncode/MaxAPDUSegmentsDecode
#

def MaxAPDUSegmentsEncode(arg):
    if (arg > 64): return 7
    return {None:0, 0:0, 2:1, 4:2, 8:3, 16:4, 32:5, 64:6}.get(arg)

def MaxAPDUSegmentsDecode(arg):
    if (arg >= 7): return 128
    return {0:None, 1:2, 2:4, 3:8, 4:16, 5:32, 6:64}.get(arg)

#
#   MaxAPDUResponseEncode/MaxAPDUResponseDecode
#

def MaxAPDUResponseEncode(arg):
    return {50:0, 128:1, 206:2, 480:3, 1024:4, 1476:5}.get(arg)

def MaxAPDUResponseDecode(arg):
    return {0:50, 1:128, 2:206, 3:480, 4:1024, 5:1476}.get(arg)

#
#   APCI
#

class APCI(PCI, DebugContents, Logging):

    _debugContents = ('apduType', 'apduSeg', 'apduMor', 'apduSA', 'apduSrv'
        , 'apduNak', 'apduSeq', 'apduWin', 'apduMaxSegs', 'apduMaxResp'
        , 'apduService', 'apduInvokeID', 'apduAbortRejectReason'
        )
        
    def __init__(self):
        PCI.__init__(self)
        self.apduType = None
        self.apduSeg = None                 # segmented
        self.apduMor = None                 # more follows
        self.apduSA = None                  # segmented response accepted
        self.apduSrv = None                 # sent by server
        self.apduNak = None                 # negative acknowledgement
        self.apduSeq = None                 # sequence number
        self.apduWin = None                 # actual/proposed window size
        self.apduMaxSegs = None             # maximum segments accepted (decoded)
        self.apduMaxResp = None             # max response accepted (decoded)
        self.apduService = None             #
        self.apduInvokeID = None            #
        self.apduAbortRejectReason = None   #

    def update(self, apci):
        PCI.update(self, apci)
        self.apduType = apci.apduType
        self.apduSeg = apci.apduSeg
        self.apduMor = apci.apduMor
        self.apduSA = apci.apduSA
        self.apduSrv = apci.apduSrv
        self.apduNak = apci.apduNak
        self.apduSeq = apci.apduSeq
        self.apduWin = apci.apduWin
        self.apduMaxSegs = apci.apduMaxSegs
        self.apduMaxResp = apci.apduMaxResp
        self.apduService = apci.apduService
        self.apduInvokeID = apci.apduInvokeID
        self.apduAbortRejectReason = apci.apduAbortRejectReason

    def __repr__(self):
        xid = id(self)
        if (xid < 0): xid += (1L << 32)

        sname = self.__module__ + '.' + self.__class__.__name__
        
        stype = APDUTypes.get(self.apduType, None)
        if stype:
            stype = stype.__name__
        else:
            stype = '?'
            
        if self.apduInvokeID is not None:
            stype += ',' + str(self.apduInvokeID)

        return '<' + sname + '(' + stype + ') instance at 0x%08x' % xid + '>'

    def Encode(self, pdu):
        """Encode the contents of the APCI into the PDU."""
        APCI._debug("Encode %r", pdu)

        PCI.update(pdu, self)

        if (self.apduType == ConfirmedRequestPDU.pduType):
            # PDU type
            buff = self.apduType << 4
            if self.apduSeg:
                buff += 0x08
            if self.apduMor:
                buff += 0x04
            if self.apduSA:
                buff += 0x02
            pdu.Put(buff)
            pdu.Put((MaxAPDUSegmentsEncode(self.apduMaxSegs) << 4) + MaxAPDUResponseEncode(self.apduMaxResp))
            pdu.Put(self.apduInvokeID)
            if self.apduSeg:
                pdu.Put(self.apduSeq)
                pdu.Put(self.apduWin)
            pdu.Put(self.apduService)

        elif (self.apduType == UnconfirmedRequestPDU.pduType):
            pdu.Put(self.apduType << 4)
            pdu.Put(self.apduService)

        elif (self.apduType == SimpleAckPDU.pduType):
            pdu.Put(self.apduType << 4)
            pdu.Put(self.apduInvokeID)
            pdu.Put(self.apduService)

        elif (self.apduType == ComplexAckPDU.pduType):
            # PDU type
            buff = self.apduType << 4
            if self.apduSeg:
                buff += 0x08
            if self.apduMor:
                buff += 0x04
            pdu.Put(buff)
            pdu.Put(self.apduInvokeID)
            if self.apduSeg:
                pdu.Put(self.apduSeq)
                pdu.Put(self.apduWin)
            pdu.Put(self.apduService)

        elif (self.apduType == SegmentAckPDU.pduType):
            # PDU type
            buff = self.apduType << 4
            if self.apduNak:
                buff += 0x02
            if self.apduSrv:
                buff += 0x01
            pdu.Put(buff)
            pdu.Put(self.apduInvokeID)
            pdu.Put(self.apduSeq)
            pdu.Put(self.apduWin)

        elif (self.apduType == ErrorPDU.pduType):
            pdu.Put(self.apduType << 4)
            pdu.Put(self.apduInvokeID)
            pdu.Put(self.apduService)

        elif (self.apduType == RejectPDU.pduType):
            pdu.Put(self.apduType << 4)
            pdu.Put(self.apduInvokeID)
            pdu.Put(self.apduAbortRejectReason)

        elif (self.apduType == AbortPDU.pduType):
            # PDU type
            buff = self.apduType << 4
            if self.apduSrv:
                buff += 0x01
            pdu.Put(buff)
            pdu.Put(self.apduInvokeID)
            pdu.Put(self.apduAbortRejectReason)

        else:
            raise ValueError, "invalid APCI.apduType"

    def Decode(self, pdu):
        """Decode the contents of the PDU into the APCI."""
        APCI._debug("Decode %r", pdu)

        PCI.update(self, pdu)

        # decode the first octet
        buff = pdu.Get()

        # decode the APCI type
        self.apduType = (buff >> 4) & 0x0F

        if (self.apduType == ConfirmedRequestPDU.pduType):
            self.apduSeg = ((buff & 0x08) != 0)
            self.apduMor = ((buff & 0x04) != 0)
            self.apduSA  = ((buff & 0x02) != 0)
            buff = pdu.Get()
            self.apduMaxSegs = MaxAPDUSegmentsDecode( (buff >> 4) & 0x07 )
            self.apduMaxResp = MaxAPDUResponseDecode( buff & 0x0F )
            self.apduInvokeID = pdu.Get()
            if self.apduSeg:
                self.apduSeq = pdu.Get()
                self.apduWin = pdu.Get()
            self.apduService = pdu.Get()
            self.pduData = pdu.pduData

        elif (self.apduType == UnconfirmedRequestPDU.pduType):
            self.apduService = pdu.Get()
            self.pduData = pdu.pduData

        elif (self.apduType == SimpleAckPDU.pduType):
            self.apduInvokeID = pdu.Get()
            self.apduService = pdu.Get()

        elif (self.apduType == ComplexAckPDU.pduType):
            self.apduSeg = ((buff & 0x08) != 0)
            self.apduMor = ((buff & 0x04) != 0)
            self.apduInvokeID = pdu.Get()
            if self.apduSeg:
                self.apduSeq = pdu.Get()
                self.apduWin = pdu.Get()
            self.apduService = pdu.Get()
            self.pduData = pdu.pduData

        elif (self.apduType == SegmentAckPDU.pduType):
            self.apduNak = ((buff & 0x02) != 0)
            self.apduSrv = ((buff & 0x01) != 0)
            self.apduInvokeID = pdu.Get()
            self.apduSeq = pdu.Get()
            self.apduWin = pdu.Get()

        elif (self.apduType == ErrorPDU.pduType):
            self.apduInvokeID = pdu.Get()
            self.apduService = pdu.Get()
            self.pduData = pdu.pduData

        elif (self.apduType == RejectPDU.pduType):
            self.apduInvokeID = pdu.Get()
            self.apduAbortRejectReason = pdu.Get()

        elif (self.apduType == AbortPDU.pduType):
            self.apduSrv = ((buff & 0x01) != 0)
            self.apduInvokeID = pdu.Get()
            self.apduAbortRejectReason = pdu.Get()
            self.pduData = pdu.pduData

        else:
            raise DecodingError, "invalid APDU type"

#
#   APDU
#

class APDU(APCI, PDUData):

    def __init__(self, *args):
        APCI.__init__(self)
        PDUData.__init__(self, *args)

    def Encode(self, pdu):
        APCI.Encode(self, pdu)
        pdu.PutData(self.pduData)

    def Decode(self, pdu):
        APCI.Decode(self, pdu)
        self.pduData = pdu.GetData(len(pdu.pduData))

#------------------------------

#
#   _APDU
#
#   This class masks the Encode() and Decode() functions of the APDU 
#   so that derived classes use the update function to copy the contents 
#   between PDU's.  Otherwise the APCI content would be decoded twice.
#

class _APDU(APDU):

    def Encode(self, pdu):
        APCI.update(pdu, self)
        pdu.PutData(self.pduData)
    
    def Decode(self, pdu):
        APCI.update(self, pdu)
        self.pduData = pdu.GetData(len(pdu.pduData))

    def SetContext(self, context):
        self.pduDestination = context.pduSource
        self.pduExpectingReply = 0
        self.pduNetworkPriority = context.pduNetworkPriority
        self.apduService = context.apduService
        self.apduInvokeID = context.apduInvokeID
    
#
#   ConfirmedRequestPDU
#

class ConfirmedRequestPDU(_APDU):
    pduType = 0
    
    def __init__(self, choice=None):
        APDU.__init__(self)
        self.apduType = ConfirmedRequestPDU.pduType
        self.apduService = choice
        self.pduExpectingReply = 1

    def __repr__(self):
        xid = id(self)
        if (xid < 0): xid += (1L << 32)

        sname = self.__module__ + '.' + self.__class__.__name__
        stype = str(self.apduService) + ',' + str(self.apduInvokeID)

        return '<' + sname + '(' + stype + ') instance at 0x%08x' % xid + '>'

RegisterAPDUType(ConfirmedRequestPDU)

#
#   UnconfirmedRequestPDU
#

class UnconfirmedRequestPDU(_APDU):
    pduType = 1
    
    def __init__(self, choice=None):
        APDU.__init__(self)
        self.apduType = UnconfirmedRequestPDU.pduType
        self.apduService = choice

    def __repr__(self):
        xid = id(self)
        if (xid < 0): xid += (1L << 32)

        sname = self.__module__ + '.' + self.__class__.__name__
        stype = str(self.apduService)

        return '<' + sname + '(' + stype + ') instance at 0x%08x' % xid + '>'

RegisterAPDUType(UnconfirmedRequestPDU)

#
#   SimpleAckPDU
#

class SimpleAckPDU(_APDU):
    pduType = 2

    def __init__(self, choice=None, invokeID=None, context=None):
        APDU.__init__(self)
        self.apduType = SimpleAckPDU.pduType
        self.apduService = choice
        self.apduInvokeID = invokeID

        # use the context to fill in most of the fields
        if context is not None:
            self.SetContext(context)
            
    def __repr__(self):
        xid = id(self)
        if (xid < 0): xid += (1L << 32)

        sname = self.__module__ + '.' + self.__class__.__name__
        stype = str(self.apduService) + ',' + str(self.apduInvokeID)

        return '<' + sname + '(' + stype + ') instance at 0x%08x' % xid + '>'

RegisterAPDUType(SimpleAckPDU)

#
#   ComplexAckPDU
#

class ComplexAckPDU(_APDU):
    pduType = 3

    def __init__(self, choice=None, invokeID=None, context=None):
        APDU.__init__(self)
        self.apduType = ComplexAckPDU.pduType
        self.apduService = choice
        self.apduInvokeID = invokeID

        # use the context to fill in most of the fields
        if context is not None:
            self.SetContext(context)
            
    def __repr__(self):
        xid = id(self)
        if (xid < 0): xid += (1L << 32)

        sname = self.__module__ + '.' + self.__class__.__name__
        stype = str(self.apduService) + ',' + str(self.apduInvokeID)

        return '<' + sname + '(' + stype + ') instance at 0x%08x' % xid + '>'

RegisterAPDUType(ComplexAckPDU)

#
#   SegmentAckPDU
#

class SegmentAckPDU(_APDU):
    pduType = 4

    def __init__(self, nak=None, srv=None, invokeID=None, sequenceNumber=None, windowSize=None):
        APDU.__init__(self)
        if nak is None: raise ValueError, "nak is None"
        if srv is None: raise ValueError, "srv is None"
        if invokeID is None: raise ValueError, "invokeID is None"
        if sequenceNumber is None: raise ValueError, "sequenceNumber is None"
        if windowSize is None: raise ValueError, "windowSize is None"

        self.apduType = SegmentAckPDU.pduType
        self.apduNak = nak
        self.apduSrv = srv
        self.apduInvokeID = invokeID
        self.apduSeq = sequenceNumber
        self.apduWin = windowSize

    def __repr__(self):
        xid = id(self)
        if (xid < 0): xid += (1L << 32)

        sname = self.__module__ + '.' + self.__class__.__name__

        return '<' + sname + ' instance at 0x%08x' % xid + '>'

RegisterAPDUType(SegmentAckPDU)

#
#   ErrorPDU
#

class ErrorPDU(_APDU):
    pduType = 5

    def __init__(self, choice=None, invokeID=None, context=None):
        APDU.__init__(self)
        self.apduType = ErrorPDU.pduType
        self.apduService = choice
        self.apduInvokeID = invokeID

        # use the context to fill in most of the fields
        if context is not None:
            self.SetContext(context)
            
    def __repr__(self):
        xid = id(self)
        if (xid < 0): xid += (1L << 32)

        sname = self.__module__ + '.' + self.__class__.__name__
        stype = str(self.apduService) + ',' + str(self.apduInvokeID)

        return '<' + sname + '(' + stype + ') instance at 0x%08x' % xid + '>'

RegisterAPDUType(ErrorPDU)

#
#   Reject
#

class BACnetRejectReason(Enumerated):
    enumerations = \
        { 'other':0
        , 'buffer-overflow':1
        , 'inconsistent-parameters':2
        , 'invalid-parameter-datatype':3
        , 'invalid-tag':4
        , 'missing-required-parameter':5
        , 'parameter-out-of-range':6
        , 'too-many-arguments':7
        , 'undefined-enumeration':8
        , 'unrecognized-service':9
        }

ExpandEnumerations(BACnetRejectReason)

class RejectPDU(_APDU):
    pduType = 6
    
    def __init__(self, invokeID=None, reason=None, context=None):
        APDU.__init__(self)
        self.apduType = RejectPDU.pduType
        self.apduInvokeID = invokeID
        if isinstance(reason, str):
            reason = BACnetRejectReason(reason).GetLong()
        self.apduAbortRejectReason = reason

        # use the context to fill in most of the fields
        if context is not None:
            self.pduDestination = context.pduSource
            self.pduExpectingReply = 0
            self.pduNetworkPriority = context.pduNetworkPriority
            self.apduInvokeID = context.apduInvokeID
            
    def __repr__(self):
        xid = id(self)
        if (xid < 0): xid += (1L << 32)

        sname = self.__module__ + '.' + self.__class__.__name__
        try:
            reason = BACnetRejectReason._xlateTable[self.apduAbortRejectReason]
        except:
            reason = str(self.apduAbortRejectReason) + '?'

        return '<' + sname + '(%s,%s) instance at 0x%08x' % (self.apduInvokeID, reason, xid) + '>'

RegisterAPDUType(RejectPDU)

#
#   Abort
#

class BACnetAbortReason(Enumerated):
    enumerations = \
        { 'other':0
        , 'buffer-overflow':1
        , 'invalid-apdu-in-this-state':2
        , 'preepmted-by-higher-priority-task':3
        , 'segmentation-not-supported':4
        
        # 64..255 are available for vendor codes
        , 'server-timeout':64
        , 'no-response':65
        }
        
ExpandEnumerations(BACnetAbortReason)

class AbortPDU(_APDU):
    pduType = 7
    
    def __init__(self, srv=None, invokeID=None, reason=None, context=None):
        APDU.__init__(self)
        self.apduType = AbortPDU.pduType
        self.apduSrv = srv
        self.apduInvokeID = invokeID
        if isinstance(reason, str):
            reason = BACnetAbortReason(reason).GetLong()
        self.apduAbortRejectReason = reason

        # use the context to fill in most of the fields
        if context is not None:
            self.pduDestination = context.pduSource
            self.pduExpectingReply = 0
            self.pduNetworkPriority = context.pduNetworkPriority
            self.apduInvokeID = context.apduInvokeID
            
    def __str__(self):
        try:
            reason = BACnetAbortReason._xlateTable[self.apduAbortRejectReason]
        except:
            reason = str(self.apduAbortRejectReason) + '?'
        return reason

    def __repr__(self):
        xid = id(self)
        if (xid < 0): xid += (1L << 32)

        sname = self.__module__ + '.' + self.__class__.__name__
        stype = '%s,%s' % (self.apduInvokeID, self.apduAbortRejectReason)
        reason = self.__str__()

        return '<' + sname + '(%s,%s) instance at 0x%08x' % (self.apduInvokeID, reason, xid) + '>'

RegisterAPDUType(AbortPDU)

#------------------------------

#
#   APCISequence
#

class APCISequence(APCI, Sequence, Logging):

    def __init__(self, **kwargs):
        APCI.__init__(self)
        Sequence.__init__(self, **kwargs)
        self._tagList = None

    def Encode(self, apdu):
        APCISequence._debug("Encode %r", apdu)
        
        # copy the header fields
        apdu.update(self)
        
        # create a tag list
        self._tagList = TagList()
        Sequence.Encode(self, self._tagList)

        # encode the tag list
        self._tagList.Encode(apdu)

    def Decode(self, apdu):
        APCISequence._debug("Decode %r", apdu)
        
        # copy the header fields
        self.update(apdu)
        
        # create a tag list and decode the rest of the data
        self._tagList = TagList()
        self._tagList.Decode(apdu)

        # pass the taglist to the Sequence for additional decoding
        Sequence.Decode(self, self._tagList)

#
#   ConfirmedRequestSequence
#

class ConfirmedRequestSequence(APCISequence, ConfirmedRequestPDU):
    serviceChoice = None
    
    def __init__(self, **kwargs):
        APCISequence.__init__(self, **kwargs)
        ConfirmedRequestPDU.__init__(self, self.serviceChoice)

#
#   ComplexAckSequence
#

class ComplexAckSequence(APCISequence, ComplexAckPDU):
    serviceChoice = None

    def __init__(self, **kwargs):
        APCISequence.__init__(self, **kwargs)
        ComplexAckPDU.__init__(self, self.serviceChoice, kwargs.get('invokeID'), context=kwargs.get('context', None))

#
#   UnconfirmedRequestSequence
#

class UnconfirmedRequestSequence(APCISequence, UnconfirmedRequestPDU):
    serviceChoice = None

    def __init__(self, **kwargs):
        APCISequence.__init__(self, **kwargs)
        UnconfirmedRequestPDU.__init__(self, self.serviceChoice)

#
#   ErrorSequence
#

class ErrorSequence(APCISequence, ErrorPDU):
    serviceChoice = None

    def __init__(self, **kwargs):
        APCISequence.__init__(self, **kwargs)
        ErrorPDU.__init__(self, self.serviceChoice, kwargs.get('invokeID'), context=kwargs.get('context', None))

#------------------------------

class ErrorClass(Enumerated):
    enumerations = \
        { 'device':0
        , 'object':1
        , 'property':2
        , 'resources':3
        , 'security':4
        , 'services':5
        , 'vt':6
        }

class ErrorCode(Enumerated):
    enumerations = \
        { 'other':0
        , 'authentication-failed':1
        , 'character-set-not-supported':41
        , 'configuration-in-progress':2
        , 'datatype-not-supported':47
        , 'device-busy':3
        , 'duplicate-name':48
        , 'duplicate-object-id':49
        , 'dynamic-creation-not-supported':4
        , 'file-access-denied':5
        , 'incompatible-security-levels':6
        , 'inconsistent-parameters':7
        , 'inconsistent-selection-criteria':8
        , 'invalid-array-index':42
        , 'invalid-configuration-data':46
        , 'invalid-data-type':9
        , 'invalid-file-access-method':10
        , 'invalid-file-start-position':11
        , 'invalid-operator-name':12
        , 'invalid-parameter-datatype':13
        , 'invalid-time-stamp':14
        , 'key-generation-error':15
        , 'missing-required-parameter':16
        , 'no-objects-of-specified-type':17
        , 'no-space-for-object':18
        , 'no-space-to-add-list-element':19
        , 'no-space-to-write-property':20
        , 'no-vt-sessions-available':21
        , 'object-deletion-not-premitted':23
        , 'object-identifier-already-exists':24
        , 'operational-problem':25
        , 'optional-functionality-not-supported':45
        , 'password-failure':26
        , 'property-is-not-a-list':22
        , 'property-is-not-an-array':50
        , 'read-access-denied':27
        , 'security-not-supported':28
        , 'service-request-denied':29
        , 'timeout':30
        , 'unknown-object':31
        , 'unknown-property':32
        , 'unknown-vt-class':34
        , 'unknown-vt-session':35
        , 'unsupported-object-type':36
        , 'value-out-of-range':37
        , 'vt-session-already-closed':38
        , 'vt-session-termination-failure':39
        , 'write-access-denied':40
        , 'cov-subscription-failed':43
        , 'not-cov-property':44
        }

class ErrorType(Sequence):
    sequenceElements = \
        [ Element('errorClass', ErrorClass)
        , Element('errorCode', ErrorCode)
        ]

class Error(ErrorSequence, ErrorType):
    sequenceElements = ErrorType.sequenceElements
    
    def __str__(self):
        return str(self.errorClass) + ": " + str(self.errorCode)
        
ErrorTypes[12] = Error

class ChangeListError(ErrorSequence):
    sequenceElements = \
        [ Element('errorType', ErrorType, 0)
        , Element('firstFailedElementNumber', Unsigned, 1)
        ]

    def __str__(self):
        return "change list error, first failed element number " + str(self.firstFailedElementNumber)
        
ErrorTypes[8] = ChangeListError
ErrorTypes[9] = ChangeListError

class CreateObjectError(ErrorSequence):
    sequenceElements = \
        [ Element('errorType', ErrorType, 0)
        , Element('firstFailedElementNumber', Unsigned, 1)
        ]

    def __str__(self):
        return "create object error, first failed element number " + str(self.firstFailedElementNumber)
        
ErrorTypes[10] = CreateObjectError

class ConfirmedPrivateTransferError(ErrorSequence):
    sequenceElements = \
        [ Element('errorType', ErrorType, 0)
        , Element('vendorID', Unsigned, 1)
        , Element('serviceNumber', Unsigned, 2)
        , Element('errorParameters', Any, 3, True)
        ]

ErrorTypes[18] = ConfirmedPrivateTransferError

class WritePropertyMultipleError(ErrorSequence):
    sequenceElements = \
        [ Element('errorType', ErrorType, 0)
        , Element('firstFailedWriteAttempt', BACnetObjectPropertyReference, 1)
        ]

ErrorTypes[16] = WritePropertyMultipleError

class VTCloseError(ErrorSequence):
    sequenceElements = \
        [ Element('errorType', ErrorType, 0)
        , Element('listOfVTSessionIdentifiers', SequenceOf(Unsigned), 1, True)
        ]

ErrorTypes[22] = VTCloseError

#-----

class ReadPropertyRequest(ConfirmedRequestSequence):
    serviceChoice = 12
    sequenceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 0)
        , Element('propertyIdentifier', BACnetPropertyIdentifier, 1)
        , Element('propertyArrayIndex', Unsigned, 2, True)
        ]

RegisterConfirmedRequestType(ReadPropertyRequest)

class ReadPropertyACK(ComplexAckSequence):
    serviceChoice = 12
    sequenceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 0)
        , Element('propertyIdentifier', BACnetPropertyIdentifier, 1)
        , Element('propertyArrayIndex', Unsigned, 2, True)
        , Element('propertyValue', Any, 3)
        ]

RegisterComplexAckType(ReadPropertyACK)

#-----

class ReadAccessSpecification(Sequence):
    sequenceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 0)
        , Element('listOfPropertyReferences', SequenceOf(BACnetPropertyReference), 1)
        ]

class ReadPropertyMultipleRequest(ConfirmedRequestSequence):
    serviceChoice = 14
    sequenceElements = \
        [ Element('listOfReadAccessSpecs', SequenceOf(ReadAccessSpecification))
        ]

RegisterConfirmedRequestType(ReadPropertyMultipleRequest)

class ReadAccessResultElementChoice(Choice):
    choiceElements = \
        [ Element('propertyValue', Any, 4)
        , Element('propertyAccessError', Error, 5)
        ]

class ReadAccessResultElement(Sequence):
    sequenceElements = \
        [ Element('propertyIdentifier', BACnetPropertyIdentifier, 2)
        , Element('propertyArrayIndex', Unsigned, 3, True)
        , Element('readResult', ReadAccessResultElementChoice)
        ]

class ReadAccessResult(Sequence):
    sequenceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 0)
        , Element('listOfResults', SequenceOf(ReadAccessResultElement), 1)
        ]

class ReadPropertyMultipleACK(ComplexAckSequence):
    serviceChoice = 14
    sequenceElements = \
        [ Element('listOfReadAccessResults', SequenceOf(ReadAccessResult))
        ]

RegisterComplexAckType(ReadPropertyMultipleACK)

#-----

class RangeByPosition(Sequence):
    sequenceElements = \
        [ Element('referenceIndex', Unsigned)
        , Element('count', Integer)
        ]

class RangeBySequenceNumber(Sequence):
    sequenceElements = \
        [ Element('referenceIndex', Unsigned)
        , Element('count', Integer)
        ]

class RangeByTime(Sequence):
    sequenceElements = \
        [ Element('referenceTime', BACnetDateTime)
        , Element('count', Integer)
        ]

class Range(Choice):
    choiceElements = \
        [ Element('byPosition', RangeByPosition, 3)
        , Element('bySequenceNumber', RangeBySequenceNumber, 6)
        , Element('byTime', RangeByTime, 7)
        ]

class ReadRangeRequest(ConfirmedRequestSequence):
    serviceChoice = 26
    sequenceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 0)
        , Element('propertyIdentifier', BACnetPropertyIdentifier, 1)
        , Element('propertyArrayIndex', Unsigned, 2, True)
        , Element('range', Range, optional=True)
        ]

RegisterConfirmedRequestType(ReadPropertyRequest)

class ReadRangeACK(ComplexAckSequence):
    serviceChoice = 26
    sequenceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 0)
        , Element('propertyIdentifier', BACnetPropertyIdentifier, 1)
        , Element('propertyArrayIndex', Unsigned, 2, True)
        , Element('resultFlags', BACnetResultFlags, 3)
        , Element('itemCount', Unsigned, 4)
        , Element('itemData', SequenceOf(Any), 5)
        , Element('firstSequenceNumber', Unsigned, 6, True)
        ]

RegisterComplexAckType(ReadPropertyACK)

#-----

class WritePropertyRequest(ConfirmedRequestSequence):
    serviceChoice = 15
    sequenceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 0)
        , Element('propertyIdentifier', BACnetPropertyIdentifier, 1)
        , Element('propertyArrayIndex', Unsigned, 2, True)
        , Element('propertyValue', Any, 3)
        , Element('priority', Integer, 4, True)
        ]

RegisterConfirmedRequestType(WritePropertyRequest)

#-----

class WriteAccessSpecification(Sequence):
    sequenceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 0)
        , Element('listOfProperties', SequenceOf(BACnetPropertyValue), 1)
        ]

class WritePropertyMultipleRequest(ConfirmedRequestSequence):
    serviceChoice = 16
    sequenceElements = \
        [ Element('listOfWriteAccessSpecs', SequenceOf(WriteAccessSpecification))
        ]

RegisterConfirmedRequestType(WritePropertyMultipleRequest)

#-----

class IAmRequest(UnconfirmedRequestSequence):
    serviceChoice = 0
    sequenceElements = \
        [ Element('iAmDeviceIdentifier', ObjectIdentifier)
        , Element('maxAPDULengthAccepted', Unsigned)
        , Element('segmentationSupported', BACnetSegmentation)
        , Element('vendorID', Unsigned)
        ]
        
RegisterUnconfirmedRequestType(IAmRequest)

#-----

class IHaveRequest(UnconfirmedRequestSequence):
    serviceChoice = 1
    sequenceElements = \
        [ Element('deviceIdentifier', ObjectIdentifier)
        , Element('objectIdentifier', ObjectIdentifier)
        , Element('objectName', CharacterString)
        ]
        
RegisterUnconfirmedRequestType(IHaveRequest)

#-----

class WhoHasLimits(Sequence):
    sequenceElements = \
        [ Element('deviceInstanceRangeLowLimit', Unsigned, 0)
        , Element('deviceInstanceRangeHighLimit', Unsigned, 1)
        ]

class WhoHasObject(Choice):
    choiceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 2)
        , Element('objectName', CharacterString, 3)
        ]

class WhoHasRequest(UnconfirmedRequestSequence):
    serviceChoice = 7
    sequenceElements = \
        [ Element('limits', WhoHasLimits, None, True)
        , Element('object', WhoHasObject)
        ]

RegisterUnconfirmedRequestType(WhoHasRequest)

#-----

class WhoIsRequest(UnconfirmedRequestSequence):
    serviceChoice = 8
    sequenceElements = \
        [ Element('deviceInstanceRangeLowLimit', Unsigned, 0, True)
        , Element('deviceInstanceRangeHighLimit', Unsigned, 1, True)
        ]

RegisterUnconfirmedRequestType(WhoIsRequest)
        
#-----

class ConfirmedEventNotificationRequest(ConfirmedRequestSequence):
    serviceChoice = 2
    sequenceElements = \
        [ Element('processIdentifier', Unsigned, 0)
        , Element('initiatingDeviceIdentifier', ObjectIdentifier, 1)
        , Element('eventObjectIdentifier', ObjectIdentifier, 2)
        , Element('timeStamp', BACnetTimeStamp, 3)
        , Element('notificationClass', Unsigned, 4)
        , Element('priority', Unsigned, 5)
        , Element('eventType', BACnetEventType, 6)
        , Element('messageText', CharacterString, 7, True)
        , Element('notifyType', BACnetNotifyType, 8)
        , Element('ackRequired', Boolean, 9, True)
        , Element('fromState', BACnetEventState, 10, True)
        , Element('toState', BACnetEventState, 11)
        , Element('eventValues', BACnetNotificationParameters, 12, True)
        ]

RegisterConfirmedRequestType(ConfirmedEventNotificationRequest)

class UnconfirmedEventNotificationRequest(Sequence):
    sequenceElements = ConfirmedEventNotificationRequest.sequenceElements

class UnconfirmedCOVNotificationRequest(UnconfirmedRequestSequence):
    serviceChoice = 2
    sequenceElements = \
        [ Element('subscriberProcessIdentifier', Unsigned, 0)
        , Element('initiatingDeviceIdentifier', ObjectIdentifier, 1)
        , Element('monitoredObjectIdentifier', ObjectIdentifier, 2)
        , Element('timeRemaining', Unsigned, 3)
        , Element('listOfValues', SequenceOf(BACnetPropertyValue), 4)
        ]

RegisterUnconfirmedRequestType(UnconfirmedCOVNotificationRequest)
        
#-----

