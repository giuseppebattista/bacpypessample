
import sys
import re
import types

from Exceptions import *

from PrimativeData import *
from ConstructedData import *
from BaseTypes import *

# some debugging
_debug = ('--debugObject' in sys.argv)

#
#   PropertyError
#

class PropertyError(AttributeError):
    pass
    
#
#   MapName
#
#   Given a Python identifier, return the property identifier.
#

MapNameRE = re.compile('[a-z][A-Z]')

def MapFn(m):
    pair = m.group()
    return pair[0] + "-" + pair[1].lower()
    
def MapName(name):
    return MapNameRE.sub(MapFn, name)

# a dictionary of object types and classes
ObjectTypes = {}

#
#   RegisterObjectType
#

def RegisterObjectType(klass):
    # make sure it's an Object derived class
    if not issubclass(klass, Object):
        raise RuntimeError, "Object derived class required"
        
    # build a property dictionary by going through the class and all its parents
    _properties = {}
    for c in klass.__mro__:
        for prop in getattr(c, 'properties', []):
            if prop.identifier not in _properties:
                _properties[prop.identifier] = prop
    
    # if the object type hasn't been provided, make an immutable one
    if 'object-type' not in _properties:
        _properties['object-type'] = Property('object-type', ObjectType, klass.objectType, mutable=False)
        
    # store this in the class
    klass._properties = _properties
    
    # now save this in all our types
    ObjectTypes[klass.objectType] = klass
    
#
#   GetObjectClass
#

def GetObjectClass(objectType):
    return ObjectTypes.get(objectType)
    
#
#   GetDatatype
#

def GetDatatype(objectType, property):
    """Return the datatype for the property of an object."""
    # get the related class
    cls = ObjectTypes.get(objectType)
    if not cls:
        return None
        
    # get the property
    prop = cls._properties.get(property)
    if not prop:
        return None
    
    # return the datatype
    return prop.datatype
    
#
#   Property
#

class Property:

    def __init__(self, identifier, datatype, default=None, optional=True, mutable=True):
        ### validate the identifier to be one of the Property enumerations
        self.identifier = identifier
        self.datatype = datatype
        self.optional = optional
        self.mutable = mutable
        self.default = default

    def ReadProperty(self, obj, arrayIndex=None):
        if _debug:
            print self, "Property.ReadProperty", obj, arrayIndex
            
        # get the value
        value = obj._values[self.identifier]
        
        # access an array
        if arrayIndex is not None:
            if not issubclass(self.datatype, Array):
                raise TypeError, "%s is not an array" % (self.identifier,)
                
            # dive in, the water's fine
            value = value[arrayIndex]
            
        # all set
        return value

    def WriteProperty(self, obj, value, arrayIndex=None, priority=None):
        if _debug:
            print self, "Property.WriteProperty", obj, value, arrayIndex, priority
            
        # see if it must be provided
        if not self.optional and value is None:
            raise ValueError, "%s value required" % (self.identifier,)
            
        # see if it can be changed
        if not self.mutable:
            raise RuntimeError, "%s immutable property" % (self.identifier,)
            
        # if it's atomic or already the correct type, leave it alone
        if issubclass(self.datatype, Atomic) or isinstance(value, self.datatype):
            pass
        elif arrayIndex is not None:
            if not issubclass(self.datatype, Array):
                raise TypeError, "%s is not an array" % (self.identifier,)
                
            # check the array
            arry = obj._values[self.identifier]
            if arry is None:
                raise ValueError, "%s uninitialized array" % (self.identifier,)
                
            # seems to be OK, let the array object take over
            arry[arrayIndex] = value
            
            return
        else:
            # coerce the value
            value = self.datatype(value)
            
        # seems to be OK
        obj._values[self.identifier] = value
        
#
#   ObjectIdentifierProperty
#

class ObjectIdentifierProperty(Property):

    def WriteProperty(self, obj, value, arrayIndex=None, priority=None):
        if _debug:
            print self, "ObjectIdentifierProperty.WriteProperty", obj, value, arrayIndex, priority
            
        # make it easy to default
        if value is None:
            pass
        elif isinstance(value, types.IntType) or isinstance(value, types.LongType):
            value = (obj.objectType, value)
        elif isinstance(value, types.TupleType) and len(value) == 2:
            if value[0] != obj.objectType:
                raise ValueError, "%s required" % (obj.objectType,)
        else:
            raise TypeError, "object identifier"
        
        return Property.WriteProperty( self, obj, value, arrayIndex, priority )
        
#
#   CurrentDateProperty
#

class CurrentDateProperty(Property):

    def __init__(self, identifier):
        Property.__init__(self, identifier, Date, default=None, optional=True, mutable=False)
        
    def ReadProperty(self, obj, arrayIndex=None):
        # access an array
        if arrayIndex is not None:
            raise TypeError, "%s is unsubscriptable" % (self.identifier,)
            
        # get the value
        now = Date()
        now.Now()
        return now.value
                
    def WriteProperty(self, obj, value, arrayIndex=None, priority=None):
        raise RuntimeError, "%s immutable property" % (self.identifier,)
    
#
#   CurrentTimeProperty
#

class CurrentTimeProperty(Property):

    def __init__(self, identifier):
        Property.__init__(self, identifier, Time, default=None, optional=True, mutable=False)
        
    def ReadProperty(self, obj, arrayIndex=None):
        # access an array
        if arrayIndex is not None:
            raise TypeError, "%s is unsubscriptable" % (self.identifier,)
            
        # get the value
        now = Time()
        now.Now()
        return now.value
                
    def WriteProperty(self, obj, value, arrayIndex=None, priority=None):
        raise RuntimeError, "%s immutable property" % (self.identifier,)
    
#
#   Object
#

class Object(object):

    properties = \
        [ ObjectIdentifierProperty('object-identifier', ObjectIdentifier, optional=False)
        , Property('object-name', CharacterString, optional=False)
        , Property('description', CharacterString, default='')
        ]
    _properties = {}
    
    def __init__(self, **kwargs):
        """Create an object, with default property values as needed."""
        # map the python names into property names and make sure they 
        # are appropriate for this object
        initargs = {}
        for key, value in kwargs.items():
            pname = MapName(key)
            if pname not in self._properties:
                raise PropertyError, pname
            initargs[pname] = value
            
        # start with a clean dict of values
        self._values = {}
        
        # initialize the object
        for prop in self._properties.values():
            propid = prop.identifier
            if initargs.has_key(propid):
                # defer to the property object for error checking
                prop.WriteProperty(self, initargs[propid])
            elif prop.default is not None:
                # default values bypass property interface
                self._values[propid] = prop.default
            elif not prop.optional:
                raise PropertyError, "%s required" % (propid,)
            else:
                self._values[propid] = None
                
    def _attrToProp(self, attr):
        """Common routine to translate a python attribute name to a property name and 
        return the appropriate property."""
        # get the property
        property = MapName(attr)
        prop = self._properties.get(property)
        if not prop:
            raise PropertyError, property
            
        # found it
        return prop
        
    def __getattr__(self, attr):
        if attr.startswith('_') or attr[0].isupper():
            return object.__getattribute__(self, attr)
            
        # defer to the property to get the value
        return self._attrToProp(attr).ReadProperty(self)
        
    def __setattr__(self, attr, value):
        if attr.startswith('_') or attr[0].isupper():
            return object.__setattr__(self, attr, value)
            
        # defer to the property to get the value
        return self._attrToProp(attr).WriteProperty(self, value)
        
    def ReadProperty(self, property, arrayIndex=None):
        if _debug:
            print self, "Object.ReadProperty", property, arrayIndex
            
        # get the property
        prop = self._properties.get(property)
        if not prop:
            raise PropertyError, property
            
        # defer to the property to get the value
        return prop.ReadProperty(self, arrayIndex)

    def WriteProperty(self, property, value, arrayIndex=None, priority=None):
        if _debug:
            print self, "Object.WriteProperty", property, arrayIndex
            
        # get the property
        prop = self._properties.get(property)
        if not prop:
            raise PropertyError, property
            
        # defer to the property to set the value
        return prop.WriteProperty(self, value, arrayIndex, priority)
        
    def GetDatatype(self, property):
        """Return the datatype for the property of an object."""
        if _debug:
            print self, "Object.GetDatatype", property
            
        # get the property
        prop = self._properties.get(property)
        if not prop:
            raise PropertyError, property
            
        # return the datatype
        return prop.datatype
        
    def DebugContents(self, indent=1):
        """Print out interesting things about the object."""
        klasses = list(self.__class__.__mro__)
        klasses.reverse()
        
        # build a list of properties "bottom up"
        properties = []
        for c in klasses:
            properties.extend(getattr(c, 'properties', []))
        
        # print out the values
        for prop in properties:
            value = prop.ReadProperty(self)
            if hasattr(value, "DebugContents"):
                print "%s%s" % ("    " * indent, prop.identifier)
                value.DebugContents(indent+1)
            else:
                print "%s%s = %r" % ("    " * indent, prop.identifier, value)
            
#
#   Standard Object Types
#

class AnalogInputObject(Object):
    objectType = 'analog-input'
    properties = \
        [ Property('present-value', Real)
        , Property('status-flags', BACnetStatusFlags)
        , Property('event-state', BACnetEventState)
        , Property('out-of-service', Boolean)
        ]

RegisterObjectType(AnalogInputObject)

class AnalogOutputObject(Object):
    objectType = 'analog-output'
    properties = \
        [ Property('present-value', Real)
        , Property('status-flags', BACnetStatusFlags)
        , Property('event-state', BACnetEventState)
        , Property('out-of-service', Boolean)
        ]

RegisterObjectType(AnalogOutputObject)

class AnalogValueObject(Object):
    objectType = 'analog-value'
    properties = \
        [ Property('present-value', Real)
        , Property('status-flags', BACnetStatusFlags)
        , Property('event-state', BACnetEventState)
        , Property('out-of-service', Boolean)
        ]

RegisterObjectType(AnalogValueObject)

class BinaryInputObject(Object):
    objectType = 'binary-input'
    properties = \
        [ Property('present-value', BACnetBinaryPV)
        , Property('status-flags', BACnetStatusFlags)
        , Property('event-state', BACnetEventState)
        , Property('out-of-service', Boolean)
        ]

RegisterObjectType(BinaryInputObject)

class BinaryOutputObject(Object):
    objectType = 'binary-output'
    properties = \
        [ Property('present-value', BACnetBinaryPV)
        , Property('status-flags', BACnetStatusFlags)
        , Property('event-state', BACnetEventState)
        , Property('out-of-service', Boolean)
        ]

RegisterObjectType(BinaryOutputObject)

class BinaryValueObject(Object):
    objectType = 'binary-value'
    properties = \
        [ Property('present-value', BACnetBinaryPV)
        , Property('status-flags', BACnetStatusFlags)
        , Property('event-state', BACnetEventState)
        , Property('out-of-service', Boolean)
        ]

RegisterObjectType(BinaryValueObject)

class CalendarObject(Object):
    objectType = 'calendar'
    properties = []

RegisterObjectType(CalendarObject)

class CommandObject(Object):
    objectType = 'command'
    properties = []

RegisterObjectType(CommandObject)

class DeviceObject(Object):
    objectType = 'device'
    properties = \
        [ Property('system-status', BACnetDeviceStatus)
        , Property('vendor-name', CharacterString)
        , Property('vendor-identifier', Unsigned)
        , Property('model-name', CharacterString)
        , Property('firmware-revision', CharacterString)
        , Property('application-software-version', CharacterString)
        , Property('location', CharacterString)
        , Property('protocol-version', Unsigned)
        , Property('protocol-conformance-class', Unsigned)
        , Property('protocol-services-supported', BACnetServicesSupported)
        , Property('protocol-object-types-supported', BACnetObjectTypesSupported)
        , Property('object-list', ArrayOf(ObjectIdentifier))
        , Property('max-apdu-length-accepted', Unsigned)
        , Property('segmentation-supported', BACnetSegmentation)
        , Property('max-segments-accepted', Unsigned)
        , Property('apdu-segment-timeout', Unsigned)
        , Property('apdu-timeout', Unsigned)
        , Property('number-of-apdu-retries', Unsigned)
        , Property('device-address-binding', SequenceOf(BACnetAddressBinding))
        ]

RegisterObjectType(DeviceObject)

class LocalDeviceObject(DeviceObject):
    properties = \
        [ CurrentTimeProperty('local-time')
        , CurrentDateProperty('local-date')
        ]
        
    defaultProperties = \
        { 'maxApduLengthAccepted': 1024
        , 'segmentationSupported': 'segmented-both'
        , 'maxSegmentsAccepted': 16
        , 'apduSegmentTimeout': 20000
        , 'apduTimeout': 3000
        , 'numberOfApduRetries': 3
        }
        
    def __init__(self, **kwargs):
        if _debug:
            print "LocalDeviceObject.__init__", kwargs
        
        # proceed as usual
        DeviceObject.__init__(self, **kwargs)
        
        # create a default implementation of an object list for local devices.
        # If it is specified in the kwargs, that overrides this default.  If
        # a derived class provides its own implementation, this could be an 
        # orphan (just sitting there with no access).
        if (self._values['object-list'] is None) and ('objectList' not in kwargs):
            try:
                self.objectList = ArrayOf(ObjectIdentifier)()
                
                # make sure this device object is in its own list
                self.objectList.append(self.objectIdentifier)
            except:
                pass
        
        # fill in the rest (if they haven't been supplied)
        for attr, value in LocalDeviceObject.defaultProperties.items():
            if attr not in kwargs:
                self.__setattr__(attr, value)
        
RegisterObjectType(LocalDeviceObject)

class EventEnrollmentObject(Object):
    objectType = 'event-enrollment'
    properties = []

RegisterObjectType(EventEnrollmentObject)

class FileObject(Object):
    objectType = 'file'
    properties = []

RegisterObjectType(FileObject)

class GroupObject(Object):
    objectType = 'group'
    properties = []

RegisterObjectType(GroupObject)

class LoopObject(Object):
    objectType = 'loop'
    properties = []

RegisterObjectType(LoopObject)

class MultiStateInputObject(Object):
    objectType = 'multi-state-input'
    properties = []

RegisterObjectType(MultiStateInputObject)

class MultiStateOutputObject(Object):
    objectType = 'multi-state-output'
    properties = []

RegisterObjectType(MultiStateOutputObject)

class NotificationClassObject(Object):
    objectType = 'notification-class'
    properties = []

RegisterObjectType(NotificationClassObject)

class ProgramObject(Object):
    objectType = 'program'
    properties = []

RegisterObjectType(ProgramObject)

class ScheduleObject(Object):
    objectType = 'schedule'
    properties = []

RegisterObjectType(ScheduleObject)

class AveragingObject(Object):
    objectType = 'averaging'
    properties = []

RegisterObjectType(AveragingObject)

class MultiStateValueObject(Object):
    objectType = 'multi-state-value'
    properties = []

RegisterObjectType(MultiStateValueObject)

class TrendLogObject(Object):
    objectType = 'trend-log'
    properties = []

RegisterObjectType(TrendLogObject)

class LifeSafetyPointObject(Object):
    objectType = 'life-safety-point'
    properties = []

RegisterObjectType(LifeSafetyPointObject)

class LifeSafetyZoneObject(Object):
    objectType = 'life-safety-zone'
    properties = []

RegisterObjectType(LifeSafetyZoneObject)

class AccumulatorObject(Object):
    objectType = 'accumulator'
    properties = []

RegisterObjectType(AccumulatorObject)

class PulseConverterObject(Object):
    objectType = 'pulse-converter'
    properties = []

RegisterObjectType(PulseConverterObject)

