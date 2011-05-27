#!/usr/bin/python

"""
Base Types
"""

from debugging import ModuleLogger

# from pdu import *
from primitivedata import *
from constructeddata import *

# some debuging
_debug = 0
_log = ModuleLogger(globals())

#
#   Arrays
#

ArrayOfObjectIdentifier = ArrayOf(ObjectIdentifier)

#
#   Base Type Bit Strings
#

class BACnetDaysOfWeek(BitString):
    bitNames = \
        { 'monday':0
        , 'tuesday':1
        , 'wednesday':2
        , 'thursday':3
        , 'friday':4
        , 'saturday':5
        , 'sunday':6
        }

class BACnetEventTransitionBits(BitString):
    bitNames = \
        { 'to-offnormal':0
        , 'to-fault':1
        , 'to-normal':2
        }

class BACnetLimitEnable(BitString):
    bitNames = \
        { 'lowLimitEnable':0
        , 'highLimitEnable':1
        }

class BACnetObjectTypesSupported(BitString):
    bitNames = \
        { 'analog-input':0
        , 'analog-output':1
        , 'analog-value':2
        , 'binary-input':3
        , 'binary-output':4
        , 'binary-value':5
        , 'calendar':6
        , 'command':7
        , 'device':8
        , 'event-enrollment':9
        , 'file':10
        , 'group':11
        , 'loop':12
        , 'multi-state-input':13
        , 'multi-state-output':14
        , 'notification-class':15
        , 'program':16
        , 'schedule':17
# Objects added after 1995
        , 'averaging':18
        , 'multi-state-value':19
        , 'trend-log':20
        , 'life-safety-point':21
        , 'life-safety-zone':22
# Objects added after 2001
        , 'accumulator':23
        , 'pulse-converter':24
# Objects added after 2004
        , 'event-log':25
        , 'trend-log-multiple':27
        , 'load-control':28
        , 'structured-view':29
        , 'access-door':30
        }
    bitLen = 31

class BACnetResultFlags(BitString):
    bitNames = \
        { 'first-item':0
        , 'last-item':1
        , 'more-items':2
        }
        
class BACnetServicesSupported(BitString):
    bitNames = \
        { 'acknowledgeAlarm':0
        , 'confirmedCOVNotification':1
        , 'confirmedEventNotification':2
        , 'getAlarmSummary':3
        , 'getEnrollmentSummary':4
        , 'subscribeCOV':5
        , 'atomicReadFile':6
        , 'atomicWriteFile':7
        , 'addListElement':8
        , 'removeListElement':9
        , 'createObject':10
        , 'deleteObject':11
        , 'readProperty':12
        , 'readPropertyConditional':13
        , 'readPropertyMultiple':14
        , 'writeProperty':15
        , 'writePropertyMultiple':16
        , 'deviceCommunicationControl':17
        , 'confirmedPrivateTransfer':18
        , 'confirmedTextMessage':19
        , 'reinitializeDevice':20
        , 'vtOpen':21
        , 'vtClose':22
        , 'vtData':23
        , 'authenticate':24
        , 'requestKey':25
        , 'i-Am':26
        , 'i-Have':27
        , 'unconfirmedCOVNotification':28
        , 'unconfirmedEventNotification':29
        , 'unconfirmedPrivateTransfer':30
        , 'unconfirmedTextMessage':31
        , 'timeSynchronization':32
        , 'who-Has':33
        , 'who-Is':34
        , 'readRange':35
        , 'utcTimeSynchronization':36
        , 'lifeSafetyOperation':37
        , 'subscribeCOVProperty':38
        , 'getEventInformation':39
        }
    bitLen = 40

class BACnetStatusFlags(BitString):
    bitNames = \
        { 'in-alarm':0
        , 'fault':1
        , 'overridden':2
        , 'out-of-service':3
        }
    bitLen = 4

#
#   Base Type Enumerations
#

class BACnetAccumulatorStatus(Enumerated):
    enumerations = \
        { 'normal':0
        , 'starting':1
        , 'recovered':2
        , 'abnormal':3
        , 'failed':4
        }

class BACnetAction(Enumerated):
    enumerations = \
        { 'direct':0
        , 'inverse':1
        }

class BACnetBinaryPV(Enumerated):
    enumerations = \
        { 'inactive':0
        , 'active':1
        }

class BACnetDeviceStatus(Enumerated):
    enumerations = \
        { 'operational':0
        , 'operational-read-only':1
        , 'download-required':2
        , 'download-in-progress':3
        , 'non-operational':4
        }

class BACnetEngineeringUnits(Enumerated):
    enumerations = {
    # Area
          'square-meters':0
        , 'square-feet':1
        
    # Currency
        , 'currency1':105
        , 'currency2':106
        , 'currency3':107
        , 'currency4':108
        , 'currency5':109
        , 'currency6':110
        , 'currency7':111
        , 'currency8':112
        , 'currency9':113
        , 'currency10':114

    # Electrical
        , 'milliamperes':2
        , 'amperes':3
        , 'ohms':4
        , 'kilohms':122
        , 'megohms':123
        , 'volts':5
        , 'millivolts':124
        , 'kilovolts':6
        , 'megavolts':7
        , 'volt-amperes':8
        , 'kilovolt-amperes':9
        , 'megavolt-amperes':10

    # Other
        }

class BACnetEventState(Enumerated):
    enumerations = \
        { 'normal':0
        , 'fault':1
        , 'offnormal':2
        , 'high-limit':3
        , 'low-limit':4
        }

class BACnetEventType(Enumerated):
    enumerations = \
        { 'change-of-bitstring':0
        , 'change-of-state':1
        , 'change-of-value':2
        , 'command-failure':3
        , 'floating-limit':4
        , 'out-of-range':5
        }

class BACnetFileAccessMethod(Enumerated):
    enumerations = \
        { 'record-access':0
        , 'stream-access':1
        , 'record-and-stream-access':2
        }

class BACnetLifeSafetyMode(Enumerated):
    enumerations = \
        { 'off':0
        , 'on':1
        , 'test':2
        , 'manned':3
        , 'unmanned':4
        , 'armed':5
        , 'disarmed':6
        , 'prearmed':7
        , 'slow':8
        , 'fast':9
        , 'disconnected':10
        , 'enabled':11
        , 'disabled':12
        , 'automatic-release-disabled':13
        , 'default':14
        }

class BACnetProgramError(Enumerated):
    enumerations = \
        { 'normal':0
        , 'load-failed':1
        , 'internal':2
        , 'program':3
        , 'other':4
        }

class BACnetProgramRequest(Enumerated):
    enumerations = \
        { 'ready':0
        , 'load':1
        , 'run':2
        , 'halt':3
        , 'restart':4
        , 'unload':5
        }

class BACnetProgramState(Enumerated):
    enumerations = \
        { 'idle':0
        , 'loading':1
        , 'running':2
        , 'waiting':3
        , 'halted':4
        , 'unloading':5
        }

class BACnetPropertyIdentifier(Enumerated):
    enumerations = \
        { 'accepted-modes':175
        , 'acked-transitions':0
        , 'ack-required':1
        , 'action':2
        , 'action-text':3
        , 'active-text':4
        , 'active-vt-sessions':5
        , 'active-cov-subscriptions':152
        , 'actual-sched-level':212
        , 'adjust-value':176
        , 'alarm-value':6
        , 'alarm-values':7
        , 'align-intervals':193
        , 'all':8
        , 'all-writes-successful':9
        , 'apdu-segment-timeout':10
        , 'apdu-timeout':11
        , 'application-software-version':12
        , 'archive':13
        , 'attempted-samples':124
        , 'auto-slave-discovery':169
        , 'average-value':125
        , 'backup-failure-timeout':153
        , 'bias':14
        , 'buffer-size':126
        , 'change-of-state-count':15
        , 'change-of-state-time':16
        , 'client-cov-increment':127
        , 'configuration-files':154
        , 'controlled-variable-reference':19
        , 'controlled-variable-units':20
        , 'controlled-variable-value':21
        , 'count':177
        , 'count-before-change':178
        , 'count-change-time':179
        , 'cov-increment':22
        , 'cov-period':180
        , 'cov-resubscription-interval':128
        , 'database-revision':155
        , 'date-list':23
        , 'daylight-savings-status':24
        , 'deadband':25
        , 'derivative-constant':26
        , 'derivative-constant-units':27
        , 'description':28
        , 'description-of-halt':29
        , 'device-address-binding':30
        , 'device-type':31
        , 'direct-reading':156
        , 'door-alarm-state':226
        , 'door-extended-pulse-time':227
        , 'door-members':228
        , 'door-open-too-long-time':229
        , 'door-pulse-time':230
        , 'door-status':231
        , 'door-unlock-delay-time':232
        , 'duty-window':213
        , 'effective-period':32
        , 'elapsed-active-time':33
        , 'enable':133
        , 'error-limit':34
        , 'event-enable':35
        , 'event-state':36
        , 'event-time-stamps':130
        , 'event-type':37
        , 'event-parameters':83
        , 'exception-schedule':38
        , 'expected-sched-level':214
        , 'fault-values':39
        , 'feedback-value':40
        , 'file-access-method':41
        , 'file-size':42
        , 'file-type':43
        , 'firmware-revision':44
        , 'full-duty-baseline':213
        , 'high-limit':45
        , 'inactive-text':46
        , 'in-process':47
        , 'input-reference':181
        , 'instance-of':48
        , 'integral-constant':49
        , 'integral-constant-units':50
        , 'interval-offset':195
        , 'last-notify-record':173
        , 'last-restart-reason':196
        , 'last-restore-time':157
        , 'life-safety-alarm-values':166
        , 'limit-enable':52
        , 'limit-monitoring-interval':182
        , 'list-of-group-members':53
        , 'list-of-object-property-references':54
        , 'list-of-session-keys':55
        , 'local-date':56
        , 'local-time':57
        , 'location':58
        , 'lock-status':233
        , 'log-buffer':131
        , 'log-device-object-property':132
        # 'log-enable' renamed to 'enable'
        , 'log-interval':134
        , 'logging-object':183
        , 'logging-record':184
        , 'logging-type':197
        , 'low-limit':59
        , 'maintenance-required':158
        , 'manipulated-variable-reference':60
        , 'manual-slave-address-binding':170
        , 'masked-alarm-values':234
        , 'maximum-output':61
        , 'maximum-value':135
        , 'maximum-value-timestamp':149
        , 'max-apdu-length-accepted':62
        , 'max-info-frames':63
        , 'max-master':64
        , 'max-pres-value':65
        , 'max-segments-accepted':167
        , 'member-of':159
        , 'minimum-off-time':66
        , 'minimum-on-time':67
        , 'minimum-output':68
        , 'minimum-value':136
        , 'minimum-value-timestamp':150
        , 'min-pres-value':69
        , 'mode':160
        , 'model-name':70
        , 'modification-date':71
        , 'node-subtype':207
        , 'node-type':208
        , 'notification-class':17
        , 'notification-threshold':137
        , 'notify-type':72
        , 'number-of-apdu-retries':73 # number-of-APDU-retries
        , 'number-of-states':74
        , 'object-identifier':75
        , 'object-list':76
        , 'object-name':77
        , 'object-property-reference':78
        , 'object-type':79
        , 'operation-expected':161
        , 'optional':80
        , 'out-of-service':81
        , 'output-units':82
        , 'polarity':84
        , 'prescale':185
        , 'present-value':85
        , 'priority':86
        , 'pulse-rate':186
        , 'priority-array':87
        , 'priority-for-writing':88
        , 'process-identifier':89
        , 'profile-name':168
        , 'program-change':90
        , 'program-location':91
        , 'program-state':92
        , 'proportional-constant':93
        , 'proportional-constant-units':94
        , 'protocol-conformance-class':95 # deleted in version 1 revision 2
        , 'protocol-object-types-supported':96
        , 'protocol-revision':139
        , 'protocol-services-supported':97
        , 'protocol-version':98
        , 'read-only':99
        , 'reason-for-halt':100
        , 'recipient-list':102
        , 'records-since-notification':140
        , 'record-count':141
        , 'reliability':103
        , 'relinquish-default':104
        , 'requested-sched-level':218
        , 'required':105
        , 'resolution':106
        , 'restart-notification-recipients':202
        , 'scale':187
        , 'scale-factor':188
        , 'schedule-default':174
        , 'secured-status':235
        , 'segmentation-supported':107
        , 'setpoint':108
        , 'setpoint-reference':109
        , 'setting':162
        , 'sched-duration':219
        , 'sched-level-descriptions':220
        , 'sched-levels':221
        , 'silenced':163
        , 'slave-address-binding':171
        , 'slave-proxy-enable':172
        , 'start-time':142
        , 'state-text':110
        , 'status-flags':111
        , 'stop-time':143
        , 'stop-when-full':144
        , 'structured-object-list':209
        , 'subordinate-annotations':210
        , 'subordinate-list':211
        , 'system-status':112
        , 'time-delay':113
        , 'time-of-active-time-reset':114
        , 'time-of-device-restart':203
        , 'time-of-state-count-reset':115
        , 'time-synchronization-interval':204
        , 'time-synchronization-recipients':116
        , 'total-record-count':145
        , 'tracking-value':164
        , 'trigger':205
        , 'units':117
        , 'update-interval':118
        , 'update-time':189
        , 'utc-offset':119
        , 'utc-time-synchronization-recipients':206
        , 'valid-samples':146
        , 'value-before-change':190
        , 'value-set':191
        , 'value-change-time':192
        , 'variance-value':151
        , 'vendor-identifier':120
        , 'vendor-name':121
        , 'vt-classes-supported':122
        , 'weekly-schedule':123
        , 'window-interval':147
        , 'window-samples':148
        , 'zone-members':165
        }

class BACnetNotifyType(Enumerated):
    enumerations = \
        { 'alarm':0
        , 'event':1
        , 'ack-notification':2
        }

class BACnetPolarity(Enumerated):
    enumerations = \
        { 'normal':0
        , 'reverse':1
        }

class BACnetPrescale(Sequence):
    sequenceElements = \
        [ Element('multiplier', Unsigned, 0)
        , Element('moduloDivide', Unsigned, 1)
        ]

class BACnetReliability(Enumerated):
    enumerations = \
        { 'no-fault-detected':0
        , 'no-sensor':1
        , 'over-range':2
        , 'under-range':3
        , 'open-loop':4
        , 'shorted-loop':5
        , 'no-output':6
        , 'unreliable-other':7
        , 'process-error':8
        , 'multi-state-fault':9
        , 'configuration-error':10
        }

class BACnetScale(Choice):
    choiceElements = \
        [ Element('floatScale', Real)
        , Element('integerScale', Integer)
        ]

class BACnetSegmentation(Enumerated):
    enumerations = \
        { 'segmented-both':0
        , 'segmented-transmit':1
        , 'segmented-receive':2
        , 'no-segmentation':3
        }

class BACnetVTClass(Enumerated):
    enumerations = \
        { 'default-terminal':0
        , 'ansi-x3-64':1
        , 'dec-vt52':2
        , 'dec-vt100':3
        , 'dec-vt220':4
        , 'hp-700-94':5
        , 'ibm-3130':6
        }

class BACnetNodeType(Enumerated):
    enumerations = \
        { 'unknown':0
        , 'system':1
        , 'network':2
        , 'device':3
        , 'organizational':4
        , 'area':5
        , 'equipment':6
        , 'point':7
        , 'collection':8
        , 'property':9
        , 'functional':10
        , 'other':11
        }

#
#   Base Type Structures
#

class BACnetActionCommand(Sequence):
    sequenceElements = \
        [ Element('deviceIdentifier', ObjectIdentifier, 0, True)
        , Element('objectIdentifier', ObjectIdentifier, 1)
        , Element('propertyIdentifier', BACnetPropertyIdentifier, 2)
        , Element('propertyArrayIndex', Unsigned, 3, True)
        , Element('propertyValue', Any, 4)
        , Element('priority', Unsigned, 5, True)
        , Element('postDelay', Unsigned, 6, True)
        , Element('quiteOnFailure', Boolean, 7)
        , Element('writeSuccessFul', Boolean, 8)
        ]

class BACnetActionList(Sequence):
    sequenceElements = \
        [ Element('action', SequenceOf(BACnetActionCommand))
        ]

class BACnetAddress(Sequence):
    sequenceElements = \
        [ Element('networkNumber', Unsigned)
        , Element('macAddress', OctetString)
        ]

class BACnetAddressBinding(Sequence):
    sequenceElements = \
        [ Element('deviceObjectIdentifier', ObjectIdentifier)
        , Element('deviceAddress', BACnetAddress)
        ]

class BACnetDateRange(Sequence):
    sequenceElements = \
        [ Element('startDate', Date)
        , Element('endDate', Date)
        ]

class BACnetWeekNDay(OctetString):

    def __str__(self):
        if len(self.value) != 3:
            return "BACnetWeekNDay(?): " + OctetString.__str__(self)
        else:
            return "BACnetWeekNDay(%d, %d, %d)" % (ord(self.value[0]), ord(self.value[1]), ord(self.value[2]))

class BACnetCalendarEntry(Choice):
    choiceElements = \
        [ Element('date', Date, 0)
        , Element('dateRange', BACnetDateRange, 1)
        , Element('weekNDay', BACnetWeekNDay, 2)
        ]

class BACnetTimeValue(Sequence):
    sequenceElements = \
        [ Element('time', Time)
        , Element('value', Any)
        ]

class BACnetDailySchedule(Sequence):
    sequenceElements = \
        [ Element('daySchedule', SequenceOf(BACnetTimeValue), 0)
        ]

class BACnetDateTime(Sequence):
    sequenceElements = \
        [ Element('date', Date)
        , Element('time', Time)
        ]

class BACnetRecipient(Choice):
    choiceElements = \
        [ Element('device', ObjectIdentifier, 0)
        , Element('address', BACnetAddress, 1)
        ]

class BACnetDestination(Sequence):
    sequenceElements = \
        [ Element('validDays', BACnetDaysOfWeek)
        , Element('fromTime', Time)
        , Element('toTime', Time)
        , Element('recipient', BACnetRecipient)
        , Element('processIdentifier', Unsigned)
        , Element('issueConfirmedNotifications', Boolean)
        , Element('transitions', BACnetEventTransitionBits)
        ]

#-----

class BACnetPropertyStates(Choice):
    choiceElements = \
        [ Element('booleanValue', Boolean, 0)
        , Element('binaryValue', BACnetBinaryPV, 1)
        , Element('eventType', BACnetEventType, 2)
        , Element('polarity', BACnetPolarity, 3)
        , Element('programChange', BACnetProgramRequest, 4)
        , Element('programState', BACnetProgramState, 5)
        , Element('reasonForHalt', BACnetProgramError, 6)
        , Element('reliability', BACnetReliability, 7)
        , Element('state', BACnetEventState, 8)
        , Element('systemStatus', BACnetDeviceStatus, 9)
        , Element('units', BACnetEngineeringUnits, 10)
        ]

class NotificationChangeOfBitstring(Sequence):
    sequenceElements = \
        [ Element('referencedBitstring', BitString, 0)
        , Element('statusFlags', BACnetStatusFlags, 1)
        ]

class NotificationChangeOfState(Sequence):
    sequenceElements = \
        [ Element('newState', BACnetPropertyStates, 0)
        , Element('statusFlags', BACnetStatusFlags, 1)
        ]
        
class NotificationChangeOfValueNewValue(Choice):
    sequenceElements = \
        [ Element('changedBits', BitString, 0)
        , Element('changedValue', Real, 1)
        ]
        
class NotificationChangeOfValue(Sequence):
    sequenceElements = \
        [ Element('newValue', NotificationChangeOfValueNewValue, 0)
        , Element('statusFlags', BACnetStatusFlags, 1)
        ]
        
class NotificationCommandFailure(Sequence):
    sequenceElements = \
        [ Element('commandValue', Any, 0)
        , Element('statusFlags', BACnetStatusFlags, 1)
        , Element('feedbackValue', Any, 2)
        ]

class NotificationFloatingLimit(Sequence):
    sequenceElements = \
        [ Element('referenceValue', Real, 0)
        , Element('statusFlags', BACnetStatusFlags, 1)
        , Element('setpointValue', Real, 2)
        , Element('errorLimit', Real, 3)
        ]

class NotificationOutOfRange(Sequence):
    sequenceElements = \
        [ Element('exceedingValue', Real, 0)
        , Element('statusFlags', BACnetStatusFlags, 1)
        , Element('deadband', Real, 2)
        , Element('exceededLimit', Real, 3)
        ]

class NotificationComplexEventType(Any): pass
class NotificationChangeOfLifeSafety(Any): pass
class NotificationExtended(Any): pass
class NotificationBufferReady(Any): pass
class NotificationUnsignedRange(Any): pass

class BACnetNotificationParameters(Choice):
    choiceElements = \
        [ Element('changeOfBitstring', NotificationChangeOfBitstring, 0)
        , Element('changeOfState', NotificationChangeOfState, 1)
        , Element('changeOfValue', NotificationChangeOfValue, 2)
        , Element('commandFailure', NotificationCommandFailure, 3)
        , Element('floatingLimit', NotificationFloatingLimit, 4)
        , Element('outOfRange', NotificationOutOfRange, 5)
        , Element('complexEventType', NotificationComplexEventType, 6)
        , Element('changeOfLifeSafety', NotificationChangeOfLifeSafety, 8)
        , Element('extended', NotificationExtended, 9)
        , Element('bufferReady', NotificationBufferReady, 10)
        , Element('unsignedRange', NotificationUnsignedRange, 11)
        ]

#-----

class BACnetObjectPropertyReference(Sequence):
    sequenceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 0)
        , Element('propertyIdentifier', BACnetPropertyIdentifier, 1)
        , Element('propertyArrayIndex', Unsigned, 2, True)
        ]
        
class BACnetObjectPropertyValue(Sequence):
    pass

# already specified in primitivedata
class BACnetObjectType(ObjectType):
    pass

class BACnetPriorityValue(Choice):
    choiceElements = \
        [ Element('null', Null)
        , Element('real', Real)
        , Element('binary', BACnetBinaryPV)
        , Element('integer', Unsigned)
        , Element('constructedValue', Any, 0)
        ]

BACnetPriorityArray = ArrayOf(BACnetPriorityValue)

class BACnetPropertyReference(Sequence):
    sequenceElements = \
        [ Element('propertyIdentifier', BACnetPropertyIdentifier, 0)
        , Element('propertyArrayIndex', Unsigned, 1, True)
        ]

class BACnetPropertyValue(Sequence):
    sequenceElements = \
        [ Element('propertyIdentifier', BACnetPropertyIdentifier, 0)
        , Element('propertyArrayIndex', Unsigned, 1, True)
        , Element('value', Any, 2)
        , Element('priority', Unsigned, 3, True)
        ]

class BACnetRecipientProcess(Sequence):
    sequenceElements = \
        [ Element('recipient', BACnetRecipient, 0)
        , Element('processIdentifier', Unsigned, 1)
        ]

class BACnetSessionKey(Sequence):
    sequenceElements = \
        [ Element('sessionKey', OctetString)
        , Element('peerAddress', BACnetAddress, 1)
        ]

class BACnetSetpointReference(Sequence):
    sequenceElements = \
        [ Element('setpointReference', BACnetObjectPropertyReference, 0, True)
        ]

class BACnetSpecialEvent(Sequence):
    pass

class BACnetTimeStamp(Choice):
    choiceElements = \
        [ Element('time', Time, 0)
        , Element('sequenceNumber', Unsigned, 1)
        , Element('dateTime', BACnetDateTime, 2)
        ]

class BACnetVTSession(Sequence):
    sequenceElements = \
        [ Element('local-vtSessionID', Unsigned)
        , Element('remote-vtSessionID', Unsigned)
        , Element('remote-vtAddress', BACnetAddress)
        ]

#-----

class BACnetDeviceObjectReference(Sequence):
    sequenceElements = \
        [ Element('deviceIdentifier', ObjectIdentifier, 0, True)
        , Element('objectIdentifier', ObjectIdentifier, 1)
        ]

