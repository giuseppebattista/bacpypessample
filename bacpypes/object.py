#!/usr/bin/python

"""
Object
"""

import sys
import re
import types

from errors import ConfigurationError
from debugging import function_debugging, ModuleLogger, Logging

from primitivedata import *
from constructeddata import *
from basetypes import *

# some debugging
_debug = 0
_log = ModuleLogger(globals())

#
#   PropertyError
#

class PropertyError(AttributeError):
    pass
    
#
#   map_name
#
#   Given a Python identifier, return the property identifier.
#

map_name_re = re.compile('[a-z][A-Z]')

def map_fn(m):
    pair = m.group()
    return pair[0] + "-" + pair[1].lower()
    
def map_name(name):
    return map_name_re.sub(map_fn, name)

# a dictionary of object types and classes
object_types = {}

#
#   register_object_type
#

@function_debugging
def register_object_type(klass):
    if _debug: register_object_type._debug("register_object_type %s", repr(klass))

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
    object_types[klass.objectType] = klass

#
#   get_object_class
#

def get_object_class(objectType):
    """Return the class associated with an object type."""
    return object_types.get(objectType)
    
#
#   get_datatype
#

@function_debugging
def get_datatype(objectType, property):
    """Return the datatype for the property of an object."""
    if _debug: get_datatype._debug("get_datatype %r %r", objectType, property)

    # get the related class
    cls = object_types.get(objectType)
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

class Property(Logging):

    def __init__(self, identifier, datatype, default=None, optional=True, mutable=True):
        if _debug:
            Property._debug("__init__ %s %s default=%r optional=%r mutable=%r",
                identifier, datatype, default, optional, mutable
                )

        # validate the identifier to be one of the Property enumerations
        if identifier not in BACnetPropertyIdentifier.enumerations:
            raise ConfigurationError, "unknown property identifier: %s" % (identifier,)

        self.identifier = identifier
        self.datatype = datatype
        self.optional = optional
        self.mutable = mutable
        self.default = default

    def ReadProperty(self, obj, arrayIndex=None):
        if _debug:
            Property._debug("ReadProperty(%s) %s arrayIndex=%r",
                self.identifier, obj, arrayIndex
                )

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
            Property._debug("WriteProperty(%s) %s %r arrayIndex=%r priority=%r",
                self.identifier, obj, value, arrayIndex, priority
                )

        # see if it must be provided
        if not self.optional and value is None:
            raise ValueError, "%s value required" % (self.identifier,)
            
        # see if it can be changed
        if not self.mutable:
            raise RuntimeError, "%s immutable property" % (self.identifier,)

        # if it's atomic assume correct datatype
        if issubclass(self.datatype, Atomic):
            if _debug: Property._debug("    - property is atomic, assumed correct type")
        elif isinstance(value, self.datatype):
            if _debug: Property._debug("    - correct type")
        elif arrayIndex is not None:
            if not issubclass(self.datatype, Array):
                raise TypeError, "%s is not an array" % (self.identifier,)
                
            # check the array
            arry = obj._values[self.identifier]
            if arry is None:
                raise ValueError, "%s uninitialized array" % (self.identifier,)
                
            # seems to be OK, let the array object take over
            if _debug: Property._debug("    - forwarding to array")
            arry[arrayIndex] = value
            
            return
        else:
            # coerce the value
            value = self.datatype(value)
            if _debug: Property._debug("    - coerced the value: %r", value)

        # seems to be OK
        obj._values[self.identifier] = value

#
#   ObjectIdentifierProperty
#

class ObjectIdentifierProperty(Property, Logging):

    def WriteProperty(self, obj, value, arrayIndex=None, priority=None):
        if _debug: ObjectIdentifierProperty._debug("WriteProperty %r %r arrayIndex=%r priority=%r", obj, value, arrayIndex, priority)
            
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
        now.now()
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
        now.now()
        return now.value
                
    def WriteProperty(self, obj, value, arrayIndex=None, priority=None):
        raise RuntimeError, "%s immutable property" % (self.identifier,)
    
#
#   Object
#

class Object(Logging):

    properties = \
        [ ObjectIdentifierProperty('object-identifier', ObjectIdentifier, optional=False)
        , Property('object-name', CharacterString, optional=False)
        , Property('description', CharacterString, default='')
        ]
    _properties = {}

    def __init__(self, **kwargs):
        """Create an object, with default property values as needed."""
        if _debug: Object._debug("__init__ %r", kwargs)

        # map the python names into property names and make sure they 
        # are appropriate for this object
        initargs = {}
        for key, value in kwargs.items():
            pname = map_name(key)
            if pname not in self._properties:
                if _debug: Object._debug("    - not a property: %r", pname)
                raise PropertyError, pname
            initargs[pname] = value

        # start with a clean dict of values
        self._values = {}

        # initialize the object
        for prop in self._properties.values():
            propid = prop.identifier

            if initargs.has_key(propid):
                if _debug: Object._debug("    - setting %s from initargs", propid)

                # defer to the property object for error checking
                prop.WriteProperty(self, initargs[propid])
            elif prop.default is not None:
                if _debug: Object._debug("    - setting %s from default", propid)

                # default values bypass property interface
                self._values[propid] = prop.default
            elif not prop.optional:
                if _debug: Object._debug("    - property %s value required", propid)

                raise PropertyError, "%s required" % (propid,)
            else:
                self._values[propid] = None

        if _debug: Object._debug("    - done __init__")

    def _attr_to_property(self, attr):
        """Common routine to translate a python attribute name to a property name and 
        return the appropriate property."""

        # get the property
        property = map_name(attr)
        prop = self._properties.get(property)
        if not prop:
            raise PropertyError, property

        # found it
        return prop

    def __getattr__(self, attr):
        if _debug: Object._debug("__getattr__ %r", attr)

        # do not redirect private attrs or functions
        if attr.startswith('_') or attr[0].isupper() or (attr == 'debug_contents'):
            return object.__getattribute__(self, attr)

        # defer to the property to get the value
        prop = self._attr_to_property(attr)
        if _debug: Object._debug("    - deferring to %r", prop)

        # defer to the property to get the value
        return prop.ReadProperty(self)

    def __setattr__(self, attr, value):
        if _debug: Object._debug("__setattr__ %r %r", attr, value)

        if attr.startswith('_') or attr[0].isupper() or (attr == 'debug_contents'):
            if _debug: Object._debug("    - special")
            return object.__setattr__(self, attr, value)

        # defer to the property to get the value
        prop = self._attr_to_property(attr)
        if _debug: Object._debug("    - deferring to %r", prop)

        return prop.WriteProperty(self, value)

    def ReadProperty(self, property, arrayIndex=None):
        if _debug: Object._debug("ReadProperty %r arrayIndex=%r", property, arrayIndex)

        # get the property
        prop = self._properties.get(property)
        if not prop:
            raise PropertyError, property

        # defer to the property to get the value
        return prop.ReadProperty(self, arrayIndex)

    def WriteProperty(self, property, value, arrayIndex=None, priority=None):
        if _debug: Object._debug("WriteProperty %r %r arrayIndex=%r priority=%r", property, value, arrayIndex, priority)

        # get the property
        prop = self._properties.get(property)
        if not prop:
            raise PropertyError, property

        # defer to the property to set the value
        return prop.WriteProperty(self, value, arrayIndex, priority)

    def get_datatype(self, property):
        """Return the datatype for the property of an object."""
        if _debug: Object._debug("get_datatype %r", property)

        # get the property
        prop = self._properties.get(property)
        if not prop:
            raise PropertyError, property

        # return the datatype
        return prop.datatype

    def debug_contents(self, indent=1, file=sys.stdout, _ids=None):
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
            if hasattr(value, "debug_contents"):
                file.write("%s%s\n" % ("    " * indent, prop.identifier))
                value.debug_contents(indent+1, file, _ids)
            else:
                file.write("%s%s = %r\n" % ("    " * indent, prop.identifier, value))

#
#   Standard Object Types
#

class BACnetAccumulatorRecord(Sequence):
    sequenceElements = \
        [ Element('timestamp', BACnetDateTime, 0)
        , Element('presentValue', Unsigned, 1)
        , Element('accumulatedValue', Unsigned, 2)
        , Element('accumulatorStatus', BACnetAccumulatorStatus, 3)
        ]

class AccumulatorObject(Object):
    objectType = 'accumulator'
    properties = \
        [ Property('present-value', Unsigned)
        , Property('description', CharacterString, optional=True)
        , Property('device-type', CharacterString, optional=True)
        , Property('status-flags', BACnetStatusFlags)
        , Property('event-state', BACnetEventState)
        , Property('reliability', BACnetReliability, optional=True)
        , Property('out-of-service', Boolean)
        , Property('scale', BACnetScale)
        , Property('units', BACnetEngineeringUnits)
        , Property('prescale', BACnetPrescale, optional=True)
        , Property('max-pres-value', Unsigned)
        , Property('value-change-time', BACnetDateTime, optional=True)
        , Property('value-before-change', Unsigned, optional=True)
        , Property('value-set', Unsigned, optional=True)
        , Property('logging-record', BACnetAccumulatorRecord, optional=True)
        , Property('logging-object', ObjectIdentifier, optional=True)
        , Property('pulse-rate', Unsigned, optional=True)
        , Property('high-limit', Unsigned, optional=True)
        , Property('low-limit', Unsigned, optional=True)
        , Property('limit-monitoring-interval', Unsigned, optional=True)
        , Property('notification-class', Unsigned, optional=True)
        , Property('time-delay', Unsigned, optional=True)
        , Property('limit-enable', BACnetLimitEnable, optional=True)
        , Property('event-enable', BACnetEventTransitionBits, optional=True)
        , Property('acked-transitions', BACnetEventTransitionBits, optional=True)
        , Property('notify-type', BACnetNotifyType, optional=True)
        , Property('event-time-stamps', SequenceOf(BACnetTimeStamp), optional=True)
        , Property('profile-name', CharacterString, optional=True)
        ]

register_object_type(AccumulatorObject)

class AnalogInputObject(Object):
    objectType = 'analog-input'
    properties = \
        [ Property('present-value', Real)
        , Property('status-flags', BACnetStatusFlags)
        , Property('event-state', BACnetEventState)
        , Property('out-of-service', Boolean)
        ]

register_object_type(AnalogInputObject)

class AnalogOutputObject(Object):
    objectType = 'analog-output'
    properties = \
        [ Property('present-value', Real)
        , Property('status-flags', BACnetStatusFlags)
        , Property('event-state', BACnetEventState)
        , Property('out-of-service', Boolean)
        ]

register_object_type(AnalogOutputObject)

class AnalogValueObject(Object):
    objectType = 'analog-value'
    properties = \
        [ Property('present-value', Real)
        , Property('status-flags', BACnetStatusFlags)
        , Property('event-state', BACnetEventState)
        , Property('out-of-service', Boolean)
        ]

register_object_type(AnalogValueObject)

class BinaryInputObject(Object):
    objectType = 'binary-input'
    properties = \
        [ Property('present-value', BACnetBinaryPV)
        , Property('status-flags', BACnetStatusFlags)
        , Property('event-state', BACnetEventState)
        , Property('out-of-service', Boolean)
        ]

register_object_type(BinaryInputObject)

class BinaryOutputObject(Object):
    objectType = 'binary-output'
    properties = \
        [ Property('present-value', BACnetBinaryPV)
        , Property('status-flags', BACnetStatusFlags)
        , Property('event-state', BACnetEventState)
        , Property('out-of-service', Boolean)
        ]

register_object_type(BinaryOutputObject)

class BinaryValueObject(Object):
    objectType = 'binary-value'
    properties = \
        [ Property('present-value', BACnetBinaryPV)
        , Property('status-flags', BACnetStatusFlags)
        , Property('event-state', BACnetEventState)
        , Property('out-of-service', Boolean)
        ]

register_object_type(BinaryValueObject)

class CalendarObject(Object):
    objectType = 'calendar'
    properties = []

register_object_type(CalendarObject)

class CommandObject(Object):
    objectType = 'command'
    properties = []

register_object_type(CommandObject)

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

register_object_type(DeviceObject)

class LocalDeviceObject(DeviceObject, Logging):
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
        if _debug: LocalDeviceObject._debug("__init__ %r", kwargs)

        # default args
        default_args = {}

        # update with defaults
        default_args.update(LocalDeviceObject.defaultProperties)

        # update with the kwargs
        default_args.update(kwargs)

        # if an object list hasn't been provided, build one
        if 'objectList' not in default_args:
            # create an object identifier list with itself in it
            objectList = ArrayOf(ObjectIdentifier)([kwargs['objectIdentifier']])
            if _debug: LocalDeviceObject._debug("    - objectList: %r", objectList)

            default_args['objectList'] = objectList

        # proceed with initializtion
        DeviceObject.__init__(self, **default_args)

register_object_type(LocalDeviceObject)

class EventEnrollmentObject(Object):
    objectType = 'event-enrollment'
    properties = []

register_object_type(EventEnrollmentObject)

class FileObject(Object):
    objectType = 'file'
    properties = []

register_object_type(FileObject)

class GroupObject(Object):
    objectType = 'group'
    properties = []

register_object_type(GroupObject)

class LifeSafetyPointObject(Object):
    objectType = 'life-safety-point'
    properties = []

register_object_type(LifeSafetyPointObject)

class LifeSafetyZoneObject(Object):
    objectType = 'life-safety-zone'
    properties = []

register_object_type(LifeSafetyZoneObject)

class LoopObject(Object):
    objectType = 'loop'
    properties = []

register_object_type(LoopObject)

class MultiStateInputObject(Object):
    objectType = 'multi-state-input'
    properties = []

register_object_type(MultiStateInputObject)

class MultiStateOutputObject(Object):
    objectType = 'multi-state-output'
    properties = []

register_object_type(MultiStateOutputObject)

class MultiStateValueObject(Object):
    objectType = 'multi-state-value'
    properties = []

register_object_type(MultiStateValueObject)

class NotificationClassObject(Object):
    objectType = 'notification-class'
    properties = []

register_object_type(NotificationClassObject)

class ProgramObject(Object):
    objectType = 'program'
    properties = []

register_object_type(ProgramObject)

class PulseConverterObject(Object):
    objectType = 'pulse-converter'
    properties = []

register_object_type(PulseConverterObject)

class ScheduleObject(Object):
    objectType = 'schedule'
    properties = []

register_object_type(ScheduleObject)

class StructuredViewObject(Object):
    objectType = 'structured-view'
    properties = \
        [ Property('node-type', BACnetNodeType)
        , Property('node-subtype', CharacterString)
        , Property('subordinate-list', ArrayOf(BACnetDeviceObjectReference))
        , Property('subordinate-annotations', ArrayOf(CharacterString), optional=True)
        , Property('profile-name', CharacterString, optional=True)
        ]

register_object_type(StructuredViewObject)

class TrendLogObject(Object):
    objectType = 'trend-log'
    properties = []

register_object_type(TrendLogObject)

