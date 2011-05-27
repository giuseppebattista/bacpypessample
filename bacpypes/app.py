#!/usr/bin/python

"""
Application Module
"""

from debugging import ModuleLogger, Logging
from comm import ApplicationServiceElement, bind

from pdu import Address, GlobalBroadcast

from primitivedata import *
from constructeddata import *

from appservice import StateMachineAccessPoint, ApplicationServiceAccessPoint
from netservice import NetworkServiceAccessPoint, NetworkServiceElement
from bvllservice import BIPSimple, BIPForeign, AnnexJCodec, UDPMultiplexer

from object import PropertyError
from apdu import ConfirmedRequestPDU, SimpleAckPDU, RejectPDU, BACnetRejectReason
from apdu import IAmRequest, ReadPropertyACK, Error

# some debugging
_debug = 0
_log = ModuleLogger(globals())

#
#   Application
#

class Application(ApplicationServiceElement, Logging):

    def __init__(self, localDevice, localAddress, aseID=None):
        if _debug: Application._debug("__init__ %r %r aseID=%r", localDevice, localAddress, aseID)
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
        
    def add_object(self, obj):
        """Add an object to the local collection."""
        if _debug: Application._debug("add_object %r", obj)
        self.objectName[obj.objectName] = obj
        self.objectIdentifier[obj.objectIdentifier] = obj
        
        # append the new object's identifier to the device's object list
        self.localDevice.objectList.append(obj.objectIdentifier)
        
    def delete_object(self, obj):
        """Add an object to the local collection."""
        if _debug: Application._debug("delete_object %r", obj)
        del self.objectName[obj.objectName]
        del self.objectIdentifier[obj.objectIdentifier]
        
        # remove the object's identifier from the device's object list
        indx = self.localDevice.objectList.index(obj.objectIdentifier)
        del self.localDevice.objectList[indx]
        
    def get_object_id(self, objid):
        """Return a local object or None."""
        return self.objectIdentifier.get(objid, None)
        
    def get_object_name(self, objname):
        """Return a local object or None."""
        return self.objectName.get(objname, None)
        
    def iter_objects(self):
        """Iterate over the objects."""
        return self.objectIdentifier.itervalues()

    #-----
    
    def indication(self, apdu):
        if _debug: Application._debug("indication %r", apdu)
            
        # get a helper function
        helperName = "do_" + apdu.__class__.__name__
        helperFn = getattr(self, helperName, None)
        if _debug: Application._debug("    - helperFn: %r", helperFn)
        
        # send back a reject for unrecognized services
        if not helperFn:
            if isinstance(apdu, ConfirmedRequestPDU):
                response = RejectPDU( apdu.apduInvokeID, BACnetRejectReason.UNRECOGNIZED_SERVICE, context=apdu)
                self.response(response)
            return
        
        # pass the apdu on to the helper function
        try:
            helperFn(apdu)
        except Exception, e:
            Application._exception("exception: %r", e)
            
            # send back an error
            if isinstance(apdu, ConfirmedRequestPDU):
                resp = Error(errorClass='device', errorCode='operational-problem', context=apdu)
                self.response(resp)

    def do_WhoIsRequest(self, apdu):
        """Respond to a Who-Is request."""
        if _debug: Application._debug("do_WhoIsRequest %r", apdu)
        
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
        self.request(iAm)
        
    def do_IAmRequest(self, apdu):
        """Given an I-Am request, cache it."""
        if _debug: Application._debug("do_IAmRequest %r", apdu)
            
        self.iAmCache[apdu.iAmDeviceIdentifier] = apdu
        
    def do_ReadPropertyRequest(self, apdu):
        """Return the value of some property of one of our objects."""
        if _debug: Application._debug("do_ReadPropertyRequest %r", apdu)
        
        # get the object
        obj = self.get_object_id(apdu.objectIdentifier)
        if _debug: Application._debug("    - object: %r", obj)
        
        if not obj:
            resp = Error(errorClass='object', errorCode='unknown-object', context=apdu)
        else:
            try:
                # get the datatype
                datatype = obj.get_datatype(apdu.propertyIdentifier)
                if _debug: Application._debug("    - datatype: %r", datatype)
                
                # get the value
                value = obj.ReadProperty(apdu.propertyIdentifier, apdu.propertyArrayIndex)
                if _debug: Application._debug("    - value: %r", value)
                
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
                if _debug: Application._debug("    - encodeable value: %r", value)
                
                # this is a ReadProperty ack
                resp = ReadPropertyACK(context=apdu)
                resp.objectIdentifier = apdu.objectIdentifier
                resp.propertyIdentifier = apdu.propertyIdentifier
                resp.propertyArrayIndex = apdu.propertyArrayIndex
        
                # save the result in the property value
                resp.propertyValue = Any()
                resp.propertyValue.cast_in(value)
        
            except PropertyError:
                resp = Error(errorClass='object', errorCode='unknown-property', context=apdu)
        
        # return the result
        self.response(resp)
        
    def do_WritePropertyRequest(self, apdu):
        """Change the value of some property of one of our objects."""
        if _debug: Application._debug("do_WritePropertyRequest %r", apdu)
        
        # get the object
        obj = self.get_object_id(apdu.objectIdentifier)
        if _debug: Application._debug("    - object: %r", obj)
        
        if not obj:
            resp = Error(errorClass='object', errorCode='unknown-object', context=apdu)
        else:
            try:
                # get the datatype
                datatype = obj.get_datatype(apdu.propertyIdentifier)
                if _debug: Application._debug("    - datatype: %r", datatype)
                
                # special case for array parts, others are managed by cast_out
                if issubclass(datatype, Array) and (apdu.propertyArrayIndex is not None):
                    if apdu.propertyArrayIndex == 0:
                        value = resp.propertyValue.cast_out(Unsigned)
                    else:
                        value = resp.propertyValue.cast_out(datatype.subtype)
                else:
                    value = resp.propertyValue.cast_out(datatype)
                if _debug: Application._debug("    - value: %r", value)
                
                # change the value
                value = obj.WriteProperty(apdu.propertyIdentifier, value, apdu.propertyArrayIndex, apdu.priority)
                    
                # success
                resp = SimpleAckPDU(context=apdu)
                
            except PropertyError:
                resp = Error(errorClass='object', errorCode='unknown-property', context=apdu)
        
        # return the result
        self.response(resp)
        
#
#   BIPSimpleApplication
#

class BIPSimpleApplication(Application, Logging):

    def __init__(self, localDevice, localAddress, aseID=None):
        if _debug: BIPSimpleApplication._debug("__init__ %r %r aseID=%r", localDevice, localAddress, aseID)
        Application.__init__(self, localDevice, localAddress, aseID)
        
        # include a application decoder
        self.asap = ApplicationServiceAccessPoint()
        
        # pass the device object to the state machine access point so it
        # can know if it should support segmentation
        self.smap = StateMachineAccessPoint(localDevice)
        
        # a network service access point will be needed
        self.nsap = NetworkServiceAccessPoint()
        
        # give the NSAP a generic network layer service element
        self.nse = NetworkServiceElement()
        bind(self.nse, self.nsap)
        
        # bind the top layers
        bind(self, self.asap, self.smap, self.nsap)
        
        # create a generic BIP stack, bound to the Annex J server 
        # on the UDP multiplexer
        self.bip = BIPSimple()
        self.annexj = AnnexJCodec()
        self.mux = UDPMultiplexer(self.localAddress)
        
        # bind the bottom layers
        bind(self.bip, self.annexj, self.mux.annexJ)
        
        # bind the BIP stack to the network, no network number
        self.nsap.bind(self.bip)

#
#   BIPForeignApplication
#

class BIPForeignApplication(Application, Logging):

    def __init__(self, localDevice, localAddress, bbmdAddress, bbmdTTL, aseID=None):
        if _debug: BIPForeignApplication._debug("__init__ %r %r %r %r aseID=%r", localDevice, localAddress, bbmdAddress, bbmdTTL, aseID)
        Application.__init__(self, localDevice, localAddress, aseID)
        
        # include a application decoder
        self.asap = ApplicationServiceAccessPoint()
        
        # pass the device object to the state machine access point so it
        # can know if it should support segmentation
        self.smap = StateMachineAccessPoint(localDevice)
        
        # a network service access point will be needed
        self.nsap = NetworkServiceAccessPoint()
        
        # give the NSAP a generic network layer service element
        self.nse = NetworkServiceElement()
        bind(self.nse, self.nsap)
        
        # bind the top layers
        bind(self, self.asap, self.smap, self.nsap)
        
        # create a generic BIP stack, bound to the Annex J server 
        # on the UDP multiplexer
        self.bip = BIPForeign(bbmdAddress, bbmdTTL)
        self.annexj = AnnexJCodec()
        self.mux = UDPMultiplexer(self.localAddress, noBroadcast=True)
        
        # bind the bottom layers
        bind(self.bip, self.annexj, self.mux.annexJ)
        
        # bind the NSAP to the stack, no network number
        self.nsap.bind(self.bip)

#
#   BIPNetworkApplication
#

class BIPNetworkApplication(NetworkServiceElement, Logging):

    def __init__(self, localAddress, eID=None):
        if _debug: BIPNetworkApplication._debug("__init__ %r eID=%r", localAddress, eID)
        NetworkServiceElement.__init__(self, eID)
        
        # allow the address to be cast to the correct type
        if isinstance(localAddress, Address):
            self.localAddress = localAddress
        else:
            self.localAddress = Address(localAddress)
        
        # a network service access point will be needed
        self.nsap = NetworkServiceAccessPoint()
        
        # give the NSAP a generic network layer service element
        bind(self, self.nsap)
        
        # create a generic BIP stack, bound to the Annex J server 
        # on the UDP multiplexer
        self.bip = BIPSimple()
        self.annexj = AnnexJCodec()
        self.mux = UDPMultiplexer(self.localAddress)
        
        # bind the bottom layers
        bind(self.bip, self.annexj, self.mux.annexJ)
        
        # bind the NSAP to the stack, no network number
        self.nsap.bind(self.bip)

