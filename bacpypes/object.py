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
from apdu import EventNotificationParameters, ReadAccessSpecification, ReadAccessResult

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

        # validate the identifier to be one of the Property enumerations
        if identifier not in PropertyIdentifier.enumerations:
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
                raise TypeError, "%s is not an array" % (self.identifier,)
                
            # check the array
            arry = obj._values[self.identifier]
            if arry is None:
                raise ValueError, "%s uninitialized array" % (self.identifier,)
                
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
#   Object
#

class Object(Logging):

    properties = \
        [ ObjectIdentifierProperty('objectIdentifier', ObjectIdentifier, optional=False)
        , Property('objectName', CharacterString, optional=False)
        , Property('description', CharacterString, default='')
        , Property('profileName', CharacterString)
        , Property('propertyList', ArrayOf(PropertyIdentifier))
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
        [ Property('globalIdentifier', Unsigned, optional=True)
        , Property('statusFlags', StatusFlags)
        , Property('reliability', Reliability)
        , Property('credentialStatus', BinaryPV)
        , Property('reasonForDisable', SequenceOf(AccessCredentialDisableReason))
        , Property('authenticationFactors', ArrayOf(CredentialAuthenticationFactor))
        , Property('activationTime', DateTime)
        , Property('expiryTime', DateTime)
        , Property('credentialDisable', AccessCredentialDisable)
        , Property('daysRemaining', Integer, optional=True)
        , Property('usesRemaining', Integer, optional=True)
        , Property('absenteeLimit', Unsigned, optional=True)
        , Property('belongsTo', DeviceObjectReference, optional=True)
        , Property('assignedAccessRights', ArrayOf(AssignedAccessRights))
        , Property('lastAccessPoint', DeviceObjectReference, optional=True)
        , Property('lastAccessEvent', AccessEvent, optional=True)
        , Property('lastUseTime', DateTime, optional=True)
        , Property('traceFlag', Boolean, optional=True)
        , Property('threatAuthority', AccessThreatLevel, optional=True)
        , Property('extendedTimeEnable', Boolean, optional=True)
        , Property('masterExemption', Boolean, optional=True)
        , Property('passbackExemption', Boolean, optional=True)
        , Property('occupancyExemption', Boolean, optional=True)
        ]

register_object_type(AccessCredentialObject)

class AccessDoorObject(Object):
    objectType = 'accessDoor'
    properties = \
        [ Property('presentValue', DoorValue, optional=True)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState)
        , Property('reliability', Reliability)
        , Property('outOfService', Boolean)
        , Property('priorityArray', PriorityArray)
        , Property('relinquishDefault', DoorValue)
        , Property('doorStatus', DoorStatus, optional=True)
        , Property('lockStatus', LockStatus, optional=True)
        , Property('securedStatus', DoorSecuredStatus, optional=True)
        , Property('doorMembers', ArrayOf(DeviceObjectReference), optional=True)
        , Property('doorPulseTime', Unsigned)
        , Property('doorExtendedPulseTime', Unsigned)
        , Property('doorUnlockDelayTime', Unsigned, optional=True)
        , Property('doorOpenTooLongTime', Unsigned)
        , Property('doorAlarmState', DoorAlarmState, optional=True)
        , Property('maskedAlarmValues', SequenceOf(DoorAlarmState), optional=True)
        , Property('maintenanceRequired', Maintenance, optional=True)
        , Property('timeDelay', Unsigned, optional=True)
        , Property('notificationClass', Unsigned, optional=True)
        , Property('alarmValues', SequenceOf(DoorAlarmState), optional=True)
        , Property('faultValues', SequenceOf(DoorAlarmState), optional=True)
        , Property('eventEnable', EventTransitionBits, optional=True)
        , Property('ackedTransitions', EventTransitionBits, optional=True)
        , Property('notifyType', NotifyType, optional=True)
        , Property('eventTimeStamps', ArrayOf(TimeStamp), optional=True)
        , Property('eventMessageTexts', ArrayOf(CharacterString))
        ]

register_object_type(AccessDoorObject)

class AccessPointObject(Object):
    objectType = 'accessPoint'
    properties = \
        [ Property('statusFlags', StatusFlags)
        , Property('eventState', EventState)
        , Property('reliability', Reliability)
        , Property('outOfService', Boolean)
        , Property('authenticationStatus', AuthenticationStatus)
        , Property('activeAuthenticationPolicy', Unsigned)
        , Property('numberOfAuthenticationPolicies', Unsigned)
        , Property('authenticationPolicyList', ArrayOf(AuthenticationPolicy), optional=True)
        , Property('authenticationPolicyNames', ArrayOf(CharacterString), optional=True)
        , Property('authorizationMode', AuthorizationMode)
        , Property('verificationTime', Unsigned, optional=True)
        , Property('lockout', Boolean, optional=True)
        , Property('lockoutRelinquishTime', Unsigned, optional=True)
        , Property('failedAttempts', Unsigned, optional=True)
        , Property('failedAttemptEvents', SequenceOf(AccessEvent), optional=True)
        , Property('maxFailedAttempts', Unsigned, optional=True)
        , Property('failedAttemptsTime', Unsigned, optional=True)
        , Property('threatLevel', AccessThreatLevel, optional=True)
        , Property('occupancyUpperLimitEnforced', Boolean, optional=True)
        , Property('occupancyLowerLimitEnforced', Boolean, optional=True)
        , Property('occupancyCountAdjust', Boolean, optional=True)
        , Property('accompanimentTime', Unsigned, optional=True)
        , Property('accessEvent', AccessEvent)
        , Property('accessEventTag', Unsigned)
        , Property('accessEventTime', TimeStamp)
        , Property('accessEventCredential', DeviceObjectReference)
        , Property('accessEventAuthenticationFactor', AuthenticationFactor, optional=True)
        , Property('accessDoors', ArrayOf(DeviceObjectReference))
        , Property('priorityForWriting', Unsigned)
        , Property('musterPoint', Boolean, optional=True)
        , Property('zoneTo', DeviceObjectReference, optional=True)
        , Property('zoneFrom', DeviceObjectReference, optional=True)
        , Property('notificationClass', Unsigned, optional=True)
        , Property('transactionNotificationClass', Unsigned, optional=True)
        , Property('accessAlarmEvents', SequenceOf(AccessEvent), optional=True)
        , Property('accessTransactionEvents', SequenceOf(AccessEvent), optional=True)
        , Property('eventEnable', EventTransitionBits, optional=True)
        , Property('ackedTransitions', EventTransitionBits, optional=True)
        , Property('notifyType', NotifyType, optional=True)
        , Property('eventTimeStamps', ArrayOf(TimeStamp), optional=True)
        , Property('eventMessageTexts', ArrayOf(CharacterString))
        ]

register_object_type(AccessPointObject)

class AccessRightsObject(Object):
    objectType = 'accessRights'
    properties = \
        [ Property('globalIdentifier', Unsigned, optional=True)
        , Property('statusFlags', StatusFlags)
        , Property('reliability', Reliability)
        , Property('enable', Boolean)
        , Property('negativeAccessRules', ArrayOf(AccessRule))
        , Property('positiveAccessRules', ArrayOf(AccessRule))
        , Property('accompaniment', DeviceObjectReference, optional=True)
        ]

register_object_type(AccessRightsObject)

class AccessUserObject(Object):
    objectType = 'accessUser'
    properties = \
        [ Property('globalIdentifier', Unsigned, optional=True)
        , Property('statusFlags', StatusFlags)
        , Property('reliability', Reliability)
        , Property('userType', AccessUserType)
        , Property('userName', CharacterString, optional=True)
        , Property('userExternalIdentifier', CharacterString, optional=True)
        , Property('userInformationReference', CharacterString, optional=True)
        , Property('members', SequenceOf(DeviceObjectReference), optional=True)
        , Property('memberOf', SequenceOf(DeviceObjectReference), optional=True)
        , Property('credentials', SequenceOf(DeviceObjectReference))
       ]

register_object_type(AccessUserObject)

class AccessZoneObject(Object):
    objectType = 'accessZone'
    properties = \
        [ Property('globalIdentifier', Unsigned, optional=True)
        , Property('occupancyState', AccessZoneOccupancyState)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState)
        , Property('reliability', Reliability)
        , Property('outOfService', Boolean)
        , Property('occupancyCount', Unsigned, optional=True)
        , Property('occupancyCountEnable', Boolean, optional=True)
        , Property('adjustValue', Integer, optional=True)
        , Property('occupancyUpperLimit', Unsigned, optional=True)
        , Property('occupancyLowerLimit', Unsigned, optional=True)
        , Property('credentialsInZone', SequenceOf(DeviceObjectReference) , optional=True)
        , Property('lastCredentialAdded', DeviceObjectReference, optional=True)
        , Property('lastCredentialAddedTime', DateTime, optional=True)
        , Property('lastCredentialRemoved', DeviceObjectReference, optional=True)
        , Property('lastCredentialRemovedTime', DateTime, optional=True)
        , Property('passbackMode', AccessPassbackMode, optional=True)
        , Property('passbackTimeout', Unsigned, optional=True)
        , Property('entryPoints', SequenceOf(DeviceObjectReference))
        , Property('exitPoints', SequenceOf(DeviceObjectReference))
        , Property('timeDelay', Unsigned, optional=True)
        , Property('notificationClass', Unsigned, optional=True)
        , Property('alarmValues', SequenceOf(AccessZoneOccupancyState), optional=True)
        , Property('eventEnable', EventTransitionBits, optional=True)
        , Property('ackedTransitions', EventTransitionBits, optional=True)
        , Property('notifyType', NotifyType, optional=True)
        , Property('eventTimeStamps', ArrayOf(TimeStamp), optional=True)
        , Property('eventMessageTexts', ArrayOf(CharacterString), optional=True)
        ]

register_object_type(AccessZoneObject)

class AccumulatorObject(Object):
    objectType = 'accumulator'
    properties = \
        [ Property('presentValue', Unsigned)
        , Property('deviceType', CharacterString, optional=True)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState)
        , Property('reliability', Reliability, optional=True)
        , Property('outOfService', Boolean)
        , Property('scale', Scale)
        , Property('units', EngineeringUnits)
        , Property('prescale', Prescale, optional=True)
        , Property('maxPresValue', Unsigned)
        , Property('valueChangeTime', DateTime, optional=True)
        , Property('valueBeforeChange', Unsigned, optional=True)
        , Property('valueSet', Unsigned, optional=True)
        , Property('loggingRecord', AccumulatorRecord, optional=True)
        , Property('loggingObject', ObjectIdentifier, optional=True)
        , Property('pulseRate', Unsigned, optional=True)
        , Property('highLimit', Unsigned, optional=True)
        , Property('lowLimit', Unsigned, optional=True)
        , Property('limitMonitoringInterval', Unsigned, optional=True)
        , Property('notificationClass', Unsigned, optional=True)
        , Property('timeDelay', Unsigned, optional=True)
        , Property('limitEnable', LimitEnable, optional=True)
        , Property('eventEnable', EventTransitionBits, optional=True)
        , Property('ackedTransitions', EventTransitionBits, optional=True)
        , Property('notifyType', NotifyType, optional=True)
        , Property('eventTimeStamps', SequenceOf(TimeStamp), optional=True)
        , Property('eventMessageTexts', SequenceOf(CharacterString), optional=True)
        ]

register_object_type(AccumulatorObject)

class AnalogInputObject(Object):
    objectType = 'analogInput'
    properties = \
        [ Property('presentValue', Real)
        , Property('deviceType', CharacterString, optional=True)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState)
        , Property('reliability', Reliability, optional=True)
        , Property('outOfService', Boolean)
        , Property('updateInterval', Unsigned, optional=True)
        , Property('units', EngineeringUnits)
        , Property('minPresValue', Real, optional=True)
        , Property('maxPresValue', Real, optional=True)
        , Property('resolution', Real, optional=True)
        , Property('covIncrement', Real, optional=True)
        , Property('timeDelay', Unsigned, optional=True)
        , Property('notificationClass', Unsigned, optional=True)
        , Property('highLimit', Real, optional=True)
        , Property('lowLimit', Real, optional=True)
        , Property('deadband', Real, optional=True)
        , Property('limitEnable', LimitEnable, optional=True)
        , Property('eventEnable', EventTransitionBits, optional=True)
        , Property('ackedTransitions', EventTransitionBits, optional=True)
        , Property('notifyType', NotifyType, optional=True)
        , Property('eventTimeStamps', ArrayOf(TimeStamp), optional=True)
        , Property('eventMessageTexts', ArrayOf(CharacterString), optional=True)
        ]

register_object_type(AnalogInputObject)

class AnalogOutputObject(Object):
    objectType = 'analogOutput'
    properties = \
         [ Property('presentValue', Real)
         , Property('deviceType', CharacterString, optional=True)
         , Property('statusFlags', StatusFlags)
         , Property('eventState', EventState)
         , Property('reliability', Reliability, optional=True)
         , Property('outOfService', Boolean)
         , Property('units',  EngineeringUnits)
         , Property('minPresValue', Real, optional=True)
         , Property('maxPresValue', Real, optional=True)
         , Property('resolution', Real, optional=True)
         , Property('priorityArray', PriorityArray)
         , Property('relinquishDefault', Real)
         , Property('covIncrement', Real, optional=True)
         , Property('timeDelay', Unsigned, optional=True)
         , Property('notificationClass', Unsigned, optional=True)
         , Property('highLimit', Real, optional=True)
         , Property('lowLimit', Real, optional=True)
         , Property('deadband', Real, optional=True)
         , Property('limitEnable', LimitEnable, optional=True)
         , Property('eventEnable', EventTransitionBits, optional=True)
         , Property('ackedTransitions',  EventTransitionBits, optional=True)
         , Property('notifyType', NotifyType, optional=True)
         , Property('eventTimeStamps', ArrayOf(TimeStamp), optional=True)
         , Property('eventMessageTexts', ArrayOf(CharacterString), optional=True)
         ]

register_object_type(AnalogOutputObject)

class AnalogValueObject(Object):
    objectType = 'analogValue'
    properties = \
        [ Property('presentValue', Real)
        , Property('deviceType', StatusFlags, optional=True)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState)
        , Property('reliability', Reliability, optional=True)
        , Property('outOfService', Boolean)
        , Property('units', EngineeringUnits)
        , Property('minPresValue', Real, optional=True)
        , Property('maxPresValue', Real, optional=True)
        , Property('resolution', Real, optional=True)
        , Property('priorityArray', PriorityArray, optional=True)
        , Property('relinquishDefault', Real, optional=True)
        , Property('covIncrement', Real, optional=True)
        , Property('timeDelay', Unsigned, optional=True)
        , Property('notificationClass',  Unsigned, optional=True)
        , Property('highLimit', Real, optional=True)
        , Property('lowLimit', Real, optional=True)
        , Property('deadband', Real, optional=True)
        , Property('limitEnable', LimitEnable, optional=True)
        , Property('eventEnable', EventTransitionBits, optional=True)
        , Property('ackedTransitions', EventTransitionBits, optional=True)
        , Property('notifyType', NotifyType, optional=True)
        , Property('eventTimeStamps', ArrayOf(TimeStamp), optional=True)
        , Property('eventMessageTexts', ArrayOf(CharacterString), optional=True)
        ]

register_object_type(AnalogValueObject)

class AveragingObject(Object):
    objectType = 'averaging'
    properties = \
        [ Property('minimumValue', Real)
        , Property('minimumValueTimestamp', DateTime, optional=True)
        , Property('averageValue', Real)
        , Property('varianceValue', Real, optional=True)
        , Property('maximumValue', Real)
        , Property('maximumValueTimestamp', DateTime, optional=True)
        , Property('attemptedSamples', Unsigned, optional=True)
        , Property('validSamples', Unsigned)
        , Property('objectPropertyReference', DeviceObjectPropertyReference)
        , Property('windowInterval', Unsigned, optional=True)
        , Property('windowSamples', Unsigned, optional=True)
        ]
 
register_object_type(AveragingObject)

class BinaryInputObject(Object):
    objectType = 'binaryInput'
    properties = \
        [ Property('presentValue', BinaryPV)
        , Property('deviceType', CharacterString, optional=True)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState)
        , Property('reliability', Reliability, optional=True)
        , Property('outOfService', Boolean)
        , Property('polarity', Polarity)
        , Property('inactiveText', CharacterString, optional=True)
        , Property('activeText', CharacterString, optional=True)
        , Property('changeOfStateTime', DateTime, optional=True)
        , Property('changeOfStateCount', Unsigned, optional=True)
        , Property('timeOfStateCountReset', DateTime, optional=True)
        , Property('elapsedActiveTime', Unsigned, optional=True)
        , Property('timeOfActiveTimeReset', DateTime, optional=True)
        , Property('timeDelay', Unsigned, optional=True)
        , Property('notificationClass', Unsigned, optional=True)
        , Property('alarmValue', BinaryPV, optional=True)
        , Property('eventEnable', EventTransitionBits, optional=True)
        , Property('ackedTransitions', EventTransitionBits, optional=True)
        , Property('notifyType', NotifyType, optional=True)
        , Property('eventTimeStamps', ArrayOf(TimeStamp), optional=True)        
        , Property('eventMessageTexts', ArrayOf(CharacterString), optional=True)
        ]

register_object_type(BinaryInputObject)

class BinaryOutputObject(Object):
    objectType = 'binaryOutput'
    properties = \
        [ Property('presentValue', BinaryPV)
        , Property('deviceType', CharacterString, optional=True)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState)
        , Property('reliability', Reliability, optional=True)
        , Property('outOfService', Boolean)
        , Property('polarity', Polarity)
        , Property('inactiveText', CharacterString, optional=True)
        , Property('activeText', CharacterString, optional=True)
        , Property('changeOfStateTime', DateTime, optional=True)
        , Property('changeOfStateCount', Unsigned, optional=True)
        , Property('timeOfStateCountReset', DateTime, optional=True)
        , Property('elapsedActiveTime', Unsigned, optional=True)
        , Property('timeOfActiveTimeReset', DateTime, optional=True)
        , Property('minimumOffTime', Unsigned, optional=True)
        , Property('minimumOnTime', Unsigned, optional=True)
        , Property('priorityArray', PriorityArray)
        , Property('relinquishDefault', BinaryPV)
        , Property('timeDelay', Unsigned, optional=True)
        , Property('notificationClass', Unsigned, optional=True)
        , Property('feedbackValue', BinaryPV, optional=True)
        , Property('eventEnable', EventTransitionBits, optional=True)
        , Property('ackedTransitions', EventTransitionBits, optional=True)
        , Property('notifyType', NotifyType, optional=True)
        , Property('eventTimeStamps', ArrayOf(TimeStamp), optional=True)
        , Property('eventMessageTexts', ArrayOf(CharacterString), optional=True)
        ]

register_object_type(BinaryOutputObject)

class BinaryValueObject(Object):
    objectType = 'binaryValue'
    properties = \
        [ Property('presentValue', BinaryPV)
        , Property('statusFlags',StatusFlags)
        , Property('eventState',EventState)
        , Property('reliability',Reliability,optional=True)
        , Property('outOfService',Boolean)
        , Property('inactiveText',CharacterString,optional=True)
        , Property('activeText',CharacterString,optional=True)
        , Property('changeOfStateTime',DateTime,optional=True)
        , Property('changeOfStateCount',Unsigned,optional=True)
        , Property('timeOfStateCountReset',DateTime,optional=True)
        , Property('elapsedActiveTime',Unsigned,optional=True)
        , Property('timeOfActiveTimeReset',DateTime,optional=True)
        , Property('minimumOffTime',Unsigned,optional=True)
        , Property('minimumOnTime',Unsigned,optional=True)
        , Property('priorityArray',PriorityArray,optional=True)
        , Property('relinquishDefault',BinaryPV,optional=True)
        , Property('timeDelay',Unsigned,optional=True)
        , Property('notificationClass',Unsigned,optional=True)
        , Property('alarmValue',BinaryPV,optional=True)
        , Property('eventEnable',EventTransitionBits,optional=True)
        , Property('ackedTransitions',EventTransitionBits,optional=True)
        , Property('notifyType',NotifyType,optional=True)
        , Property('eventTimeStamps', ArrayOf(TimeStamp),optional=True)
        , Property('eventMessageTexts', ArrayOf(CharacterString),optional=True)
        ]

register_object_type(BinaryValueObject)

class BitStringValueObject(Object):
    objectType = 'bitstringValue'
    properties = \
        [ Property('presentValue', BitString)
        , Property('bitText', ArrayOf(CharacterString), optional=True)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState, optional=True)
        , Property('reliability', Reliability, optional=True)
        , Property('outOfService', Boolean, optional=True)
        , Property('priorityArray', PriorityArray, optional=True)
        , Property('relinquishDefault', BitString, optional=True)
        , Property('timeDelay', Unsigned, optional=True)
        , Property('notificationClass', Unsigned, optional=True)
        , Property('alarmValues', ArrayOf(BitString), optional=True)
        , Property('bitMask', BitString, optional=True)
        , Property('eventEnable', EventTransitionBits, optional=True)
        , Property('ackedTransitions', EventTransitionBits, optional=True)
        , Property('notifyType', NotifyType, optional=True)
        , Property('eventTimeStamps', ArrayOf(TimeStamp), optional=True)
        , Property('eventMessageTexts', ArrayOf(CharacterString))
        ]

register_object_type(BitStringValueObject)

class CalendarObject(Object):
    objectType = 'calendar'
    properties = \
        [ Property('presentValue', Boolean)
        , Property('dateList', SequenceOf(CalendarEntry)) 
        ]

register_object_type(CalendarObject)

class CharacterStringValueObject(Object):
    objectType = 'characterStringValue'
    properties = \
        [ Property('presentValue', CharacterString)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState, optional=True)
        , Property('reliability', Reliability, optional=True)
        , Property('outOfService', Boolean, optional=True)
        , Property('priorityArray', PriorityArray, optional=True)
        , Property('relinquishDefault', CharacterString, optional=True)
        , Property('timeDelay', Unsigned, optional=True)
        , Property('notificationClass', Unsigned, optional=True)
        , Property('alarmValues', ArrayOf(OptionalCharacterString), optional=True)
        , Property('faultValues', ArrayOf(OptionalCharacterString), optional=True)
        , Property('eventEnable', EventTransitionBits, optional=True)
        , Property('ackedTransitions', EventTransitionBits, optional=True)
        , Property('notifyType', NotifyType, optional=True)
        , Property('eventTimeStamps', ArrayOf(TimeStamp), optional=True)
        , Property('eventMessageTexts', ArrayOf(CharacterString), optional=True)
        ]

register_object_type(CharacterStringValueObject)

class CommandObject(Object):
    objectType = 'command'
    properties = \
        [ Property('presentValue', Unsigned, optional=True)
        , Property('inProcess', Boolean)
        , Property('allWritesSuccessful', Boolean)
        , Property('action', ArrayOf(ActionList))
        , Property('actionText', ArrayOf(CharacterString), optional=True)
        ]

register_object_type(CommandObject)

class CredentialDataInputObject(Object):
    objectType = 'credentialDataInput'
    properties = \
        [ Property('presentValue', AuthenticationFactor)
        , Property('statusFlags', StatusFlags)
        , Property('reliability', Reliability, optional=True)
        , Property('outOfService', Boolean)
        , Property('supportedFormats', ArrayOf(AuthenticationFactorFormat))
        , Property('supportedFormatClasses', ArrayOf(Unsigned))
        ]

register_object_type(CredentialDataInputObject)

class DatePatternValueObject(Object):
    objectType = 'datePatternValue'
    properties = \
        [ Property('presentValue', Date)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState, optional=True)
        , Property('reliability', Reliability, optional=True)
        , Property('outOfService', Boolean, optional=True)
        , Property('priorityArray', PriorityArray, optional=True)
        , Property('relinquishDefault', DateTime, optional=True)
        ]

register_object_type(DatePatternValueObject)

class DateValueObject(Object):
    objectType = 'dateValue'
    properties = \
        [ Property('presentValue', Date)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState, optional=True)
        , Property('reliability', Reliability, optional=True)
        , Property('outOfService', Boolean, optional=True)
        , Property('priorityArray', PriorityArray, optional=True)
        , Property('relinquishDefault', Date, optional=True)
        ]

register_object_type(DateValueObject)

class DateTimePatternValueObject(Object):
    objectType = 'datetimePatternValue'
    properties = \
        [ Property('presentValue', DateTime)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState, optional=True)
        , Property('reliability', Reliability, optional=True)
        , Property('outOfService', Boolean, optional=True)
        , Property('priorityArray', PriorityArray, optional=True)
        , Property('relinquishDefault', DateTime, optional=True)
        , Property('isUtc', Boolean, optional=True)
        ]

register_object_type(DateTimePatternValueObject)

class DateTimeValueObject(Object):
    objectType = 'datetimeValue'
    properties = \
        [ Property('presentValue', DateTime)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState, optional=True)
        , Property('reliability', Reliability, optional=True)
        , Property('outOfService', Boolean, optional=True)
        , Property('priorityArray', PriorityArray, optional=True)
        , Property('relinquishDefault', DateTime, optional=True)
        , Property('isUtc', Boolean, optional=True)
        ]

register_object_type(DateTimeValueObject)

class DeviceObject(Object):
    objectType = 'device'
    properties = \
        [ Property('systemStatus', DeviceStatus)
        , Property('vendorName', CharacterString)
        , Property('vendorIdentifier', Unsigned)
        , Property('modelName', CharacterString)
        , Property('firmwareRevision', CharacterString)
        , Property('applicationSoftwareVersion', CharacterString)
        , Property('location', CharacterString, optional=True)
        , Property('protocolVersion', Unsigned)
        , Property('protocolRevision', Unsigned)
        , Property('protocolServicesSupported', ServicesSupported)
        , Property('protocolObjectTypesSupported', ObjectTypesSupported)
        , Property('objectList', ArrayOf(ObjectIdentifier))
        , Property('structuredObjectList', ArrayOf(ObjectIdentifier), optional=True)
        , Property('maxApduLengthAccepted', Unsigned)
        , Property('segmentationSupported', Segmentation)
        , Property('vtClassesSupported', SequenceOf(VTClass), optional=True)
        , Property('activeVtSessions', SequenceOf(VTSession), optional=True)
        , Property('localTime', Time, optional=True)
        , Property('localDate', Date, optional=True)
        , Property('utcOffset', Integer, optional=True)
        , Property('daylightSavingsStatus', Boolean, optional=True)
        , Property('apduSegmentTimeout', Unsigned, optional=True)
        , Property('apduTimeout', Unsigned)
        , Property('numberOfApduRetries', Unsigned)
        , Property('timeSynchronizationRecipients', SequenceOf(Recipient), optional=True)
        , Property('maxMaster', Unsigned, optional=True)
        , Property('maxInfoFrames', Unsigned)
        , Property('deviceAddressBinding', SequenceOf(AddressBinding))
        , Property('databaseRevision', Unsigned, optional=True)
        , Property('configurationFiles', ArrayOf(ObjectIdentifier), optional=True)
        , Property('lastRestoreTime', TimeStamp, optional=True)
        , Property('backupFailureTimeout', Unsigned, optional=True)
        , Property('backupPreparationTime', Unsigned, optional=True)
        , Property('restorePreparationTime', Unsigned, optional=True)
        , Property('restoreCompletionTime', Unsigned, optional=True)
        , Property('backupAndRestoreState', BackupState, optional=True)
        , Property('activeCovSubscriptions', SequenceOf(COVSubscription), optional=True)
        , Property('maxSegmentsAccepted', Unsigned, optional=True)
        , Property('slaveProxyEnable', ArrayOf(Boolean), optional=True)
        , Property('autoSlaveDiscovery', ArrayOf(Boolean), optional=True)
        , Property('slaveAddressBinding', SequenceOf(AddressBinding), optional=True)
        , Property('manualSlaveAddressBinding', SequenceOf(AddressBinding), optional=True)
        , Property('lastRestartReason', RestartReason, optional=True)
        , Property('timeOfDeviceRestart', TimeStamp, optional=True)
        , Property('restartNotificationRecipients', SequenceOf(Recipient), optional=True)
        , Property('utcTimeSynchronizationRecipients', SequenceOf(Recipient), optional=True)
        , Property('timeSynchronizationInterval', Unsigned, optional=True)
        , Property('alignIntervals', Boolean, optional=True)
        , Property('intervalOffset', Unsigned, optional=True)
        ]

register_object_type(DeviceObject)

class EventEnrollmentObject(Object):
    objectType = 'eventEnrollment'
    properties = \
        [ Property('eventType', EventType)
        , Property('notifyType', NotifyType)
        , Property('eventParameters', EventParameter)
        , Property('objectPropertyReference', DeviceObjectPropertyReference)
        , Property('eventState', EventState)
        , Property('eventEnable', EventTransitionBits)
        , Property('ackedTransitions', EventTransitionBits)
        , Property('notificationClass', Unsigned)
        , Property('eventTimeStamps', ArrayOf(TimeStamp))
        , Property('eventMessageTexts', ArrayOf(CharacterString), optional=True)
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
        [ Property('statusFlags', StatusFlags)
        , Property('eventState', EventState)
        , Property('reliability', Reliability, optional=True)
        , Property('enable', Boolean, optional=True)
        , Property('startTime', DateTime, optional=True)
        , Property('stopTime', DateTime, optional=True)
        , Property('stopWhenFull', Boolean)
        , Property('bufferSize', Unsigned)
        , Property('logBuffer', SequenceOf(EventLogRecord))
        , Property('recordCount', Unsigned, optional=True)
        , Property('totalRecordCount', Unsigned)
        , Property('notificationThreshold', Unsigned, optional=True)
        , Property('recordsSinceNotification', Unsigned, optional=True)
        , Property('lastNotifyRecord', Unsigned, optional=True)
        , Property('notificationClass', Unsigned, optional=True)
        , Property('eventEnable', EventTransitionBits, optional=True)
        , Property('ackedTransitions', EventTransitionBits, optional=True)
        , Property('notifyType', NotifyType, optional=True)
        , Property('eventTimeStamps', ArrayOf(TimeStamp), optional=True)
        , Property('eventMessageTexts', ArrayOf(CharacterString), optional=True)
        ]

register_object_type(EventLogObject)

#-----

class FileObject(Object):
    objectType = 'file'
    properties = \
        [ Property('fileType', CharacterString)
        , Property('fileSize', Unsigned)
        , Property('modificationDate', DateTime)
        , Property('archive', Boolean, optional=True)
        , Property('readOnly', Boolean)
        , Property('fileAccessMethod', FileAccessMethod)
        , Property('recordCount', Unsigned, optional=True)
        ]

register_object_type(FileObject)

#-----

class GlobalGroupObject(Object):
    objectType = 'globalGroup'
    properties = \
        [ Property('groupMembers', ArrayOf(DeviceObjectPropertyReference))
        , Property('groupMemberNames', ArrayOf(CharacterString), optional=True)
        , Property('presentValue', ArrayOf(PropertyAccessResult))
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState)
        , Property('memberStatusFlags', StatusFlags)
        , Property('reliability', Reliability, optional=True)
        , Property('outOfService', Boolean)
        , Property('updateInterval', Unsigned, optional=True)
        , Property('requestedUpdateInterval', Unsigned, optional=True)
        , Property('covResubscriptionInterval', Unsigned, optional=True)
        , Property('clientCovIncrement', ClientCOV, optional=True)
        , Property('timeDelay', Unsigned, optional=True)
        , Property('notificationClass', Unsigned, optional=True)
        , Property('eventEnable', EventTransitionBits, optional=True)
        , Property('ackedTransitions', EventTransitionBits, optional=True)
        , Property('notifyType', NotifyType, optional=True)
        , Property('eventTimeStamps', ArrayOf(TimeStamp), optional=True)
        , Property('eventMessageTexts', ArrayOf(CharacterString), optional=True)
        , Property('covuPeriod', Unsigned, optional=True)
        , Property('covuRecipients', SequenceOf(Recipient), optional=True)
        ]

register_object_type(GlobalGroupObject)

class GroupObject(Object):
    objectType = 'group'
    properties = \
        [ Property('listOfGroupMembers', SequenceOf(ReadAccessSpecification))
        , Property('presentValue', SequenceOf(ReadAccessResult))
        ]

register_object_type(GroupObject)

class IntegerValueObject(Object):
    objectType = 'integerValue'
    properties = \
        [ Property('presentValue', Integer)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState, optional=True)
        , Property('reliability', Reliability, optional=True)
        , Property('outOfService', Boolean, optional=True)
        , Property('units', EngineeringUnits)
        , Property('priorityArray', PriorityArray, optional=True)
        , Property('relinquishDefault', Integer, optional=True)
        , Property('covIncrement', Unsigned, optional=True)
        , Property('timeDelay', Unsigned, optional=True)
        , Property('notificationClass', Unsigned, optional=True)
        , Property('highLimit', Integer, optional=True)
        , Property('lowLimit', Integer, optional=True)
        , Property('deadband', Unsigned, optional=True)
        , Property('limitEnable', LimitEnable, optional=True)
        , Property('eventEnable', EventTransitionBits, optional=True)
        , Property('ackedTransitions', EventTransitionBits, optional=True)
        , Property('notifyType', NotifyType, optional=True)
        , Property('eventTimeStamps', ArrayOf(TimeStamp), optional=True)
        , Property('eventMessageTexts', ArrayOf(CharacterString), optional=True)
        ]

register_object_type(IntegerValueObject)

class LargeAnalogValueObject(Object):
    objectType = 'largeAnalogValue'
    properties = \
        [ Property('presentValue', Double)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState, optional=True)
        , Property('reliability', Reliability, optional=True)
        , Property('outOfService', Boolean, optional=True)
        , Property('units', EngineeringUnits)
        , Property('priorityArray', PriorityArray, optional=True)
        , Property('relinquishDefault', Integer, optional=True)
        , Property('covIncrement', Unsigned, optional=True)
        , Property('timeDelay', Unsigned, optional=True)
        , Property('notificationClass', Unsigned, optional=True)
        , Property('highLimit', Double, optional=True)
        , Property('lowLimit', Double, optional=True)
        , Property('deadband', Double, optional=True)
        , Property('limitEnable', LimitEnable, optional=True)
        , Property('eventEnable', EventTransitionBits, optional=True)
        , Property('ackedTransitions', EventTransitionBits, optional=True)
        , Property('notifyType', NotifyType, optional=True)
        , Property('eventTimeStamps', ArrayOf(TimeStamp), optional=True)
        , Property('eventMessageTexts', ArrayOf(CharacterString), optional=True)
        ]

register_object_type(LargeAnalogValueObject)

class LifeSafetyPointObject(Object):
    objectType = 'lifeSafetyPoint'
    properties = \
        [ Property('presentValue', LifeSafetyState)
        , Property('trackingValue', LifeSafetyState)
        , Property('deviceType', CharacterString, optional=True)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState)
        , Property('reliability', Reliability)
        , Property('outOfService', Boolean)
        , Property('mode', LifeSafetyMode, optional=True)
        , Property('acceptedModes', SequenceOf(LifeSafetyMode))
        , Property('timeDelay', Unsigned, optional=True)
        , Property('notificationClass', Unsigned, optional=True)
        , Property('lifeSafetyAlarmValues', SequenceOf(LifeSafetyState), optional=True)
        , Property('alarmValues', SequenceOf(LifeSafetyState), optional=True)
        , Property('faultValues', SequenceOf(LifeSafetyState), optional=True)
        , Property('eventEnable', EventTransitionBits, optional=True)
        , Property('ackedTransitions', EventTransitionBits, optional=True)
        , Property('notifyType', NotifyType, optional=True)
        , Property('eventTimeStamps', ArrayOf(TimeStamp), optional=True)
        , Property('eventMessageTexts', ArrayOf(CharacterString), optional=True)
        , Property('silenced', SilencedState)
        , Property('operationExpected', LifeSafetyOperation)
        , Property('maintenanceRequired', Maintenance, optional=True)
        , Property('setting', Unsigned, optional=True)
        , Property('directReading', Real, optional=True)
        , Property('units', EngineeringUnits, optional=True)
        , Property('memberOf', SequenceOf(DeviceObjectReference), optional=True)
        ]

register_object_type(LifeSafetyPointObject)

class LifeSafetyZoneObject(Object):
    objectType = 'lifeSafetyZone'
    properties = \
        [ Property('presentValue', LifeSafetyState)
        , Property('trackingValue', LifeSafetyState)
        , Property('deviceType', CharacterString, optional=True)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState)
        , Property('reliability', Reliability)
        , Property('outOfService', Boolean)
        , Property('mode', LifeSafetyMode, optional=True)
        , Property('acceptedModes', SequenceOf(LifeSafetyMode))
        , Property('timeDelay', Unsigned, optional=True)
        , Property('notificationClass', Unsigned, optional=True)
        , Property('lifeSafetyAlarmValues', SequenceOf(LifeSafetyState), optional=True)
        , Property('alarmValues', SequenceOf(LifeSafetyState), optional=True)
        , Property('faultValues', SequenceOf(LifeSafetyState), optional=True)
        , Property('eventEnable', EventTransitionBits, optional=True)
        , Property('ackedTransitions', EventTransitionBits, optional=True)
        , Property('notifyType', NotifyType, optional=True)
        , Property('eventTimeStamps', ArrayOf(TimeStamp), optional=True)
        , Property('eventMessageTexts', ArrayOf(CharacterString), optional=True)
        , Property('silenced', SilencedState)
        , Property('operationExpected', LifeSafetyOperation)
        , Property('maintenanceRequired', Boolean, optional=True)
        , Property('zoneMembers', SequenceOf(DeviceObjectReference))
        , Property('memberOf', SequenceOf(DeviceObjectReference), optional=True)
        ]

register_object_type(LifeSafetyZoneObject)

class LoadControlObject(Object):
    objectType = 'loadControl'
    properties = \
        [ Property('presentValue', ShedState)
        , Property('stateDescription', CharacterString, optional=True)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState)
        , Property('reliability', Reliability, optional=True)
        , Property('requestedShedLevel', ShedLevel, optional=True)
        , Property('startTime', DateTime, optional=True)
        , Property('shedDuration', Unsigned, optional=True)
        , Property('dutyWindow', Unsigned, optional=True)
        , Property('enable', Boolean, optional=True)
        , Property('fullDutyBaseline', Real, optional=True)
        , Property('expectedShedLevel', ShedLevel)
        , Property('actualShedLevel', ShedLevel)
        , Property('shedLevels', ArrayOf(Unsigned), optional=True)
        , Property('shedLevelDescriptions', ArrayOf(CharacterString))
        , Property('notificationClass', Unsigned, optional=True)
        , Property('timeDelay', Unsigned, optional=True)
        , Property('eventEnable', EventTransitionBits, optional=True)
        , Property('ackedTransitions', EventTransitionBits, optional=True)
        , Property('notifyType', NotifyType, optional=True)
        , Property('eventTimeStamps', ArrayOf(TimeStamp), optional=True)
        , Property('eventMessageTexts', ArrayOf(CharacterString), optional=True)
        ]

register_object_type(LoadControlObject)

class LoopObject(Object):
    objectType = 'loop'
    properties = \
        [ Property('presentValue', Real)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState)
        , Property('reliability', Reliability, optional=True)
        , Property('outOfService', Boolean)
        , Property('updateInterval', Unsigned)
        , Property('outputUnits', EngineeringUnits)
        , Property('manipulatedVariableReference', ObjectPropertyReference)
        , Property('controlledVariableReference', ObjectPropertyReference)
        , Property('controlledVariableValue', Real)
        , Property('controlledVariableUnits', EngineeringUnits)
        , Property('setpointReference', SetpointReference)
        , Property('setpoint', Real)
        , Property('action', Action)
        , Property('proportionalConstant', Real, optional=True)
        , Property('proportionalConstantUnits', EngineeringUnits, optional=True)
        , Property('integralConstant', Real, optional=True)
        , Property('integralConstantUnits', EngineeringUnits, optional=True)
        , Property('derivativeConstant', Real, optional=True)
        , Property('derivativeConstantUnits', EngineeringUnits, optional=True)
        , Property('bias', Real, optional=True)
        , Property('maximumOutput', Real, optional=True)
        , Property('minimumOutput', Real, optional=True)
        , Property('priorityForWriting', Unsigned)
        , Property('covIncrement', Real, optional=True)
        , Property('timeDelay', Unsigned, optional=True)
        , Property('notificationClass', Unsigned, optional=True)
        , Property('errorLimit', Real, optional=True)
        , Property('deadband', Real, optional=True)
        , Property('eventEnable', EventTransitionBits, optional=True)
        , Property('ackedTransitions', EventTransitionBits, optional=True)
        , Property('notifyType', NotifyType, optional=True)
        , Property('eventTimeStamps', ArrayOf(TimeStamp), optional=True)
        , Property('eventMessageTexts', ArrayOf(CharacterString), optional=True)
        ]

register_object_type(LoopObject)

class MultiStateInputObject(Object):
    objectType = 'multiStateInput'
    properties = \
        [ Property('presentValue',  Unsigned)
        , Property('deviceType',  CharacterString, optional=True)
        , Property('statusFlags',  StatusFlags)
        , Property('eventState',  EventState)
        , Property('reliability',  Reliability, optional=True)
        , Property('outOfService',  Boolean)
        , Property('numberOfStates',  Unsigned)
        , Property('stateText',  ArrayOf(CharacterString), optional=True)
        , Property('timeDelay',  Unsigned, optional=True)
        , Property('notificationClass',  Unsigned, optional=True)
        , Property('alarmValues',  SequenceOf(Unsigned), optional=True)
        , Property('faultValues',  SequenceOf(Unsigned), optional=True)
        , Property('eventEnable',  EventTransitionBits, optional=True)
        , Property('ackedTransitions',  EventTransitionBits, optional=True)
        , Property('notifyType',  NotifyType, optional=True)
        , Property('eventTimeStamps',  ArrayOf(TimeStamp), optional=True)
        , Property('eventMessageTexts',  ArrayOf(CharacterString), optional=True)
        ]

register_object_type(MultiStateInputObject)

class MultiStateOutputObject(Object):
    objectType = 'multiStateOutput'
    properties = \
        [ Property('presentValue', Unsigned, optional=True)
        , Property('deviceType', CharacterString, optional=True)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState)
        , Property('reliability', Reliability, optional=True)
        , Property('outOfService', Boolean)
        , Property('numberOfStates', Unsigned)
        , Property('stateText', ArrayOf(CharacterString), optional=True)
        , Property('priorityArray', PriorityArray)
        , Property('relinquishDefault', Unsigned, optional=True)
        , Property('timeDelay', Unsigned, optional=True)
        , Property('notificationClass', Unsigned, optional=True)
        , Property('feedbackValue', Unsigned, optional=True)
        , Property('eventEnable', EventTransitionBits, optional=True)
        , Property('ackedTransitions', EventTransitionBits, optional=True)
        , Property('notifyType', NotifyType, optional=True)
        , Property('eventTimeStamps', ArrayOf(TimeStamp), optional=True)
        , Property('eventMessageTexts', ArrayOf(CharacterString), optional=True)
        ]

register_object_type(MultiStateOutputObject)

class MultiStateValueObject(Object): 
    objectType = 'multiStateValue'
    properties = \
        [ Property('presentValue', Unsigned)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState)
        , Property('reliability', Reliability, optional=True)
        , Property('outOfService', Boolean)
        , Property('numberOfStates', Unsigned)
        , Property('stateText', ArrayOf(CharacterString), optional=True)
        , Property('priorityArray', PriorityArray, optional=True)
        , Property('relinquishDefault', Unsigned, optional=True)
        , Property('timeDelay', Unsigned, optional=True)
        , Property('notificationClass', Unsigned, optional=True)
        , Property('alarmValues', SequenceOf(Unsigned), optional=True)
        , Property('faultValues', SequenceOf(Unsigned), optional=True)
        , Property('eventEnable', EventTransitionBits, optional=True)
        , Property('ackedTransitions', EventTransitionBits, optional=True)
        , Property('notifyType', NotifyType, optional=True)
        , Property('eventTimeStamps', ArrayOf(TimeStamp), optional=True)
        , Property('eventMessageTexts', ArrayOf(CharacterString), optional=True)
        ]
        
register_object_type(MultiStateValueObject)

class NetworkSecurityObject(Object):
    objectType = 'networkSecurity'
    properties = \
        [ Property('baseDeviceSecurityPolicy', SecurityLevel)
### more
        ]

class NotificationClassObject(Object):
    objectType = 'notificationClass'
    properties = \
        [ Property('notificationClass', Unsigned)
        , Property('priority', ArrayOf(Unsigned))
        , Property('ackRequired', EventTransitionBits)
        , Property('recipientList', SequenceOf(Destination))
        ]

register_object_type(NotificationClassObject)

class OctetStringValueObject(Object):
    objectType = 'octetstringValue'
    properties = \
        [ Property('presentValue', CharacterString, optional=True)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState, optional=True)
        , Property('reliability', Reliability, optional=True)
        , Property('outOfService', Boolean, optional=True)
        , Property('priorityArray', PriorityArray, optional=True)
        , Property('relinquishDefault', OctetString, optional=True)
        ]

register_object_type(OctetStringValueObject)

class PositiveIntegerValueObject(Object):
    objectType = 'positiveIntegerValue'
    properties = \
        [ Property('presentValue', Unsigned)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState, optional=True)
        , Property('reliability', Reliability, optional=True)
        , Property('outOfService', Boolean, optional=True)
        , Property('units', EngineeringUnits)
        , Property('priorityArray', PriorityArray, optional=True)
        , Property('relinquishDefault', Unsigned, optional=True)
        , Property('covIncrement', Unsigned, optional=True)
        , Property('timeDelay', Unsigned, optional=True)
        , Property('notificationClass', Unsigned, optional=True)
        , Property('highLimit', Unsigned, optional=True)
        , Property('lowLimit', Unsigned, optional=True)
        , Property('deadband', Unsigned, optional=True)
        , Property('limitEnable', LimitEnable, optional=True)
        , Property('eventEnable', EventTransitionBits, optional=True)
        , Property('ackedTransitions', EventTransitionBits, optional=True)
        , Property('notifyType', NotifyType, optional=True)
        , Property('eventTimeStamps', ArrayOf(TimeStamp), optional=True)
        , Property('eventMessageTexts', ArrayOf(CharacterString), optional=True)
        ]

register_object_type(PositiveIntegerValueObject)

class ProgramObject(Object):
    objectType = 'program'
    properties = \
        [ Property('programState', ProgramState)
        , Property('programChange', ProgramRequest, optional=True)
        , Property('reasonForHalt', ProgramError, optional=True)
        , Property('descriptionOfHalt', CharacterString, optional=True)
        , Property('programLocation', CharacterString, optional=True)
        , Property('instanceOf', CharacterString, optional=True)
        , Property('statusFlags', StatusFlags)
        , Property('reliability', Reliability, optional=True)
        , Property('outOfService', Boolean)
        ]

register_object_type(ProgramObject)

class PulseConverterObject(Object):
    objectType = 'pulseConverter'
    properties = \
        [ Property('presentValue', Real)
        , Property('inputReference', ObjectPropertyReference, optional=True)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState)
        , Property('reliability', Reliability, optional=True)
        , Property('outOfService', Boolean)
        , Property('units', EngineeringUnits)
        , Property('scaleFactor', Real)
        , Property('adjustValue', Real, optional=True)
        , Property('count', Unsigned)
        , Property('updateTime', DateTime)
        , Property('countChangeTime', DateTime)
        , Property('countBeforeChange', Unsigned)
        , Property('covIncrement', Real, optional=True)
        , Property('covPeriod', Unsigned, optional=True)
        , Property('notificationClass', Unsigned, optional=True)
        , Property('timeDelay', Unsigned, optional=True)
        , Property('highLimit', Real, optional=True)
        , Property('lowLimit', Real, optional=True)
        , Property('deadband', Real, optional=True)
        , Property('limitEnable', LimitEnable, optional=True)
        , Property('eventEnable', EventTransitionBits, optional=True)
        , Property('ackedTransitions', EventTransitionBits, optional=True)
        , Property('notifyType', NotifyType, optional=True)
        , Property('eventTimeStamps', ArrayOf(TimeStamp), optional=True)
        , Property('eventMessageTexts', ArrayOf(CharacterString), optional=True)
        ]

register_object_type(PulseConverterObject)

class ScheduleObject(Object):
    objectType = 'schedule'
    properties = \
        [ Property('presentValue', Any)
        , Property('effectivePeriod', DateRange)
        , Property('weeklySchedule', ArrayOf(DailySchedule), optional=True)
        , Property('exceptionSchedule', ArrayOf(SpecialEvent), optional=True)
        , Property('scheduleDefault', Any)
        , Property('listOfObjectPropertyReferences', SequenceOf(DeviceObjectPropertyReference))
        , Property('priorityForWriting', Unsigned)
        , Property('statusFlags', StatusFlags)
        , Property('reliability', Reliability)
        , Property('outOfService', Boolean)
        ]

register_object_type(ScheduleObject)

class StructuredViewObject(Object):
    objectType = 'structuredView'
    properties = \
        [ Property('nodeType', NodeType)
        , Property('nodeSubtype', CharacterString, optional=True)
        , Property('subordinateList', ArrayOf(DeviceObjectReference))
        , Property('subordinateAnnotations', ArrayOf(CharacterString), optional=True)
        ]

register_object_type(StructuredViewObject)

class TimePatternValueObject(Object):
    objectType = 'timePatternValue'
    properties = \
        [ Property('presentValue', DateTime)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState, optional=True)
        , Property('reliability', Reliability, optional=True)
        , Property('outOfService', Boolean, optional=True)
        , Property('isUtc', Boolean, optional=True)
        , Property('priorityArray', PriorityArray, optional=True)
        , Property('relinquishDefault', DateTime, optional=True)
        ]

register_object_type(TimePatternValueObject)

class TimeValueObject(Object):
    objectType = 'timeValue'
    properties = \
        [ Property('presentValue', Time)
        , Property('statusFlags', StatusFlags)
        , Property('eventState', EventState, optional=True)
        , Property('reliability', Reliability, optional=True)
        , Property('outOfService', Boolean, optional=True)
        , Property('priorityArray', PriorityArray, optional=True)
        , Property('relinquishDefault', Time, optional=True)
        ]

register_object_type(TimeValueObject)

class TrendLogObject(Object):
    objectType = 'trendLog'
    properties = \
        [ Property('enable', Boolean, optional=True)
        , Property('startTime', DateTime, optional=True)
        , Property('stopTime', DateTime, optional=True)
        , Property('logDeviceObjectProperty', DeviceObjectPropertyReference, optional=True)
        , Property('logInterval', Unsigned, optional=True)
        , Property('covResubscriptionInterval', Unsigned, optional=True)
        , Property('clientCovIncrement', ClientCOV, optional=True)
        , Property('stopWhenFull', Boolean)
        , Property('bufferSize', Unsigned)
        , Property('logBuffer', SequenceOf(LogRecord))
        , Property('recordCount', Unsigned, optional=True)
        , Property('totalRecordCount', Unsigned)
        , Property('notificationThreshold', Unsigned, optional=True)
        , Property('recordsSinceNotification', Unsigned, optional=True)
        , Property('lastNotifyRecord', Unsigned, optional=True)
        , Property('eventState', EventState)
        , Property('notificationClass', Unsigned, optional=True)
        , Property('eventEnable', EventTransitionBits, optional=True)
        , Property('ackedTransitions', EventTransitionBits, optional=True)
        , Property('notifyType', NotifyType, optional=True)
        , Property('eventTimeStamps', ArrayOf(TimeStamp), optional=True)
        , Property('eventMessageTexts', ArrayOf(CharacterString), optional=True)
        , Property('loggingType', LoggingType)
        , Property('alignIntervals', Boolean, optional=True)
        , Property('intervalOffset', Unsigned, optional=True)
        , Property('trigger', Boolean, optional=True)
        , Property('statusFlags', StatusFlags)
        , Property('reliability', Reliability, optional=True)
        ]

register_object_type(TrendLogObject)

class TrendLogMultipleObject(Object):
    objectType = 'trendLogMultiple'
    properties = \
        [ Property('statusFlags', StatusFlags)
        , Property('eventState', EventState)
        , Property('reliability', Reliability, optional=True)
        , Property('enable', Boolean, optional=True)
        , Property('startTime', DateTime, optional=True)
        , Property('stopTime', DateTime, optional=True)
        , Property('logDeviceObjectProperty', ArrayOf(DeviceObjectPropertyReference))
        , Property('loggingType', LoggingType)
        , Property('logInterval', Unsigned)
        , Property('alignIntervals', Boolean, optional=True)
        , Property('intervalOffset', Unsigned, optional=True)
        , Property('trigger', Boolean, optional=True)
        , Property('stopWhenFull', Boolean)
        , Property('bufferSize', Unsigned)
        , Property('logBuffer', SequenceOf(LogMultipleRecord))
        , Property('recordCount', Unsigned, optional=True)
        , Property('totalRecordCount', Unsigned)
        , Property('notificationThreshold', Unsigned, optional=True)
        , Property('recordsSinceNotification', Unsigned, optional=True)
        , Property('lastNotifyRecord', Unsigned, optional=True)
        , Property('notificationClass', Unsigned, optional=True)
        , Property('eventEnable', EventTransitionBits, optional=True)
        , Property('ackedTransitions', EventTransitionBits, optional=True)
        , Property('notifyType', NotifyType, optional=True)
        , Property('eventTimeStamps', ArrayOf(TimeStamp), optional=True)
        , Property('eventMessageTexts', ArrayOf(CharacterString), optional=True)
        ]

register_object_type(TrendLogMultipleObject)
