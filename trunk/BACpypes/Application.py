
import sys
import traceback
from pprint import pprint

from BACpypes.PDU import Address, GlobalBroadcast
from BACpypes.CommunicationsCore import ServiceAccessPoint, ApplicationServiceElement, Bind

from BACpypes.PrimativeData import *
from BACpypes.ConstructedData import *

from BACpypes.ApplicationService import StateMachineAccessPoint, ApplicationServiceAccessPoint, DebugApplicationServiceAccessPoint
from BACpypes.NetworkService import NetworkServiceAccessPoint, NetworkServiceElement
from BACpypes.BVLL import BIPSimple, AnnexJCodec, UDPMultiplexer

from BACpypes.Object import LocalDeviceObject, PropertyError
from BACpypes.APDU import ConfirmedRequestPDU, SimpleAckPDU, RejectPDU, BACnetRejectReason
from BACpypes.APDU import WhoIsRequest, IAmRequest, Error
from BACpypes.APDU import ReadPropertyRequest, ReadPropertyACK
from BACpypes.APDU import WritePropertyRequest

# some debugging
_debug = ('--debugApplication' in sys.argv)
_debugNoTrapHelper = ('--debugNoTrapHelper' in sys.argv)

#
#   Application
#

class Application(ApplicationServiceElement):

    def __init__(self, localDevice, localAddress, aseID=None):
        if _debug:
            print "Application.__init__", localDevice, aseID
        ApplicationServiceElement.__init__(self, aseID)
        
        # keep track of the local device
        self.localDevice = localDevice
        
        # allow the address to be cast to the correct type
        if isinstance(localAddress, Address):
            self.localAddress = localAddress
        else:
            self.localAddress = Address(localAddress)
        
        # local objects by ID and name
        self.objectName = {localDevice.objectName:localDevice}
        self.objectIdentifier = {localDevice.objectIdentifier:localDevice}
        
        # keep a cache of I-Am responses
        self.iAmCache = {}
        
    def AddObject(self, obj):
        """Add an object to the local collection."""
        self.objectName[obj.objectName] = obj
        self.objectIdentifier[obj.objectIdentifier] = obj
        
        # append the new object's identifier to the device's object list
        self.localDevice.objectList.append(obj.objectIdentifier)
        
    def DeleteObject(self, obj):
        """Add an object to the local collection."""
        del self.objectName[obj.objectName]
        del self.objectIdentifier[obj.objectIdentifier]
        
        # remove the object's identifier from the device's object list
        indx = self.localDevice.objectList.index(obj.objectIdentifier)
        del self.localDevice.objectList[indx]
        
    def GetObjectID(self, objid):
        """Return a local object or None."""
        return self.objectIdentifier.get(objid, None)
        
    def GetObjectName(self, objname):
        """Return a local object or None."""
        return self.objectName.get(objname, None)
        
    def ObjectIter(self):
        """Iterate over the objects."""
        return self.objectIdentifier.itervalues()

    #-----
    
    def Indication(self, apdu):
        if _debug:
            print "Application.Indication"
            apdu.DebugContents()
            
        # get a helper function
        helperName = "do_" + apdu.__class__.__name__
        helperFn = getattr(self, helperName, None)
        if _debug:
            print "    - helperFn", helperFn
            
        # send back a reject for unrecognized services
        if not helperFn:
            if isinstance(apdu, ConfirmedRequestPDU):
                response = RejectPDU( apdu.apduInvokeID, BACnetRejectReason.UNRECOGNIZEDSERVICE, context=apdu)
                self.Response(response)
            return
        
        # pass the apdu on to the helper function
        if _debugNoTrapHelper:
            helperFn(apdu)
            if _debug:
                print "    - helperFn complete"
        else:
            try:
                helperFn(apdu)
                if _debug:
                    print "    - helperFn complete"
            except:
                print "Exception processing", apdu, ':', sys.exc_info()[1]
                if _debug:
                    pprint(traceback.extract_stack())
                    print
                
                # send back an error
                if isinstance(apdu, ConfirmedRequestPDU):
                    resp = Error(errorClass='device', errorCode='operational-problem', context=apdu)
                    self.Response(resp)
    
    def do_WhoIsRequest(self, apdu):
        """Respond to a Who-Is request."""
        if _debug:
            print "Application.do_WhoIsRequest"
            
        # may be a restriction
        if (apdu.deviceInstanceRangeLowLimit is not None) and \
                (apdu.deviceInstanceRangeHighLimit is not None):
            if (self.localDevice.objectIdentifier[1] < apdu.deviceInstanceRangeLowLimit):
                return
            if (self.localDevice.objectIdentifier[1] > apdu.deviceInstanceRangeHighLimit):
                return
                
        # create a I-Am "response"
        iAm = IAmRequest()
        iAm.iAmDeviceIdentifier = self.localDevice.objectIdentifier
        iAm.maxAPDULengthAccepted = self.localDevice.maxApduLengthAccepted
        iAm.segmentationSupported = self.localDevice.segmentationSupported
        iAm.vendorID = self.localDevice.vendorIdentifier
        
        # blast it out
        iAm.pduDestination = GlobalBroadcast()
        self.Request(iAm)
        
    def do_IAmRequest(self, apdu):
        """Given an I-Am request, cache it."""
        if _debug:
            print "Application.do_IAmRequest"
            
        self.iAmCache[apdu.iAmDeviceIdentifier] = apdu
        
    def do_ReadPropertyRequest(self, apdu):
        """Return the value of some property of one of our objects."""
        if _debug:
            print "Application.do_ReadPropertyRequest"
            
        # get the object
        obj = self.GetObjectID(apdu.objectIdentifier)
        if _debug:
            print "    - object:", obj
        if not obj:
            resp = Error(errorClass='object', errorCode='unknown-object', context=apdu)
        else:
            try:
                # get the datatype
                datatype = obj.GetDatatype(apdu.propertyIdentifier)
                if _debug:
                    print "    - datatype:", datatype
                    
                # get the value
                value = obj.ReadProperty(apdu.propertyIdentifier, apdu.propertyArrayIndex)
                if _debug:
                    print "    - value:", value, type(value)
                    
                # change atomic values into something encodeable
                if issubclass(datatype, Atomic):
                    value = datatype(value)
                elif issubclass(datatype, Array) and (apdu.propertyArrayIndex is not None):
                    if apdu.propertyArrayIndex == 0:
                        value = Integer(value)
                    elif issubclass(datatype.subtype, Atomic):
                        value = datatype.subtype(value)
                    elif not isinstance(value, datatype.subtype):
                        raise TypeError, "invalid result datatype, expecting %s" % (datatype.subtype.__name__,)
                elif not isinstance(value, datatype):
                    raise TypeError, "invalid result datatype, expecting %s" % (datatype.__name__,)
                if _debug:
                    print "    - encodeable value:", value, type(value)
                    
                # this is a ReadProperty ack
                resp = ReadPropertyACK(context=apdu)
                resp.objectIdentifier = apdu.objectIdentifier
                resp.propertyIdentifier = apdu.propertyIdentifier
                resp.propertyArrayIndex = apdu.propertyArrayIndex
        
                # save the result in the property value
                resp.propertyValue = Any()
                resp.propertyValue.CastIn(value)
        
            except PropertyError:
                resp = Error(errorClass='object', errorCode='unknown-property', context=apdu)
        
        # return the result
        self.Response(resp)
        
    def do_WritePropertyRequest(self, apdu):
        """Change the value of some property of one of our objects."""
        if _debug:
            print "Application.do_WritePropertyRequest"
            
        # get the object
        obj = self.GetObjectID(apdu.objectIdentifier)
        if _debug:
            print "    - object:", obj
        if not obj:
            resp = Error(errorClass='object', errorCode='unknown-object', context=apdu)
        else:
            try:
                # get the datatype
                datatype = obj.GetDatatype(apdu.propertyIdentifier)
                if _debug:
                    print "    - datatype:", datatype
                    
                # special case for array parts, others are managed by CastOut
                if issubclass(datatype, Array) and (apdu.propertyArrayIndex is not None):
                    if apdu.propertyArrayIndex == 0:
                        value = resp.propertyValue.CastOut(Integer)
                    else:
                        value = resp.propertyValue.CastOut(datatype.subtype)
                else:
                    value = resp.propertyValue.CastOut(datatype)
                if _debug:
                    print "    - value:", value, type(value)

                # change the value
                value = obj.WriteProperty(apdu.propertyIdentifier, value, apdu.propertyArrayIndex, apdu.priority)
                    
                # success
                resp = SimpleAckPDU(context=apdu)
                
            except PropertyError:
                resp = Error(errorClass='object', errorCode='unknown-property', context=apdu)
        
        # return the result
        self.Response(resp)
        
#
#   BIPSimpleApplication
#

class BIPSimpleApplication(Application):

    def __init__(self, localDevice, localAddress, aseID=None):
        if _debug:
            print "BIPSimpleApplication.__init__", localDevice, localAddress, aseID
        Application.__init__(self, localDevice, localAddress, aseID)
        
        if _debug:
            # make a debugger at the top
            self.dasap = DebugApplicationServiceAccessPoint()
        else:
            self.dasap = None
        
        # include a application decoder
        self.asap = ApplicationServiceAccessPoint()
        
        # pass the device object to the state machine access point so it
        # can know if it should support segmentation
        self.smap = StateMachineAccessPoint(localDevice)
        
        # a network service access point will be needed
        self.nsap = NetworkServiceAccessPoint()
        
        # give the NSAP a generic network layer service element
        self.nse = NetworkServiceElement()
        Bind(self.nse, self.nsap)
        
        # bind the top layers
        if _debug:
            Bind(self, self.dasap, self.asap, self.smap, self.nsap)
        else:
            Bind(self, self.asap, self.smap, self.nsap)
        
        # create a generic BIP stack, bound to the Annex J server 
        # on the UDP multiplexer
        self.bip = BIPSimple()
        self.annexj = AnnexJCodec()
        self.mux = UDPMultiplexer(self.localAddress)
        
        # bind the bottom layers
        Bind(self.bip, self.annexj, self.mux.annexJ)
        
        # bind the NSAP to the stack, no network number
        self.nsap.Bind(self.bip)
