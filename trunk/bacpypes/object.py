#!/usr/bin/python

"""
Object
"""

import sys
import types

from errors import ConfigurationError
from debugging import function_debugging, ModuleLogger, Logging

from primitivedata import *
from constructeddata import *
from basetypes import *
from apdu import Error, EventNotificationParameters, ReadAccessSpecification, ReadAccessResult

# some debugging
_debug = 0
_log = ModuleLogger(globals())

#
#   PropertyError
#

class PropertyError(AttributeError):
    pass

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
    if 'objectType' not in _properties:
        _properties['objectType'] = Property('objectType', ObjectType, klass.objectType, mutable=False)

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

        # keep the arguments
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
                raise ExecutionError(errorClass='property', errorCode='propertyIsNotAnArray')

            if value:
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
                raise ExecutionError(errorClass='property', errorCode='propertyIsNotAnArray')

            # check the array
            arry = obj._values[self.identifier]
            if arry is None:
                raise RuntimeError, "%s uninitialized array" % (self.identifier,)

            # seems to be OK, let the array object take over
            if _debug: Property._debug("    - forwarding to array")
            arry[arrayIndex] = value

            return
        elif value is not None:
            # coerce the value
            value = self.datatype(value)
            if _debug: Property._debug("    - coerced the value: %r", value)

        # seems to be OK
        obj._values[self.identifier] = value

#
#   StandardProperty
#

class StandardProperty(Property, Logging):

    def __init__(self, identifier, datatype, default=None, optional=True, mutable=True):
        if _debug:
            StandardProperty._debug("__init__ %s %s default=%r optional=%r mutable=%r",
                identifier, datatype, default, optional, mutable
                )

        # use one of the subclasses
        if not isinstance(self, (OptionalProperty, ReadableProperty, WritableProperty)):
            raise ConfigurationError, self.__class__.__name__ + " must derive from OptionalProperty, ReadableProperty, or WritableProperty"

        # validate the identifier to be one of the standard property enumerations
        if identifier not in PropertyIdentifier.enumerations:
            raise ConfigurationError, "unknown standard property identifier: %s" % (identifier,)

        # continue with the initialization
        Property.__init__(self, identifier, datatype, default, optional, mutable)

#
#   OptionalProperty
#

class OptionalProperty(StandardProperty, Logging):

    """The property is required to be present and readable using BACnet services."""

    def __init__(self, identifier, datatype, default=None, optional=True, mutable=False):
        if _debug:
            OptionalProperty._debug("__init__ %s %s default=%r optional=%r mutable=%r",
                identifier, datatype, default, optional, mutable
                )

        # continue with the initialization
        StandardProperty.__init__(self, identifier, datatype, default, optional, mutable)

#
#   ReadableProperty
#

class ReadableProperty(StandardProperty, Logging):

    """The property is required to be present and readable using BACnet services."""

    def __init__(self, identifier, datatype, default=None, optional=False, mutable=False):
        if _debug:
            ReadableProperty._debug("__init__ %s %s default=%r optional=%r mutable=%r",
                identifier, datatype, default, optional, mutable
                )

        # continue with the initialization
        StandardProperty.__init__(self, identifier, datatype, default, optional, mutable)

#
#   WritableProperty
#

class WritableProperty(StandardProperty, Logging):

    """The property is required to be present, readable, and writable using BACnet services."""

    def __init__(self, identifier, datatype, default=None, optional=False, mutable=True):
        if _debug:
            ReadableProperty._debug("__init__ %s %s default=%r optional=%r mutable=%r",
                identifier, datatype, default, optional, mutable
                )

        # continue with the initialization
        StandardProperty.__init__(self, identifier, datatype, default, optional, mutable)

#
#   ObjectIdentifierProperty
#

class ObjectIdentifierProperty(ReadableProperty, Logging):

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
#   Object
#

class Object(Logging):

    properties = \
        [ ObjectIdentifierProperty('objectIdentifier', ObjectIdentifier, optional=False)
        , ReadableProperty('objectName', CharacterString, optional=False)
        , ReadableProperty('description', CharacterString, default='')
        , OptionalProperty('profileName', CharacterString)
        , ReadableProperty('propertyList', ArrayOf(PropertyIdentifier))
        ]
    _properties = {}

    def __init__(self, **kwargs):
        """Create an object, with default property values as needed."""
        if _debug: Object._debug("__init__ %r", kwargs)

        # map the python names into property names and make sure they 
        # are appropriate for this object
        initargs = {}
        for key, value in kwargs.items():
            if key not in self._properties:
                raise PropertyError, key
            initargs[key] = value

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

            else:
                if not prop.optional:
                    if _debug: Object._warning("    - property %s value required", propid)

                self._values[propid] = None

        if _debug: Object._debug("    - done __init__")

    def _attr_to_property(self, attr):
        """Common routine to translate a python attribute name to a property name and 
        return the appropriate property."""

        # get the property
        prop = self._properties.get(attr)
        if not prop:
            raise PropertyError, attr

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

class AccessCredentialObject(Object):
    objectType = 'accessCredential'
    properties = \
        [ WritableProperty('globalIdentifier', Unsigned)
        , ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('reliability', Reliability)
        , ReadableProperty('credentialStatus', BinaryPV)
        , ReadableProperty('reasonForDisable', SequenceOf(AccessCredentialDisableReason))
        , ReadableProperty('authenticationFactors', ArrayOf(CredentialAuthenticationFactor))
        , ReadableProperty('activationTime', DateTime)
        , ReadableProperty('expiryTime', DateTime)
        , ReadableProperty('credentialDisable', AccessCredentialDisable)
        , OptionalProperty('daysRemaining', Integer)
        , OptionalProperty('usesRemaining', Integer)
        , OptionalProperty('absenteeLimit', Unsigned)
        , OptionalProperty('belongsTo', DeviceObjectReference)
        , ReadableProperty('assignedAccessRights', ArrayOf(AssignedAccessRights))
        , OptionalProperty('lastAccessPoint', DeviceObjectReference)
        , OptionalProperty('lastAccessEvent', AccessEvent)
        , OptionalProperty('lastUseTime', DateTime)
        , OptionalProperty('traceFlag', Boolean)
        , OptionalProperty('threatAuthority', AccessThreatLevel)
        , OptionalProperty('extendedTimeEnable', Boolean)
        , OptionalProperty('masterExemption', Boolean)
        , OptionalProperty('passbackExemption', Boolean)
        , OptionalProperty('occupancyExemption', Boolean)
        ]

register_object_type(AccessCredentialObject)

class AccessDoorObject(Object):
    objectType = 'accessDoor'
    properties = \
        [ WritableProperty('presentValue', DoorValue)
        , ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('eventState', EventState)
        , ReadableProperty('reliability', Reliability)
        , ReadableProperty('outOfService', Boolean)
        , ReadableProperty('priorityArray', PriorityArray)
        , ReadableProperty('relinquishDefault', DoorValue)
        , OptionalProperty('doorStatus', DoorStatus)
        , OptionalProperty('lockStatus', LockStatus)
        , OptionalProperty('securedStatus', DoorSecuredStatus)
        , OptionalProperty('doorMembers', ArrayOf(DeviceObjectReference))
        , ReadableProperty('doorPulseTime', Unsigned)
        , ReadableProperty('doorExtendedPulseTime', Unsigned)
        , OptionalProperty('doorUnlockDelayTime', Unsigned)
        , ReadableProperty('doorOpenTooLongTime', Unsigned)
        , OptionalProperty('doorAlarmState', DoorAlarmState)
        , OptionalProperty('maskedAlarmValues', SequenceOf(DoorAlarmState))
        , OptionalProperty('maintenanceRequired', Maintenance)
        , OptionalProperty('timeDelay', Unsigned)
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('alarmValues', SequenceOf(DoorAlarmState))
        , OptionalProperty('faultValues', SequenceOf(DoorAlarmState))
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        ]

register_object_type(AccessDoorObject)

class AccessPointObject(Object):
    objectType = 'accessPoint'
    properties = \
        [ ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('eventState', EventState)
        , ReadableProperty('reliability', Reliability)
        , ReadableProperty('outOfService', Boolean)
        , ReadableProperty('authenticationStatus', AuthenticationStatus)
        , ReadableProperty('activeAuthenticationPolicy', Unsigned)
        , ReadableProperty('numberOfAuthenticationPolicies', Unsigned)
        , OptionalProperty('authenticationPolicyList', ArrayOf(AuthenticationPolicy))
        , OptionalProperty('authenticationPolicyNames', ArrayOf(CharacterString))
        , ReadableProperty('authorizationMode', AuthorizationMode)
        , OptionalProperty('verificationTime', Unsigned)
        , OptionalProperty('lockout', Boolean)
        , OptionalProperty('lockoutRelinquishTime', Unsigned)
        , OptionalProperty('failedAttempts', Unsigned)
        , OptionalProperty('failedAttemptEvents', SequenceOf(AccessEvent))
        , OptionalProperty('maxFailedAttempts', Unsigned)
        , OptionalProperty('failedAttemptsTime', Unsigned)
        , OptionalProperty('threatLevel', AccessThreatLevel)
        , OptionalProperty('occupancyUpperLimitEnforced', Boolean)
        , OptionalProperty('occupancyLowerLimitEnforced', Boolean)
        , OptionalProperty('occupancyCountAdjust', Boolean)
        , OptionalProperty('accompanimentTime', Unsigned)
        , ReadableProperty('accessEvent', AccessEvent)
        , ReadableProperty('accessEventTag', Unsigned)
        , ReadableProperty('accessEventTime', TimeStamp)
        , ReadableProperty('accessEventCredential', DeviceObjectReference)
        , OptionalProperty('accessEventAuthenticationFactor', AuthenticationFactor)
        , ReadableProperty('accessDoors', ArrayOf(DeviceObjectReference))
        , ReadableProperty('priorityForWriting', Unsigned)
        , OptionalProperty('musterPoint', Boolean)
        , OptionalProperty('zoneTo', DeviceObjectReference)
        , OptionalProperty('zoneFrom', DeviceObjectReference)
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('transactionNotificationClass', Unsigned)
        , OptionalProperty('accessAlarmEvents', SequenceOf(AccessEvent))
        , OptionalProperty('accessTransactionEvents', SequenceOf(AccessEvent))
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        ]

register_object_type(AccessPointObject)

class AccessRightsObject(Object):
    objectType = 'accessRights'
    properties = \
        [ WritableProperty('globalIdentifier', Unsigned)
        , ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('reliability', Reliability)
        , ReadableProperty('enable', Boolean)
        , ReadableProperty('negativeAccessRules', ArrayOf(AccessRule))
        , ReadableProperty('positiveAccessRules', ArrayOf(AccessRule))
        , OptionalProperty('accompaniment', DeviceObjectReference)
        ]

register_object_type(AccessRightsObject)

class AccessUserObject(Object):
    objectType = 'accessUser'
    properties = \
        [ WritableProperty('globalIdentifier', Unsigned)
        , ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('reliability', Reliability)
        , ReadableProperty('userType', AccessUserType)
        , OptionalProperty('userName', CharacterString)
        , OptionalProperty('userExternalIdentifier', CharacterString)
        , OptionalProperty('userInformationReference', CharacterString)
        , OptionalProperty('members', SequenceOf(DeviceObjectReference))
        , OptionalProperty('memberOf', SequenceOf(DeviceObjectReference))
        , ReadableProperty('credentials', SequenceOf(DeviceObjectReference))
       ]

register_object_type(AccessUserObject)

class AccessZoneObject(Object):
    objectType = 'accessZone'
    properties = \
        [ WritableProperty('globalIdentifier', Unsigned)
        , ReadableProperty('occupancyState', AccessZoneOccupancyState)
        , ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('eventState', EventState)
        , ReadableProperty('reliability', Reliability)
        , ReadableProperty('outOfService', Boolean)
        , OptionalProperty('occupancyCount', Unsigned)
        , OptionalProperty('occupancyCountEnable', Boolean)
        , OptionalProperty('adjustValue', Integer)
        , OptionalProperty('occupancyUpperLimit', Unsigned)
        , OptionalProperty('occupancyLowerLimit', Unsigned)
        , OptionalProperty('credentialsInZone', SequenceOf(DeviceObjectReference) )
        , OptionalProperty('lastCredentialAdded', DeviceObjectReference)
        , OptionalProperty('lastCredentialAddedTime', DateTime)
        , OptionalProperty('lastCredentialRemoved', DeviceObjectReference)
        , OptionalProperty('lastCredentialRemovedTime', DateTime)
        , OptionalProperty('passbackMode', AccessPassbackMode)
        , OptionalProperty('passbackTimeout', Unsigned)
        , ReadableProperty('entryPoints', SequenceOf(DeviceObjectReference))
        , ReadableProperty('exitPoints', SequenceOf(DeviceObjectReference))
        , OptionalProperty('timeDelay', Unsigned)
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('alarmValues', SequenceOf(AccessZoneOccupancyState))
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        ]

register_object_type(AccessZoneObject)

class AccumulatorObject(Object):
    objectType = 'accumulator'
    properties = \
        [ ReadableProperty('presentValue', Unsigned)
        , OptionalProperty('deviceType', CharacterString)
        , ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , ReadableProperty('outOfService', Boolean)
        , ReadableProperty('scale', Scale)
        , ReadableProperty('units', EngineeringUnits)
        , OptionalProperty('prescale', Prescale)
        , ReadableProperty('maxPresValue', Unsigned)
        , OptionalProperty('valueChangeTime', DateTime)
        , OptionalProperty('valueBeforeChange', Unsigned)
        , OptionalProperty('valueSet', Unsigned)
        , OptionalProperty('loggingRecord', AccumulatorRecord)
        , OptionalProperty('loggingObject', ObjectIdentifier)
        , OptionalProperty('pulseRate', Unsigned)
        , OptionalProperty('highLimit', Unsigned)
        , OptionalProperty('lowLimit', Unsigned)
        , OptionalProperty('limitMonitoringInterval', Unsigned)
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('timeDelay', Unsigned)
        , OptionalProperty('limitEnable', LimitEnable)
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', SequenceOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', SequenceOf(CharacterString))
        ]

register_object_type(AccumulatorObject)

class AnalogInputObject(Object):
    objectType = 'analogInput'
    properties = \
        [ ReadableProperty('presentValue', Real)
        , OptionalProperty('deviceType', CharacterString)
        , ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , ReadableProperty('outOfService', Boolean)
        , OptionalProperty('updateInterval', Unsigned)
        , ReadableProperty('units', EngineeringUnits)
        , OptionalProperty('minPresValue', Real)
        , OptionalProperty('maxPresValue', Real)
        , OptionalProperty('resolution', Real)
        , OptionalProperty('covIncrement', Real)
        , OptionalProperty('timeDelay', Unsigned)
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('highLimit', Real)
        , OptionalProperty('lowLimit', Real)
        , OptionalProperty('deadband', Real)
        , OptionalProperty('limitEnable', LimitEnable)
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        ]

register_object_type(AnalogInputObject)

class AnalogOutputObject(Object):
    objectType = 'analogOutput'
    properties = \
        [ WritableProperty('presentValue', Real)
        , OptionalProperty('deviceType', CharacterString)
        , ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , ReadableProperty('outOfService', Boolean)
        , ReadableProperty('units',  EngineeringUnits)
        , OptionalProperty('minPresValue', Real)
        , OptionalProperty('maxPresValue', Real)
        , OptionalProperty('resolution', Real)
        , ReadableProperty('priorityArray', PriorityArray)
        , ReadableProperty('relinquishDefault', Real)
        , OptionalProperty('covIncrement', Real)
        , OptionalProperty('timeDelay', Unsigned)
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('highLimit', Real)
        , OptionalProperty('lowLimit', Real)
        , OptionalProperty('deadband', Real)
        , OptionalProperty('limitEnable', LimitEnable)
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions',  EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        ]

register_object_type(AnalogOutputObject)

class AnalogValueObject(Object):
    objectType = 'analogValue'
    properties = \
        [ ReadableProperty('presentValue', Real)
        , ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , ReadableProperty('outOfService', Boolean)
        , ReadableProperty('units', EngineeringUnits)
        , OptionalProperty('minPresValue', Real)
        , OptionalProperty('maxPresValue', Real)
        , OptionalProperty('resolution', Real)
        , OptionalProperty('priorityArray', PriorityArray)
        , OptionalProperty('relinquishDefault', Real)
        , OptionalProperty('covIncrement', Real)
        , OptionalProperty('timeDelay', Unsigned)
        , OptionalProperty('notificationClass',  Unsigned)
        , OptionalProperty('highLimit', Real)
        , OptionalProperty('lowLimit', Real)
        , OptionalProperty('deadband', Real)
        , OptionalProperty('limitEnable', LimitEnable)
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        ]

register_object_type(AnalogValueObject)

class AveragingObject(Object):
    objectType = 'averaging'
    properties = \
        [ ReadableProperty('minimumValue', Real)
        , OptionalProperty('minimumValueTimestamp', DateTime)
        , ReadableProperty('averageValue', Real)
        , OptionalProperty('varianceValue', Real)
        , ReadableProperty('maximumValue', Real)
        , OptionalProperty('maximumValueTimestamp', DateTime)
        , WritableProperty('attemptedSamples', Unsigned)
        , ReadableProperty('validSamples', Unsigned)
        , ReadableProperty('objectPropertyReference', DeviceObjectPropertyReference)
        , WritableProperty('windowInterval', Unsigned)
        , WritableProperty('windowSamples', Unsigned)
        ]
 
register_object_type(AveragingObject)

class BinaryInputObject(Object):
    objectType = 'binaryInput'
    properties = \
        [ ReadableProperty('presentValue', BinaryPV)
        , OptionalProperty('deviceType', CharacterString)
        , ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , ReadableProperty('outOfService', Boolean)
        , ReadableProperty('polarity', Polarity)
        , OptionalProperty('inactiveText', CharacterString)
        , OptionalProperty('activeText', CharacterString)
        , OptionalProperty('changeOfStateTime', DateTime)
        , OptionalProperty('changeOfStateCount', Unsigned)
        , OptionalProperty('timeOfStateCountReset', DateTime)
        , OptionalProperty('elapsedActiveTime', Unsigned)
        , OptionalProperty('timeOfActiveTimeReset', DateTime)
        , OptionalProperty('timeDelay', Unsigned)
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('alarmValue', BinaryPV)
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))        
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        ]

register_object_type(BinaryInputObject)

class BinaryOutputObject(Object):
    objectType = 'binaryOutput'
    properties = \
        [ WritableProperty('presentValue', BinaryPV)
        , OptionalProperty('deviceType', CharacterString)
        , ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , ReadableProperty('outOfService', Boolean)
        , ReadableProperty('polarity', Polarity)
        , OptionalProperty('inactiveText', CharacterString)
        , OptionalProperty('activeText', CharacterString)
        , OptionalProperty('changeOfStateTime', DateTime)
        , OptionalProperty('changeOfStateCount', Unsigned)
        , OptionalProperty('timeOfStateCountReset', DateTime)
        , OptionalProperty('elapsedActiveTime', Unsigned)
        , OptionalProperty('timeOfActiveTimeReset', DateTime)
        , OptionalProperty('minimumOffTime', Unsigned)
        , OptionalProperty('minimumOnTime', Unsigned)
        , ReadableProperty('priorityArray', PriorityArray)
        , ReadableProperty('relinquishDefault', BinaryPV)
        , OptionalProperty('timeDelay', Unsigned)
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('feedbackValue', BinaryPV)
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        ]

register_object_type(BinaryOutputObject)

class BinaryValueObject(Object):
    objectType = 'binaryValue'
    properties = \
        [ WritableProperty('presentValue', BinaryPV)
        , ReadableProperty('statusFlags',StatusFlags)
        , ReadableProperty('eventState',EventState)
        , OptionalProperty('reliability',Reliability)
        , ReadableProperty('outOfService',Boolean)
        , OptionalProperty('inactiveText',CharacterString)
        , OptionalProperty('activeText',CharacterString)
        , OptionalProperty('changeOfStateTime',DateTime)
        , OptionalProperty('changeOfStateCount',Unsigned)
        , OptionalProperty('timeOfStateCountReset',DateTime)
        , OptionalProperty('elapsedActiveTime',Unsigned)
        , OptionalProperty('timeOfActiveTimeReset',DateTime)
        , OptionalProperty('minimumOffTime',Unsigned)
        , OptionalProperty('minimumOnTime',Unsigned)
        , OptionalProperty('priorityArray',PriorityArray)
        , OptionalProperty('relinquishDefault',BinaryPV)
        , OptionalProperty('timeDelay',Unsigned)
        , OptionalProperty('notificationClass',Unsigned)
        , OptionalProperty('alarmValue',BinaryPV)
        , OptionalProperty('eventEnable',EventTransitionBits)
        , OptionalProperty('ackedTransitions',EventTransitionBits)
        , OptionalProperty('notifyType',NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        ]

register_object_type(BinaryValueObject)

class BitStringValueObject(Object):
    objectType = 'bitstringValue'
    properties = \
        [ ReadableProperty('presentValue', BitString)
        , OptionalProperty('bitText', ArrayOf(CharacterString))
        , ReadableProperty('statusFlags', StatusFlags)
        , OptionalProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , OptionalProperty('outOfService', Boolean)
        , OptionalProperty('priorityArray', PriorityArray)
        , OptionalProperty('relinquishDefault', BitString)
        , OptionalProperty('timeDelay', Unsigned)
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('alarmValues', ArrayOf(BitString))
        , OptionalProperty('bitMask', BitString)
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        ]

register_object_type(BitStringValueObject)

class CalendarObject(Object):
    objectType = 'calendar'
    properties = \
        [ ReadableProperty('presentValue', Boolean)
        , ReadableProperty('dateList', SequenceOf(CalendarEntry)) 
        ]

register_object_type(CalendarObject)

class CharacterStringValueObject(Object):
    objectType = 'characterStringValue'
    properties = \
        [ ReadableProperty('presentValue', CharacterString)
        , ReadableProperty('statusFlags', StatusFlags)
        , OptionalProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , OptionalProperty('outOfService', Boolean)
        , OptionalProperty('priorityArray', PriorityArray)
        , OptionalProperty('relinquishDefault', CharacterString)
        , OptionalProperty('timeDelay', Unsigned)
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('alarmValues', ArrayOf(OptionalCharacterString))
        , OptionalProperty('faultValues', ArrayOf(OptionalCharacterString))
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        ]

register_object_type(CharacterStringValueObject)

class CommandObject(Object):
    objectType = 'command'
    properties = \
        [ WritableProperty('presentValue', Unsigned)
        , ReadableProperty('inProcess', Boolean)
        , ReadableProperty('allWritesSuccessful', Boolean)
        , ReadableProperty('action', ArrayOf(ActionList))
        , OptionalProperty('actionText', ArrayOf(CharacterString))
        ]

register_object_type(CommandObject)

class CredentialDataInputObject(Object):
    objectType = 'credentialDataInput'
    properties = \
        [ ReadableProperty('presentValue', AuthenticationFactor)
        , ReadableProperty('statusFlags', StatusFlags)
        , OptionalProperty('reliability', Reliability)
        , ReadableProperty('outOfService', Boolean)
        , ReadableProperty('supportedFormats', ArrayOf(AuthenticationFactorFormat))
        , ReadableProperty('supportedFormatClasses', ArrayOf(Unsigned))
        ]

register_object_type(CredentialDataInputObject)

class DatePatternValueObject(Object):
    objectType = 'datePatternValue'
    properties = \
        [ ReadableProperty('presentValue', Date)
        , ReadableProperty('statusFlags', StatusFlags)
        , OptionalProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , OptionalProperty('outOfService', Boolean)
        , OptionalProperty('priorityArray', PriorityArray)
        , OptionalProperty('relinquishDefault', DateTime)
        ]

register_object_type(DatePatternValueObject)

class DateValueObject(Object):
    objectType = 'dateValue'
    properties = \
        [ ReadableProperty('presentValue', Date)
        , ReadableProperty('statusFlags', StatusFlags)
        , OptionalProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , OptionalProperty('outOfService', Boolean)
        , OptionalProperty('priorityArray', PriorityArray)
        , OptionalProperty('relinquishDefault', Date)
        ]

register_object_type(DateValueObject)

class DateTimePatternValueObject(Object):
    objectType = 'datetimePatternValue'
    properties = \
        [ ReadableProperty('presentValue', DateTime)
        , ReadableProperty('statusFlags', StatusFlags)
        , OptionalProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , OptionalProperty('outOfService', Boolean)
        , OptionalProperty('priorityArray', PriorityArray)
        , OptionalProperty('relinquishDefault', DateTime)
        , OptionalProperty('isUtc', Boolean)
        ]

register_object_type(DateTimePatternValueObject)

class DateTimeValueObject(Object):
    objectType = 'datetimeValue'
    properties = \
        [ ReadableProperty('presentValue', DateTime)
        , ReadableProperty('statusFlags', StatusFlags)
        , OptionalProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , OptionalProperty('outOfService', Boolean)
        , OptionalProperty('priorityArray', PriorityArray)
        , OptionalProperty('relinquishDefault', DateTime)
        , OptionalProperty('isUtc', Boolean)
        ]

register_object_type(DateTimeValueObject)

class DeviceObject(Object):
    objectType = 'device'
    properties = \
        [ ReadableProperty('systemStatus', DeviceStatus)
        , ReadableProperty('vendorName', CharacterString)
        , ReadableProperty('vendorIdentifier', Unsigned)
        , ReadableProperty('modelName', CharacterString)
        , ReadableProperty('firmwareRevision', CharacterString)
        , ReadableProperty('applicationSoftwareVersion', CharacterString)
        , OptionalProperty('location', CharacterString)
        , ReadableProperty('protocolVersion', Unsigned)
        , ReadableProperty('protocolRevision', Unsigned)
        , ReadableProperty('protocolServicesSupported', ServicesSupported)
        , ReadableProperty('protocolObjectTypesSupported', ObjectTypesSupported)
        , ReadableProperty('objectList', ArrayOf(ObjectIdentifier))
        , OptionalProperty('structuredObjectList', ArrayOf(ObjectIdentifier))
        , ReadableProperty('maxApduLengthAccepted', Unsigned)
        , ReadableProperty('segmentationSupported', Segmentation)
        , OptionalProperty('vtClassesSupported', SequenceOf(VTClass))
        , OptionalProperty('activeVtSessions', SequenceOf(VTSession))
        , OptionalProperty('localTime', Time)
        , OptionalProperty('localDate', Date)
        , OptionalProperty('utcOffset', Integer)
        , OptionalProperty('daylightSavingsStatus', Boolean)
        , OptionalProperty('apduSegmentTimeout', Unsigned)
        , ReadableProperty('apduTimeout', Unsigned)
        , ReadableProperty('numberOfApduRetries', Unsigned)
        , OptionalProperty('timeSynchronizationRecipients', SequenceOf(Recipient))
        , OptionalProperty('maxMaster', Unsigned)
        , OptionalProperty('maxInfoFrames', Unsigned)
        , ReadableProperty('deviceAddressBinding', SequenceOf(AddressBinding))
        , ReadableProperty('databaseRevision', Unsigned)
        , OptionalProperty('configurationFiles', ArrayOf(ObjectIdentifier))
        , OptionalProperty('lastRestoreTime', TimeStamp)
        , OptionalProperty('backupFailureTimeout', Unsigned)
        , OptionalProperty('backupPreparationTime', Unsigned)
        , OptionalProperty('restorePreparationTime', Unsigned)
        , OptionalProperty('restoreCompletionTime', Unsigned)
        , OptionalProperty('backupAndRestoreState', BackupState)
        , OptionalProperty('activeCovSubscriptions', SequenceOf(COVSubscription))
        , OptionalProperty('maxSegmentsAccepted', Unsigned)
        , OptionalProperty('slaveProxyEnable', ArrayOf(Boolean))
        , OptionalProperty('autoSlaveDiscovery', ArrayOf(Boolean))
        , OptionalProperty('slaveAddressBinding', SequenceOf(AddressBinding))
        , OptionalProperty('manualSlaveAddressBinding', SequenceOf(AddressBinding))
        , OptionalProperty('lastRestartReason', RestartReason)
        , OptionalProperty('timeOfDeviceRestart', TimeStamp)
        , OptionalProperty('restartNotificationRecipients', SequenceOf(Recipient))
        , OptionalProperty('utcTimeSynchronizationRecipients', SequenceOf(Recipient))
        , OptionalProperty('timeSynchronizationInterval', Unsigned)
        , OptionalProperty('alignIntervals', Boolean)
        , OptionalProperty('intervalOffset', Unsigned)
        ]

register_object_type(DeviceObject)

class EventEnrollmentObject(Object):
    objectType = 'eventEnrollment'
    properties = \
        [ ReadableProperty('eventType', EventType)
        , ReadableProperty('notifyType', NotifyType)
        , ReadableProperty('eventParameters', EventParameter)
        , ReadableProperty('objectPropertyReference', DeviceObjectPropertyReference)
        , ReadableProperty('eventState', EventState)
        , ReadableProperty('eventEnable', EventTransitionBits)
        , ReadableProperty('ackedTransitions', EventTransitionBits)
        , ReadableProperty('notificationClass', Unsigned)
        , ReadableProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        ]

register_object_type(EventEnrollmentObject)

#-----

class EventLogRecordLogDatum(Choice):
    choiceElements = \
        [ Element('logStatus', LogStatus, 0)
        , Element('notification', EventNotificationParameters, 1)
        , Element('timeChange', Real, 2)
        ]

class EventLogRecord(Sequence):
    sequenceElements = \
        [ Element('timestamp', DateTime, 0)
        , Element('logDatum', EventLogRecordLogDatum, 1)
        ]

class EventLogObject(Object):
    objectType = 'eventLog'
    properties = \
        [ ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , WritableProperty('enable', Boolean)
        , OptionalProperty('startTime', DateTime)
        , OptionalProperty('stopTime', DateTime)
        , ReadableProperty('stopWhenFull', Boolean)
        , ReadableProperty('bufferSize', Unsigned)
        , ReadableProperty('logBuffer', SequenceOf(EventLogRecord))
        , WritableProperty('recordCount', Unsigned)
        , ReadableProperty('totalRecordCount', Unsigned)
        , OptionalProperty('notificationThreshold', Unsigned)
        , OptionalProperty('recordsSinceNotification', Unsigned)
        , OptionalProperty('lastNotifyRecord', Unsigned)
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        ]

register_object_type(EventLogObject)

#-----

class FileObject(Object):
    objectType = 'file'
    properties = \
        [ ReadableProperty('fileType', CharacterString)
        , ReadableProperty('fileSize', Unsigned)
        , ReadableProperty('modificationDate', DateTime)
        , WritableProperty('archive', Boolean)
        , ReadableProperty('readOnly', Boolean)
        , ReadableProperty('fileAccessMethod', FileAccessMethod)
        , OptionalProperty('recordCount', Unsigned)
        ]

register_object_type(FileObject)

#-----

class GlobalGroupObject(Object):
    objectType = 'globalGroup'
    properties = \
        [ ReadableProperty('groupMembers', ArrayOf(DeviceObjectPropertyReference))
        , OptionalProperty('groupMemberNames', ArrayOf(CharacterString))
        , ReadableProperty('presentValue', ArrayOf(PropertyAccessResult))
        , ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('eventState', EventState)
        , ReadableProperty('memberStatusFlags', StatusFlags)
        , OptionalProperty('reliability', Reliability)
        , ReadableProperty('outOfService', Boolean)
        , OptionalProperty('updateInterval', Unsigned)
        , OptionalProperty('requestedUpdateInterval', Unsigned)
        , OptionalProperty('covResubscriptionInterval', Unsigned)
        , OptionalProperty('clientCovIncrement', ClientCOV)
        , OptionalProperty('timeDelay', Unsigned)
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        , OptionalProperty('covuPeriod', Unsigned)
        , OptionalProperty('covuRecipients', SequenceOf(Recipient))
        ]

register_object_type(GlobalGroupObject)

class GroupObject(Object):
    objectType = 'group'
    properties = \
        [ ReadableProperty('listOfGroupMembers', SequenceOf(ReadAccessSpecification))
        , ReadableProperty('presentValue', SequenceOf(ReadAccessResult))
        ]

register_object_type(GroupObject)

class IntegerValueObject(Object):
    objectType = 'integerValue'
    properties = \
        [ ReadableProperty('presentValue', Integer)
        , ReadableProperty('statusFlags', StatusFlags)
        , OptionalProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , OptionalProperty('outOfService', Boolean)
        , ReadableProperty('units', EngineeringUnits)
        , OptionalProperty('priorityArray', PriorityArray)
        , OptionalProperty('relinquishDefault', Integer)
        , OptionalProperty('covIncrement', Unsigned)
        , OptionalProperty('timeDelay', Unsigned)
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('highLimit', Integer)
        , OptionalProperty('lowLimit', Integer)
        , OptionalProperty('deadband', Unsigned)
        , OptionalProperty('limitEnable', LimitEnable)
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        ]

register_object_type(IntegerValueObject)

class LargeAnalogValueObject(Object):
    objectType = 'largeAnalogValue'
    properties = \
        [ ReadableProperty('presentValue', Double)
        , ReadableProperty('statusFlags', StatusFlags)
        , OptionalProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , OptionalProperty('outOfService', Boolean)
        , ReadableProperty('units', EngineeringUnits)
        , OptionalProperty('priorityArray', PriorityArray)
        , OptionalProperty('relinquishDefault', Integer)
        , OptionalProperty('covIncrement', Unsigned)
        , OptionalProperty('timeDelay', Unsigned)
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('highLimit', Double)
        , OptionalProperty('lowLimit', Double)
        , OptionalProperty('deadband', Double)
        , OptionalProperty('limitEnable', LimitEnable)
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        ]

register_object_type(LargeAnalogValueObject)

class LifeSafetyPointObject(Object):
    objectType = 'lifeSafetyPoint'
    properties = \
        [ ReadableProperty('presentValue', LifeSafetyState)
        , ReadableProperty('trackingValue', LifeSafetyState)
        , OptionalProperty('deviceType', CharacterString)
        , ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('eventState', EventState)
        , ReadableProperty('reliability', Reliability)
        , ReadableProperty('outOfService', Boolean)
        , WritableProperty('mode', LifeSafetyMode)
        , ReadableProperty('acceptedModes', SequenceOf(LifeSafetyMode))
        , OptionalProperty('timeDelay', Unsigned)
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('lifeSafetyAlarmValues', SequenceOf(LifeSafetyState))
        , OptionalProperty('alarmValues', SequenceOf(LifeSafetyState))
        , OptionalProperty('faultValues', SequenceOf(LifeSafetyState))
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        , ReadableProperty('silenced', SilencedState)
        , ReadableProperty('operationExpected', LifeSafetyOperation)
        , OptionalProperty('maintenanceRequired', Maintenance)
        , OptionalProperty('setting', Unsigned)
        , OptionalProperty('directReading', Real)
        , OptionalProperty('units', EngineeringUnits)
        , OptionalProperty('memberOf', SequenceOf(DeviceObjectReference))
        ]

register_object_type(LifeSafetyPointObject)

class LifeSafetyZoneObject(Object):
    objectType = 'lifeSafetyZone'
    properties = \
        [ ReadableProperty('presentValue', LifeSafetyState)
        , ReadableProperty('trackingValue', LifeSafetyState)
        , OptionalProperty('deviceType', CharacterString)
        , ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('eventState', EventState)
        , ReadableProperty('reliability', Reliability)
        , ReadableProperty('outOfService', Boolean)
        , WritableProperty('mode', LifeSafetyMode)
        , ReadableProperty('acceptedModes', SequenceOf(LifeSafetyMode))
        , OptionalProperty('timeDelay', Unsigned)
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('lifeSafetyAlarmValues', SequenceOf(LifeSafetyState))
        , OptionalProperty('alarmValues', SequenceOf(LifeSafetyState))
        , OptionalProperty('faultValues', SequenceOf(LifeSafetyState))
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        , ReadableProperty('silenced', SilencedState)
        , ReadableProperty('operationExpected', LifeSafetyOperation)
        , OptionalProperty('maintenanceRequired', Boolean)
        , ReadableProperty('zoneMembers', SequenceOf(DeviceObjectReference))
        , OptionalProperty('memberOf', SequenceOf(DeviceObjectReference))
        ]

register_object_type(LifeSafetyZoneObject)

class LoadControlObject(Object):
    objectType = 'loadControl'
    properties = \
        [ ReadableProperty('presentValue', ShedState)
        , OptionalProperty('stateDescription', CharacterString)
        , ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , WritableProperty('requestedShedLevel', ShedLevel)
        , WritableProperty('startTime', DateTime)
        , WritableProperty('shedDuration', Unsigned)
        , WritableProperty('dutyWindow', Unsigned)
        , WritableProperty('enable', Boolean)
        , OptionalProperty('fullDutyBaseline', Real)
        , ReadableProperty('expectedShedLevel', ShedLevel)
        , ReadableProperty('actualShedLevel', ShedLevel)
        , WritableProperty('shedLevels', ArrayOf(Unsigned))
        , ReadableProperty('shedLevelDescriptions', ArrayOf(CharacterString))
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('timeDelay', Unsigned)
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        ]

register_object_type(LoadControlObject)

class LoopObject(Object):
    objectType = 'loop'
    properties = \
        [ ReadableProperty('presentValue', Real)
        , ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , ReadableProperty('outOfService', Boolean)
        , ReadableProperty('updateInterval', Unsigned)
        , ReadableProperty('outputUnits', EngineeringUnits)
        , ReadableProperty('manipulatedVariableReference', ObjectPropertyReference)
        , ReadableProperty('controlledVariableReference', ObjectPropertyReference)
        , ReadableProperty('controlledVariableValue', Real)
        , ReadableProperty('controlledVariableUnits', EngineeringUnits)
        , ReadableProperty('setpointReference', SetpointReference)
        , ReadableProperty('setpoint', Real)
        , ReadableProperty('action', Action)
        , OptionalProperty('proportionalConstant', Real)
        , OptionalProperty('proportionalConstantUnits', EngineeringUnits)
        , OptionalProperty('integralConstant', Real)
        , OptionalProperty('integralConstantUnits', EngineeringUnits)
        , OptionalProperty('derivativeConstant', Real)
        , OptionalProperty('derivativeConstantUnits', EngineeringUnits)
        , OptionalProperty('bias', Real)
        , OptionalProperty('maximumOutput', Real)
        , OptionalProperty('minimumOutput', Real)
        , ReadableProperty('priorityForWriting', Unsigned)
        , OptionalProperty('covIncrement', Real)
        , OptionalProperty('timeDelay', Unsigned)
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('errorLimit', Real)
        , OptionalProperty('deadband', Real)
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        ]

register_object_type(LoopObject)

class MultiStateInputObject(Object):
    objectType = 'multiStateInput'
    properties = \
        [ ReadableProperty('presentValue', Unsigned)
        , OptionalProperty('deviceType', CharacterString)
        , ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , ReadableProperty('outOfService', Boolean)
        , ReadableProperty('numberOfStates', Unsigned)
        , OptionalProperty('stateText', ArrayOf(CharacterString))
        , OptionalProperty('timeDelay', Unsigned)
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('alarmValues', SequenceOf(Unsigned))
        , OptionalProperty('faultValues', SequenceOf(Unsigned))
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        ]

register_object_type(MultiStateInputObject)

class MultiStateOutputObject(Object):
    objectType = 'multiStateOutput'
    properties = \
        [ WritableProperty('presentValue', Unsigned)
        , OptionalProperty('deviceType', CharacterString)
        , ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , ReadableProperty('outOfService', Boolean)
        , ReadableProperty('numberOfStates', Unsigned)
        , OptionalProperty('stateText', ArrayOf(CharacterString))
        , ReadableProperty('priorityArray', PriorityArray)
        , OptionalProperty('relinquishDefault', Unsigned)
        , OptionalProperty('timeDelay', Unsigned)
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('feedbackValue', Unsigned)
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        ]

register_object_type(MultiStateOutputObject)

class MultiStateValueObject(Object): 
    objectType = 'multiStateValue'
    properties = \
        [ ReadableProperty('presentValue', Unsigned)
        , ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , ReadableProperty('outOfService', Boolean)
        , ReadableProperty('numberOfStates', Unsigned)
        , OptionalProperty('stateText', ArrayOf(CharacterString))
        , OptionalProperty('priorityArray', PriorityArray)
        , OptionalProperty('relinquishDefault', Unsigned)
        , OptionalProperty('timeDelay', Unsigned)
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('alarmValues', SequenceOf(Unsigned))
        , OptionalProperty('faultValues', SequenceOf(Unsigned))
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        ]
        
register_object_type(MultiStateValueObject)

class NetworkSecurityObject(Object):
    objectType = 'networkSecurity'
    properties = \
        [ WritableProperty('baseDeviceSecurityPolicy', SecurityLevel)
### more
        ]

class NotificationClassObject(Object):
    objectType = 'notificationClass'
    properties = \
        [ ReadableProperty('notificationClass', Unsigned)
        , ReadableProperty('priority', ArrayOf(Unsigned))
        , ReadableProperty('ackRequired', EventTransitionBits)
        , ReadableProperty('recipientList', SequenceOf(Destination))
        ]

register_object_type(NotificationClassObject)

class OctetStringValueObject(Object):
    objectType = 'octetstringValue'
    properties = \
        [ ReadableProperty('presentValue', CharacterString)
        , ReadableProperty('statusFlags', StatusFlags)
        , OptionalProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , OptionalProperty('outOfService', Boolean)
        , OptionalProperty('priorityArray', PriorityArray)
        , OptionalProperty('relinquishDefault', OctetString)
        ]

register_object_type(OctetStringValueObject)

class PositiveIntegerValueObject(Object):
    objectType = 'positiveIntegerValue'
    properties = \
        [ ReadableProperty('presentValue', Unsigned)
        , ReadableProperty('statusFlags', StatusFlags)
        , OptionalProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , OptionalProperty('outOfService', Boolean)
        , ReadableProperty('units', EngineeringUnits)
        , OptionalProperty('priorityArray', PriorityArray)
        , OptionalProperty('relinquishDefault', Unsigned)
        , OptionalProperty('covIncrement', Unsigned)
        , OptionalProperty('timeDelay', Unsigned)
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('highLimit', Unsigned)
        , OptionalProperty('lowLimit', Unsigned)
        , OptionalProperty('deadband', Unsigned)
        , OptionalProperty('limitEnable', LimitEnable)
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        ]

register_object_type(PositiveIntegerValueObject)

class ProgramObject(Object):
    objectType = 'program'
    properties = \
        [ ReadableProperty('programState', ProgramState)
        , WritableProperty('programChange', ProgramRequest)
        , OptionalProperty('reasonForHalt', ProgramError)
        , OptionalProperty('descriptionOfHalt', CharacterString)
        , OptionalProperty('programLocation', CharacterString)
        , OptionalProperty('instanceOf', CharacterString)
        , ReadableProperty('statusFlags', StatusFlags)
        , OptionalProperty('reliability', Reliability)
        , ReadableProperty('outOfService', Boolean)
        ]

register_object_type(ProgramObject)

class PulseConverterObject(Object):
    objectType = 'pulseConverter'
    properties = \
        [ ReadableProperty('presentValue', Real)
        , OptionalProperty('inputReference', ObjectPropertyReference)
        , ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , ReadableProperty('outOfService', Boolean)
        , ReadableProperty('units', EngineeringUnits)
        , ReadableProperty('scaleFactor', Real)
        , WritableProperty('adjustValue', Real)
        , ReadableProperty('count', Unsigned)
        , ReadableProperty('updateTime', DateTime)
        , ReadableProperty('countChangeTime', DateTime)
        , ReadableProperty('countBeforeChange', Unsigned)
        , OptionalProperty('covIncrement', Real)
        , OptionalProperty('covPeriod', Unsigned)
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('timeDelay', Unsigned)
        , OptionalProperty('highLimit', Real)
        , OptionalProperty('lowLimit', Real)
        , OptionalProperty('deadband', Real)
        , OptionalProperty('limitEnable', LimitEnable)
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
        ]

register_object_type(PulseConverterObject)

class ScheduleObject(Object):
    objectType = 'schedule'
    properties = \
        [ ReadableProperty('presentValue', Any)
        , ReadableProperty('effectivePeriod', DateRange)
        , OptionalProperty('weeklySchedule', ArrayOf(DailySchedule))
        , OptionalProperty('exceptionSchedule', ArrayOf(SpecialEvent))
        , ReadableProperty('scheduleDefault', Any)
        , ReadableProperty('listOfObjectPropertyReferences', SequenceOf(DeviceObjectPropertyReference))
        , ReadableProperty('priorityForWriting', Unsigned)
        , ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('reliability', Reliability)
        , ReadableProperty('outOfService', Boolean)
        ]

register_object_type(ScheduleObject)

class StructuredViewObject(Object):
    objectType = 'structuredView'
    properties = \
        [ ReadableProperty('nodeType', NodeType)
        , OptionalProperty('nodeSubtype', CharacterString)
        , ReadableProperty('subordinateList', ArrayOf(DeviceObjectReference))
        , OptionalProperty('subordinateAnnotations', ArrayOf(CharacterString))
        ]

register_object_type(StructuredViewObject)

class TimePatternValueObject(Object):
    objectType = 'timePatternValue'
    properties = \
        [ ReadableProperty('presentValue', Time)
        , ReadableProperty('statusFlags', StatusFlags)
        , OptionalProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , OptionalProperty('outOfService', Boolean)
        , OptionalProperty('isUtc', Boolean)
        , OptionalProperty('priorityArray', PriorityArray)
        , OptionalProperty('relinquishDefault', DateTime)
        ]

register_object_type(TimePatternValueObject)

class TimeValueObject(Object):
    objectType = 'timeValue'
    properties = \
        [ ReadableProperty('presentValue', Time)
        , ReadableProperty('statusFlags', StatusFlags)
        , OptionalProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , OptionalProperty('outOfService', Boolean)
        , OptionalProperty('priorityArray', PriorityArray)
        , OptionalProperty('relinquishDefault', Time)
        ]

register_object_type(TimeValueObject)

class TrendLogObject(Object):
    objectType = 'trendLog'
    properties = \
        [ ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , WritableProperty('enable', Boolean)
        , OptionalProperty('startTime', DateTime)
        , OptionalProperty('stopTime', DateTime)
        , OptionalProperty('logDeviceObjectProperty', DeviceObjectPropertyReference)
        , OptionalProperty('logInterval', Unsigned)
        , OptionalProperty('covResubscriptionInterval', Unsigned)
        , OptionalProperty('clientCovIncrement', ClientCOV)
        , ReadableProperty('stopWhenFull', Boolean)
        , ReadableProperty('bufferSize', Unsigned)
        , ReadableProperty('logBuffer', SequenceOf(LogRecord))
        , WritableProperty('recordCount', Unsigned)
        , ReadableProperty('totalRecordCount', Unsigned)
        , ReadableProperty('loggingType', LoggingType)
        , OptionalProperty('alignIntervals', Boolean)
        , OptionalProperty('intervalOffset', Unsigned)
        , OptionalProperty('trigger', Boolean)
        , ReadableProperty('statusFlags', StatusFlags)
        , OptionalProperty('reliability', Reliability)
        , OptionalProperty('notificationThreshold', Unsigned)
        , OptionalProperty('recordsSinceNotification', Unsigned)
        , OptionalProperty('lastNotifyRecord', Unsigned)
        , ReadableProperty('eventState', EventState)
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
#       , OptionalProperty('eventMessageTextsConfig', ArrayOf(CharacterString))
#       , OptionalProperty('eventDetectionEnable', Boolean)
#       , OptionalProperty('eventAlgorithmInhibitRef', ObjectPropertyReference)
#       , OptionalProperty('eventAlgorithmInhibit', Boolean)
#       , OptionalProperty('reliabilityEvaluationInhibit', Boolean)
        ]

register_object_type(TrendLogObject)

class TrendLogMultipleObject(Object):
    objectType = 'trendLogMultiple'
    properties = \
        [ ReadableProperty('statusFlags', StatusFlags)
        , ReadableProperty('eventState', EventState)
        , OptionalProperty('reliability', Reliability)
        , WritableProperty('enable', Boolean)
        , OptionalProperty('startTime', DateTime)
        , OptionalProperty('stopTime', DateTime)
        , ReadableProperty('logDeviceObjectProperty', ArrayOf(DeviceObjectPropertyReference))
        , ReadableProperty('loggingType', LoggingType)
        , ReadableProperty('logInterval', Unsigned)
        , OptionalProperty('alignIntervals', Boolean)
        , OptionalProperty('intervalOffset', Unsigned)
        , OptionalProperty('trigger', Boolean)
        , ReadableProperty('stopWhenFull', Boolean)
        , ReadableProperty('bufferSize', Unsigned)
        , ReadableProperty('logBuffer', SequenceOf(LogMultipleRecord))
        , WritableProperty('recordCount', Unsigned)
        , ReadableProperty('totalRecordCount', Unsigned)
        , OptionalProperty('notificationThreshold', Unsigned)
        , OptionalProperty('recordsSinceNotification', Unsigned)
        , OptionalProperty('lastNotifyRecord', Unsigned)
        , OptionalProperty('notificationClass', Unsigned)
        , OptionalProperty('eventEnable', EventTransitionBits)
        , OptionalProperty('ackedTransitions', EventTransitionBits)
        , OptionalProperty('notifyType', NotifyType)
        , OptionalProperty('eventTimeStamps', ArrayOf(TimeStamp))
        , OptionalProperty('eventMessageTexts', ArrayOf(CharacterString))
#       , OptionalProperty('eventMessageTextsConfig', ArrayOf(CharacterString))
#       , OptionalProperty('eventDetectionEnable', Boolean)
#       , OptionalProperty('eventAlgorithmInhibitRef', ObjectPropertyReference)
#       , OptionalProperty('eventAlgorithmInhibit', Boolean)
#       , OptionalProperty('reliabilityEvaluationInhibit', Boolean)
        ]

register_object_type(TrendLogMultipleObject)

