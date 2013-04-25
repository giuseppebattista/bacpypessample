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
#   Bit Strings
#

class DaysOfWeek(BitString):
    _owl_prefix = 'dow'
    bitNames = \
        { 'monday':0
        , 'tuesday':1
        , 'wednesday':2
        , 'thursday':3
        , 'friday':4
        , 'saturday':5
        , 'sunday':6
        }

class EventTransitionBits(BitString):
    _owl_prefix = 'etb'
    bitNames = \
        { 'toOffnormal':0
        , 'toFault':1
        , 'toNormal':2
        }

class LimitEnable(BitString):
    _owl_prefix = 'le'
    bitNames = \
        { 'lowLimitEnable':0
        , 'highLimitEnable':1
        }

class LogStatus(BitString):
    _owl_prefix = 'ls'
    bitNames = \
        { 'logDisabled':0
        , 'bufferPurged':1
        , 'logInterrupted':2
        }
    bitLen = 3

class ObjectTypesSupported(BitString):
    _owl_prefix = 'ots'
    bitNames = \
        { 'analogInput':0 
        , 'analogOutput':1
        , 'analogValue':2
        , 'binaryInput':3
        , 'binaryOutput':4
        , 'binaryValue':5
        , 'calendar':6
        , 'command':7
        , 'device':8
        , 'eventEnrollment':9
        , 'file':10
        , 'group':11
        , 'loop':12
        , 'multiStateInput':13
        , 'multiStateOutput':14
        , 'notificationClass':15
        , 'program':16
        , 'schedule':17
        , 'averaging':18
        , 'multiStateValue':19
        , 'trendLog':20
        , 'lifeSafetyPoint':21
        , 'lifeSafetyZone':22
        , 'accumulator':23
        , 'pulseConverter':24
        , 'eventLog':25
        , 'globalGroup':26
        , 'trendLogMultiple':27
        , 'loadControl':28
        , 'structuredView':29
        , 'accessDoor':30
        , 'accessPoint':33
        , 'accessRights':34
        , 'accessUser':35
        , 'accessZone':36
        , 'credentialDataInput':37
        , 'networkSecurity':38
        , 'bitstringValue':39
        , 'characterstringValue':40
        , 'datePatternValue':41
        , 'dateValue':42
        , 'datetimePatternValue':43
        , 'datetimeValue':44
        , 'integerValue':45
        , 'largeAnalogValue':46
        , 'octetstringValue':47
        , 'positiveIntegerValue':48
        , 'timePatternValue':49
        , 'timeValue':50
        }
    bitLen = 51

class ResultFlags(BitString):
    _owl_prefix = 'rf'
    bitNames = \
        { 'firstItem':0
        , 'lastItem':1
        , 'moreItems':2
        }
    bitLen = 3

class ServicesSupported(BitString):
    _owl_prefix = 'ss'
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
      # , 'readPropertyConditional':13      # removed in version 1 revision 12
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
      # , 'authenticate':24                 # removed in version 1 revision 11
      # , 'requestKey':25                   # removed in version 1 revision 11
        , 'iAm':26
        , 'iHave':27
        , 'unconfirmedCOVNotification':28
        , 'unconfirmedEventNotification':29
        , 'unconfirmedPrivateTransfer':30
        , 'unconfirmedTextMessage':31
        , 'timeSynchronization':32
        , 'whoHas':33
        , 'whoIs':34
        , 'readRange':35
        , 'utcTimeSynchronization':36
        , 'lifeSafetyOperation':37
        , 'subscribeCOVProperty':38
        , 'getEventInformation':39
        }
    bitLen = 40

class StatusFlags(BitString):
    _owl_prefix = 'sf'
    bitNames = \
        { 'inAlarm':0
        , 'fault':1
        , 'overridden':2
        , 'outOfService':3
        }
    bitLen = 4

#
#   Enumerations
#

class AccessAuthenticationFactorDisable(Enumerated):
    _owl_prefix = 'aafd'
    _owl_lolim = 64
    _owl_hilim = 65535
    enumerations = \
        { 'none':0
        , 'disabled':1
        , 'disabledLost':2
        , 'disabledStolen':3
        , 'disabledDamaged':4
        , 'disabledDestroyed':5
        }

class AccessCredentialDisable(Enumerated):
    _owl_prefix = 'acd'
    _owl_lolim = 64
    _owl_hilim = 65535
    enumerations = \
        { 'none':0
        , 'disable':1
        , 'disableManual':2
        , 'disableLockout':3
        }

class AccessCredentialDisableReason(Enumerated):
    _owl_prefix = 'acdr'
    enumerations = \
        { 'disabled':0
        , 'disabledNeedsProvisioning':1
        , 'disabledUnassigned':2
        , 'disabledNotYetActive':3
        , 'disabledExpired':4
        , 'disabledLockout':5
        , 'disabledMaxDays':6
        , 'disabledMaxUses':7
        , 'disabledInactivity':8
        , 'disabledManual':9
        }

class AccessEvent(Enumerated):
    _owl_prefix = 'ae'
    _owl_lolim = 512
    _owl_hilim = 65535
    enumerations = \
        { 'none':0
        , 'granted':1
        , 'muster':2
        , 'passbackDetected':3
        , 'duress':4
        , 'trace':5
        , 'lockoutMaxAttempts':6
        , 'lockoutOther':7
        , 'lockoutRelinquished':8
        , 'lockedByHigherPriority':9
        , 'outOfService':10
        , 'outOfServiceRelinquished':11
        , 'accompanimentBy':12
        , 'authenticationFactorRead':13
        , 'authorizationDelayed':14
        , 'verificationRequired':15
        , 'deniedDenyAll':128
        , 'deniedUnknownCredential':129
        , 'deniedAuthenticationUnavailable':130
        , 'deniedAuthenticationFactorTimeout':131
        , 'deniedIncorrectAuthenticationFactor':132
        , 'deniedZoneNoAccessRights':133
        , 'deniedPointNoAccessRights':134
        , 'deniedNoAccessRights':135
        , 'deniedOutOfTimeRange':136
        , 'deniedThreatLevel':137
        , 'deniedPassback':138
        , 'deniedUnexpectedLocationUsage':139
        , 'deniedMaxAttempts':140
        , 'deniedLowerOccupancyLimit':141
        , 'deniedUpperOccupancyLimit':142
        , 'deniedAuthenticationFactorLost':143
        , 'deniedAuthenticationFactorStolen':144
        , 'deniedAuthenticationFactorDamaged':145
        , 'deniedAuthenticationFactorDestroyed':146
        , 'deniedAuthenticationFactorDisabled':147
        , 'deniedAuthenticationFactorError':148
        , 'deniedCredentialUnassigned':149
        , 'deniedCredentialNotProvisioned':150
        , 'deniedCredentialNotYetActive':151
        , 'deniedCredentialExpired':152
        , 'deniedCredentialManualDisable':153
        , 'deniedCredentialLockout':154
        , 'deniedCredentialMaxDays':155
        , 'deniedCredentialMaxUses':156
        , 'deniedCredentialInactivity':157
        , 'deniedCredentialDisabled':158
        , 'deniedNoAccompaniment':159
        , 'deniedIncorrectAccompaniment':160
        , 'deniedLockout':161
        , 'deniedVerificationFailed':162
        , 'deniedVerificationTimeout':163
        , 'deniedOther':164
        }

class AccessPassbackMode(Enumerated):
    _owl_prefix = 'apm'
    enumerations = \
        { 'passbackOff':0
        , 'hardPassback':1
        , 'softPassback':2
        }

class AccessRuleTimeRangeSpecifier(Enumerated):
    _owl_prefix = 'artrs'
    enumerations = \
        { 'specified':0
        , 'always':1
        }

class AccessRuleLocationSpecifier(Enumerated):
    _owl_prefix = 'arls'
    enumerations = \
        { 'specified':0
        , 'all':1
        }

class AccessUserType(Enumerated):
    _owl_prefix = 'aut'
    _owl_lolim = 64
    _owl_hilim = 65535
    enumerations = \
        { 'asset':0
        , 'group':1
        , 'person':2
        }

class AccessZoneOccupancyState(Enumerated):
    _owl_prefix = 'azos'
    _owl_lolim = 64
    _owl_hilim = 65535
    enumerations = \
        { 'normal':0
        , 'belowLowerLimit':1
        , 'atLowerLimit':2
        , 'atUpperLimit':3
        , 'aboveUpperLimit':4
        , 'disabled':5
        , 'notSupported':6
        }

class AccumulatorRecordAccumulatorStatus(Enumerated):
    _owl_prefix = 'aras'
    enumerations = \
        { 'normal':0
        , 'starting':1
        , 'recovered':2
        , 'abnormal':3
        , 'failed':4
        }

class Action(Enumerated):
    _owl_prefix = 'action'
    enumerations = \
        { 'direct':0
        , 'reverse':1
        }

class AuthenticationFactorType(Enumerated):
    _owl_prefix = 'aft'
    enumerations = \
        { 'undefined':0
        , 'error':1
        , 'custom':2
        , 'simpleNumber16':3
        , 'simpleNumber32':4
        , 'simpleNumber56':5
        , 'simpleAlphaNumeric':6
        , 'abaTrack2':7
        , 'wiegand26':8
        , 'wiegand37':9
        , 'wiegand37facility':10
        , 'facility16card32':11
        , 'facility32card32':12
        , 'fascN':13
        , 'fascNbcd':14
        , 'fascNlarge':15
        , 'fascNlargeBcd':16
        , 'gsa75':17
        , 'chuid':18
        , 'chuidFull':19
        , 'guid':20
        , 'cbeffA':21
        , 'cbeffB':22
        , 'cbeffC':23
        , 'userPassword':24
        }

class AuthenticationStatus(Enumerated):
    _owl_prefix = 'authStatus'
    enumerations = \
        { 'notReady':0
        , 'ready':1
        , 'disabled':2
        , 'waitingForAuthenticationFactor':3
        , 'waitingForAccompaniment':4
        , 'waitingForVerification':5
        , 'inProgress':6
        }

class AuthorizationException(Enumerated):
    _owl_prefix = 'authExcpt'
    _owl_lolim = 64
    _owl_hilim = 255
    enumerations = \
        { 'passback':0
        , 'occupancyCheck':1
        , 'accessRights':2
        , 'lockout':3
        , 'deny':4
        , 'verification':5
        , 'authorizationDelay':6
        }

class AuthorizationMode(Enumerated):
    _owl_prefix = 'authMode'
    _owl_lolim = 64
    _owl_hilim = 65536
    enumerations = \
        { 'authorize':0
        , 'grantActive':1
        , 'denyAll':2
        , 'verificationRequired':3
        , 'authorizationDelayed':4
        , 'none':5
        }

class BackupState(Enumerated):
    _owl_prefix = 'bs'
    enumerations = \
        { 'idle':0
        , 'preparingForBackup':1
        , 'preparingForRestore':2
        , 'performingABackup':3
        , 'performingARestore':4
        , 'backupFailure':5
        , 'restoreFailure':5
        }

class BinaryPV(Enumerated):
    _owl_prefix = 'bpv'
    enumerations = \
        { 'inactive':0
        , 'active':1
        }

class DeviceStatus(Enumerated):
    _owl_prefix = 'devStatus'
    _owl_lolim = 64
    _owl_hilim = 65535
    enumerations = \
        { 'operational':0
        , 'operationalReadOnly':1
        , 'downloadRequired':2
        , 'downloadInProgress':3
        , 'nonOperational':4
        }

class DoorAlarmState(Enumerated):
    _owl_prefix = 'das'
    _owl_lolim = 256
    _owl_hilim = 65535
    enumerations = \
        { 'normal':0
        , 'alarm':1
        , 'doorOpenTooLong':2
        , 'forcedOpen':3
        , 'tamper':4
        , 'doorFault':5
        , 'lockDown':6
        , 'freeAccess':7
        , 'egressOpen':8
        }

class DoorSecuredStatus(Enumerated):
    _owl_prefix = 'dss'
    enumerations = \
        { 'secured':0
        , 'unsecured':1
        , 'unknown':2
        }

class DoorStatus(Enumerated):
    _owl_prefix = 'doorStatus'
    enumerations = \
        { 'closed':0
        , 'opened':1
        , 'unknown':2
        }

class DoorValue(Enumerated):
    _owl_prefix = 'dv'
    enumerations = \
        { 'lock':0
        , 'unlock':1
        , 'pulseUnlock':2
        , 'extendedPulseUnlock':3
        }

class EngineeringUnits(Enumerated):
    _owl_prefix = 'eu'
    _owl_lolim = 256
    _owl_hilim = 65535
    enumerations = \
        {
        #Acceleration
          'metersPerSecondPerSecond':166
        , 'squareMeters':0
        , 'squareCentimeters':116
        , 'squareFeet':1
        , 'squareInches':115
        #Currency
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
        #Electrical
        , 'milliamperes':2
        , 'amperes':3
        , 'amperesPerMeter':167
        , 'amperesPerSquareMeter':168
        , 'ampereSquareMeters':169
        , 'decibels':199
        , 'decibelsMillivolt':200
        , 'decibelsVolt':201
        , 'farads':170
        , 'henrys':171
        , 'ohms':4
        , 'ohmMeters':172
        , 'milliohms':145
        , 'kilohms':122
        , 'megohms':123
        , 'microSiemens':190
        , 'millisiemens':202
        , 'siemens':173
        , 'siemensPerMeter':174
        , 'teslas':175
        , 'volts':5
        , 'millivolts':124
        , 'kilovolts':6
        , 'megavolts':7
        , 'voltAmperes':8
        , 'kilovoltAmperes':9
        , 'megavoltAmperes':10
        , 'voltAmperesReactive':11
        , 'kilovoltAmperesReactive':12
        , 'megavoltAmperesReactive':13
        , 'voltsPerDegreeKelvin':176
        , 'voltsPerMeter':177
        , 'degreesPhase':14
        , 'powerFactor':15
        , 'webers':178
        # Energy
        , 'joules':16
        , 'kilojoules':17
        , 'kilojoulesPerKilogram':125
        , 'megajoules':126
        , 'wattHours':18
        , 'kilowattHours':19
        , 'megawattHours':146
        , 'wattHoursReactive':203
        , 'kilowattHoursReactive':204
        , 'megawattHoursReactive':205
        , 'btus':20
        , 'kiloBtus':147
        , 'megaBtus':148
        , 'therms':21
        , 'tonHours':22
        # Enthalpy 
        , 'joulesPerKilogramDryAir':23
        , 'kilojoulesPerKilogramDryAir':149
        , 'megajoulesPerKilogramDryAir':150
        , 'btusPerPoundDryAir':24
        , 'btusPerPound':117
        , 'joulesPerDegreeKelvin':127
        # Entropy
        , 'kilojoulesPerDegreeKelvin':151
        , 'megajoulesPerDegreeKelvin':152
        , 'joulesPerKilogramDegreeKelvin':128
        # Force
        , 'newton':153
        # Frequency
        , 'cyclesPerHour':25
        , 'cyclesPerMinute':26
        , 'hertz':27
        , 'kilohertz':129
        , 'megahertz':130
        , 'perHour':131
        , 'gramsOfWaterPerKilogramDryAir':28
        , 'percentRelativeHumidity':29
        , 'micrometers':194
        , 'millimeters':30
        , 'centimeters':118
        , 'kilometers':193
        , 'meters':31
        , 'inches':32
        , 'feet':33
        , 'candelas':179
        , 'candelasPerSquareMeter':180
        , 'wattsPerSquareFoot':34
        , 'wattsPerSquareMeter':35
        , 'lumens':36
        , 'luxes':37
        , 'footCandles':38
        , 'milligrams':196
        , 'grams':195
        , 'kilograms':39
        , 'poundsMass':40
        , 'tons':41
        , 'gramsPerSecond':154
        , 'gramsPerMinute':155
        , 'kilogramsPerSecond':42
        , 'kilogramsPerMinute':43
        , 'kilogramsPerHour':44
        , 'poundsMassPerSecond':119
        , 'poundsMassPerMinute':45
        , 'poundsMassPerHour':46
        , 'tonsPerHour':156
        , 'milliwatts':132
        , 'watts':47
        , 'kilowatts':48
        , 'megawatts':49
        , 'btusPerHour':50
        , 'kiloBtusPerHour':157
        , 'horsepower':51
        , 'tonsRefrigeration':52
        , 'pascals':53
        , 'hectopascals':133
        , 'kilopascals':54
        , 'millibars':134
        , 'bars':55
        , 'poundsForcePerSquareInch':56
        , 'millimetersOfWater':206
        , 'centimetersOfWater':57
        , 'inchesOfWater':58
        , 'millimetersOfMercury':59
        , 'centimetersOfMercury':60
        , 'inchesOfMercury':61
        , 'degreesCelsius':62
        , 'degreesKelvin':63
        , 'degreesKelvinPerHour':181
        , 'degreesKelvinPerMinute':182
        , 'degreesFahrenheit':64
        , 'degreeDaysCelsius':65
        , 'degreeDaysFahrenheit':66
        , 'deltaDegreesFahrenheit':120
        , 'deltaDegreesKelvin':121
        , 'years':67
        , 'months':68
        , 'weeks':69
        , 'days':70
        , 'hours':71
        , 'minutes':72
        , 'seconds':73
        , 'hundredthsSeconds':158
        , 'milliseconds':159
        , 'newtonMeters':160
        , 'millimetersPerSecond':161
        , 'millimetersPerMinute':162
        , 'metersPerSecond':74
        , 'metersPerMinute':163
        , 'metersPerHour':164
        , 'kilometersPerHour':75
        , 'feetPerSecond':76
        , 'feetPerMinute':77
        , 'milesPerHour':78
        , 'cubicFeet':79
        , 'cubicMeters':80
        , 'imperialGallons':81
        , 'milliliters':197
        , 'liters':82
        , 'usGallons':83
        , 'cubicFeetPerSecond':142
        , 'cubicFeetPerMinute':84
        , 'cubicFeetPerHour':191
        , 'cubicMetersPerSecond':85
        , 'cubicMetersPerMinute':165
        , 'cubicMetersPerHour':135
        , 'imperialGallonsPerMinute':86
        , 'millilitersPerSecond':198
        , 'litersPerSecond':87
        , 'litersPerMinute':88
        , 'litersPerHour':136
        , 'usGallonsPerMinute':89
        , 'usGallonsPerHour':192
        , 'degreesAngular':90
        , 'degreesCelsiusPerHour':91
        , 'degreesCelsiusPerMinute':92
        , 'degreesFahrenheitPerHour':93
        , 'degreesFahrenheitPerMinute':94
        , 'jouleSeconds':183
        , 'kilogramsPerCubicMeter':186
        , 'kilowattHoursPerSquareMeter':137
        , 'kilowattHoursPerSquareFoot':138
        , 'megajoulesPerSquareMeter':139
        , 'megajoulesPerSquareFoot':140
        , 'noUnits':95
        , 'newtonSeconds':187
        , 'newtonsPerMeter':188
        , 'partsPerMillion':96
        , 'partsPerBillion':97
        , 'percent':98
        , 'percentObscurationPerFoot':143
        , 'percentObscurationPerMeter':144
        , 'percentPerSecond':99
        , 'perMinute':100
        , 'perSecond':101
        , 'psiPerDegreeFahrenheit':102
        , 'radians':103
        , 'radiansPerSecond':184
        , 'revolutionsPerMinute':104
        , 'squareMetersPerNewton':185
        , 'wattsPerMeterPerDegreeKelvin':189
        , 'wattsPerSquareMeterDegreeKelvin':141
        , 'perMille':207
        , 'gramsPerGram':208
        , 'kilogramsPerKilogram':209
        , 'gramsPerKilogram':210
        , 'milligramsPerGram':211
        , 'milligramsPerKilogram':212
        , 'gramsPerMilliliter':213
        , 'gramsPerLiter':214
        , 'milligramsPerLiter':215
        , 'microgramsPerLiter':216
        , 'gramsPerCubicMeter':217
        , 'milligramsPerCubicMeter':218
        , 'microgramsPerCubicMeter':219
        , 'nanogramsPerCubicMeter':220
        , 'gramsPerCubicCentimeter':221
        , 'becquerels':222
        , 'kilobecquerels':223
        , 'megabecquerels':224
        , 'gray':225
        , 'milligray':226
        , 'microgray':227
        , 'sieverts':228
        , 'millisieverts':229
        , 'microsieverts':230
        , 'microsievertsPerHour':231
        , 'decibelsA':232
        , 'nephelometricTurbidityUnit':233
        , 'pH':234
        , 'gramsPerSquareMeter':235
        , 'minutesPerDegreeKelvin':236
        }

class ErrorClass(Enumerated):
    _owl_prefix = 'errClass'
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
    _owl_prefix = 'errCode'
    enumerations = \
        { 'abortApduTooLong':123
        , 'abortApplicationExceededReplyTime':124
        , 'abortBufferOverflow':51
        , 'abortInsufficientSecurity':135
        , 'abortInvalidApduInThisState':52
        , 'abortOther':56
        , 'abortOutOfResources':125
        , 'abortPreemptedByHigherPriorityTask':53
        , 'abortProprietary':55
        , 'abortSecurityError':136
        , 'abortSegmentationNotSupported':54
        , 'abortProprietary':55
        , 'abortOther':56
        , 'abortTsmTimeout':126
        , 'abortWindowSizeOutOfRange':127
        , 'accessDenied':85
        , 'addressingError':115
        , 'badDestinationAddress':86
        , 'badDestinationDeviceId':87
        , 'badSignature':88
        , 'badSourceAddress':89
        , 'badTimestamp':90
        , 'busy':82
        , 'cannotUseKey':91
        , 'cannotVerifyMessageId':92
        , 'characterSetNotSupported':41
        , 'communicationDisabled':83
        , 'configurationInProgress':2
        , 'correctKeyRevision':93
        , 'covSubscriptionFailed':43 
        , 'datatypeNotSupported':47
        , 'deleteFdtEntryFailed':120
        , 'deviceBusy':3
        , 'destinationDeviceIdRequired':94
        , 'distributeBroadcastFailed':121
        , 'duplicateMessage':95
        , 'duplicateName':48
        , 'duplicateObjectId':49
        , 'dynamicCreationNotSupported':4
        , 'encryptionNotConfigured':96
        , 'encryptionRequired':97
        , 'fileAccessDenied':5
        , 'fileFull':128
        , 'inconsistentConfiguration':129
        , 'inconsistentObjectType':130
        , 'inconsistentParameters':7
        , 'inconsistentSelectionCriterion':8
        , 'incorrectKey':98
        , 'internalError':131
        , 'invalidArrayIndex':42
        , 'invalidConfigurationData':46
        , 'invalidDataType':9
        , 'invalidEventState':73
        , 'invalidFileAccessMethod':10
        , 'invalidFileStartPosition':11
        , 'invalidKeyData':99
        , 'invalidParameterDataType':13
        , 'invalidTag':57
        , 'invalidTimeStamp':14
        , 'keyUpdateInProgress':100
        , 'listElementNotFound':81
        , 'logBufferFull':75
        , 'loggedValuePurged':76
        , 'malformedMessage':101
        , 'messageTooLong':113
        , 'missingRequiredParameter':16
        , 'networkDown':58
        , 'noAlarmConfigured':74
        , 'noObjectsOfSpecifiedType':17
        , 'noPropertySpecified':77
        , 'noSpaceForObject':18
        , 'noSpaceToAddListElement':19
        , 'noSpaceToWriteProperty':20
        , 'noVtSessionsAvailable':21
        , 'notConfigured':132
        , 'notConfiguredForTriggeredLogging':78
        , 'notCovProperty':44 
        , 'notKeyServer':102
        , 'notRouterToDnet':110
        , 'objectDeletionNotPermitted':23
        , 'objectIdentifierAlreadyExists':24
        , 'other':0
        , 'operationalProblem':25
        , 'optionalFunctionalityNotSupported':45
        , 'outOfMemory':133
        , 'parameterOutOfRange':80
        , 'passwordFailure':26
        , 'propertyIsNotAList':22
        , 'propertyIsNotAnArray':50
        , 'readAccessDenied':27
        , 'readBdtFailed':117
        , 'readFdtFailed':119
        , 'registerForeignDeviceFailed':118
        , 'rejectBufferOverflow':59
        , 'rejectInconsistentParameters':60
        , 'rejectInvalidParameterDataType':61
        , 'rejectInvalidTag':62
        , 'rejectMissingRequiredParameter':63
        , 'rejectParameterOutOfRange':64
        , 'rejectTooManyArguments':65
        , 'rejectUndefinedEnumeration':66
        , 'rejectUnrecognizedService':67
        , 'rejectProprietary':68
        , 'rejectOther':69
        , 'routerBusy':111
        , 'securityError':114
        , 'securityNotConfigured':103
        , 'serviceRequestDenied':29
        , 'sourceSecurityRequired':104
        , 'success':84
        , 'timeout':30
        , 'tooManyKeys':105
        , 'unknownAuthenticationType':106
        , 'unknownDevice':70
        , 'unknownFileSize':122
        , 'unknownKey':107
        , 'unknownKeyRevision':108
        , 'unknownNetworkMessage':112
        , 'unknownObject':31
        , 'unknownProperty':32
        , 'unknownSubscription':79
        , 'umknownRoute':71
        , 'unknownSourceMessage':109
        , 'unknownVtClass':34
        , 'unknownVtSession':35
        , 'unsupportedObjectType':36
        , 'valueNotInitialized':72
        , 'valueOutOfRange':37
        , 'valueTooLong':134 
        , 'vtSessionAlreadyClosed':38
        , 'vtSessionTerminationFailure':39
        , 'writeAccessDenied':40
        , 'writeBdtFailed':116
        }

class EventState(Enumerated):
    _owl_prefix = 'eState'
    _owl_lolim = 64
    _owl_hilim = 65535
    enumerations = \
        { 'normal':0
        , 'fault':1
        , 'offnormal':2
        , 'highLimit':3
        , 'lowLimit':4
        , 'lifeSafetyAlarm':5
        }

class EventType(Enumerated):
    _owl_prefix = 'eType'
    _owl_lolim = 64
    _owl_hilim = 65535
    enumerations = \
        { 'changeOfBitstring':0
        , 'changeOfState':1
        , 'changeOfValue':2
        , 'commandFailure':3
        , 'floatingLimit':4
        , 'outOfRange':5
        # -- context tag 7 is deprecated
        , 'changeOfLifeSafety':8
        , 'extended':9
        , 'bufferReady':10
        , 'unsignedRange':11
        # -- enumeration value 12 is reserved for future addenda 
        , 'accessEvent':13
        , 'doubleOutOfRange':14
        , 'signedOutOfRange':15
        , 'unsignedOutOfRange':16
        , 'changeOfCharacterstring':17
        , 'changeOfStatusFlags':18
        }

class FileAccessMethod(Enumerated):
    _owl_prefix = 'fam'
    enumerations = \
        { 'recordAccess':0
        , 'streamAccess':1
        }

class LifeSafetyMode(Enumerated):
    _owl_prefix = 'lsm'
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
        , 'automaticReleaseDisabled':13
        , 'default':14
        }

class LifeSafetyOperation(Enumerated):
    _owl_prefix = 'lso'
    _owl_lolim = 64
    _owl_hilim = 65535
    enumerations = \
        { 'none':0
        , 'silence':1
        , 'silenceAudible':2
        , 'silenceVisual':3
        , 'reset':4
        , 'resetAlarm':5
        , 'resetFault':6
        , 'unsilence':7
        , 'unsilenceAudible':8
        , 'unsilenceVisual':9
        }

class LifeSafetyState(Enumerated):
    _owl_prefix = 'lss'
    enumerations = \
        { 'quiet':0
        , 'preAlarm':1
        , 'alarm':2
        , 'fault':3
        , 'faultPreAlarm':4
        , 'faultAlarm':5
        , 'notReady':6
        , 'active':7
        , 'tamper':8
        , 'testAlarm':9
        , 'testActive':10
        , 'testFault':11
        , 'testFaultAlarm':12
        , 'holdup':13
        , 'duress':14
        , 'tamperAlarm':15
        , 'abnormal':16
        , 'emergencyPower':17
        , 'delayed':18
        , 'blocked':19
        , 'localAlarm':20
        , 'generalAlarm':21
        , 'supervisory':22
        , 'testSupervisory':23
        }

class LightingInProgress(Enumerated):
    _owl_prefix = 'lip'
    enumerations = \
        { 'idle':0
        , 'fadeActive':1
        , 'rampActive':2
        , 'notControlled':3
        , 'other':4
        }

class LightingOperation(Enumerated):
    _owl_prefix = 'lo'
    _owl_lolim = 256
    _owl_hilim = 65535
    enumerations = \
        { 'none':0
        , 'fadeTo':1
        , 'rampTo':2
        , 'stepUp':3
        , 'stepDown':4
        , 'stepOn':5
        , 'stepOff':6
        , 'warn':7
        , 'warnOff':8
        , 'warnRelinquish':9
        , 'stop':10
        }

class LightingTransition(Enumerated):
    _owl_prefix = 'ltr'
    _owl_lolim = 64
    _owl_hilim = 255
    enumerations = \
        { 'none':0
        , 'fade':1
        , 'ramp':2
        }

class LockStatus(Enumerated):
    _owl_prefix = 'lockStatus'
    enumerations = \
        { 'locked':0
        , 'unlocked':1
        , 'fault':2
        , 'unknown':3
        }

class LoggingType(Enumerated):
    _owl_prefix = 'lt'
    _owl_lolim = 64
    _owl_hilim = 255
    enumerations = \
        { 'polled':0
        , 'cov':1
        , 'triggered':2
        }

class Maintenance(Enumerated):
    _owl_prefix = 'maint'
    _owl_lolim = 256
    _owl_hilim = 65535
    enumerations = \
        { 'none':0
        , 'periodicTest':1
        , 'needServiceOperational':2
        , 'needServiceInoperative':3
        }

class NodeType(Enumerated):
    _owl_prefix = 'nodeType'
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

class NotifyType(Enumerated):
    _owl_prefix = 'nt'
    enumerations = \
        { 'alarm':0
        , 'event':1
        , 'ackNotification':2
        }

class Polarity(Enumerated):
    _owl_prefix = 'pol'
    enumerations = \
        { 'normal':0
        , 'reverse':1
        }

class ProgramError(Enumerated):
    _owl_prefix = 'pe'
    _owl_lolim = 64
    _owl_hilim = 65535
    enumerations = \
        { 'normal':0
        , 'loadFailed':1
        , 'internal':2
        , 'program':3
        , 'other':4
        }

class ProgramRequest(Enumerated):
    _owl_prefix = 'pgmr'
    enumerations = \
        { 'ready':0
        , 'load':1
        , 'run':2
        , 'halt':3
        , 'restart':4
        , 'unload':5
        }

class ProgramState(Enumerated):
    _owl_prefix = 'pgmState'
    enumerations = \
        { 'idle':0
        , 'loading':1
        , 'running':2
        , 'waiting':3
        , 'halted':4
        , 'unloading':5
        }

class PropertyIdentifier(Enumerated):
    _owl_prefix = 'pi'
    _owl_lolim = 512
    _owl_hilim = 4194303
    enumerations = \
        { 'absenteeLimit':244
        , 'acceptedModes':175
        , 'accessAlarmEvents':245
        , 'accessDoors':246
        , 'accessEvent':247
        , 'accessEventAuthenticationFactor':248
        , 'accessEventCredential':249
        , 'accessEventTag':322
        , 'accessEventTime':250
        , 'accessTransactionEvents':251
        , 'accompaniment':252
        , 'accompanimentTime':253
        , 'ackRequired':1
        , 'ackedTransitions':0
        , 'action':2
        , 'actionText':3
        , 'activationTime':254
        , 'activeAuthenticationPolicy':255
        , 'activeCovSubscriptions':152
        , 'activeText':4
        , 'activeVtSessions':5
        , 'actualShedLevel':212
        , 'adjustValue':176
        , 'alarmValue':6
        , 'alarmValues':7
        , 'alignIntervals':193
        , 'all':8
        , 'allWritesSuccessful':9
        , 'apduSegmentTimeout':10
        , 'apduTimeout':11
        , 'applicationSoftwareVersion':12
        , 'archive':13
        , 'assignedAccessRights':256
        , 'attemptedSamples':124
        , 'authenticationFactors':257
        , 'authenticationPolicyList':258
        , 'authenticationPolicyNames':259
        , 'authenticationStatus':260
        , 'authorizationMode':261
        , 'autoSlaveDiscovery':169
        , 'averageValue':125
        , 'backupAndRestoreState':338
        , 'backupFailureTimeout':153
        , 'backupPreparationTime':339
        , 'baseDeviceSecurityPolicy':327
        , 'belongsTo':262
        , 'bias':14
        , 'bitMask':342
        , 'bitText':343
        , 'bufferSize':126
        , 'changeOfStateCount':15
        , 'changeOfStateTime':16
        , 'clientCovIncrement':127
        , 'configurationFiles':154
        , 'controlledVariableReference':19
        , 'controlledVariableUnits':20
        , 'controlledVariableValue':21
        , 'count':177
        , 'countBeforeChange':178
        , 'countChangeTime':179
        , 'covIncrement':22
        , 'covPeriod':180
        , 'covResubscriptionInterval':128
        , 'covuPeriod':349
        , 'covuRecipients':350
        , 'credentialDisable':263
        , 'credentialStatus':264
        , 'credentials':265
        , 'credentialsInZone':266
        , 'databaseRevision':155
        , 'dateList':23
        , 'daylightSavingsStatus':24
        , 'daysRemaining':267
        , 'deadband':25
        , 'derivativeConstant':26
        , 'derivativeConstantUnits':27
        , 'description':28
        , 'descriptionOfHalt':29
        , 'deviceAddressBinding':30
        , 'deviceType':31
        , 'directReading':156
        , 'distributionKeyRevision':328
        , 'doNotHide':329
        , 'doorAlarmState':226
        , 'doorExtendedPulseTime':227
        , 'doorMembers':228
        , 'doorOpenTooLongTime':229
        , 'doorPulseTime':230
        , 'doorStatus':231
        , 'doorUnlockDelayTime':232
        , 'dutyWindow':213
        , 'effectivePeriod':32
        , 'elapsedActiveTime':33
        , 'entryPoints':268
        , 'enable':133
        , 'errorLimit':34
        , 'eventEnable':35
        , 'eventMessageTexts':351
        , 'eventState':36
        , 'eventTimeStamps':130
        , 'eventType':37
        , 'eventParameters':83
        , 'exceptionSchedule':38
        , 'exitPoints':269
        , 'expectedShedLevel':214
        , 'expiryTime':270
        , 'extendedTimeEnable':271
        , 'failedAttemptEvents':272
        , 'failedAttempts':273
        , 'failedAttemptsTime':274
        , 'faultValues':39
        , 'feedbackValue':40
        , 'fileAccessMethod':41
        , 'fileSize':42
        , 'fileType':43
        , 'firmwareRevision':44
        , 'fullDutyBaseline':215
        , 'globalIdentifier':323
        , 'groupMembers':345
        , 'groupMemberNames':346
        , 'highLimit':45
        , 'inactiveText':46
        , 'inProcess':47
        , 'inputReference':181
        , 'instanceOf':48
        , 'integralConstant':49
        , 'integralConstantUnits':50
        , 'intervalOffset':195
        , 'isUtc':344
        , 'keySets':330
        , 'lastAccessEvent':275
        , 'lastAccessPoint':276
        , 'lastCredentialAdded':277
        , 'lastCredentialAddedTime':278
        , 'lastCredentialRemoved':279
        , 'lastCredentialRemovedTime':280
        , 'lastKeyServer':331
        , 'lastNotifyRecord':173
        , 'lastRestartReason':196
        , 'lastRestoreTime':157
        , 'lastUseTime':281
        , 'lifeSafetyAlarmValues':166
        , 'limitEnable':52
        , 'limitMonitoringInterval':182
        , 'listOfGroupMembers':53
        , 'listOfObjectPropertyReferences':54
        , 'listOfSessionKeys':55
        , 'localDate':56
        , 'localTime':57
        , 'location':58
        , 'lockStatus':233
        , 'lockout':282
        , 'lockoutRelinquishTime':283
        , 'logBuffer':131
        , 'logDeviceObjectProperty':132
        , 'logInterval':134
        , 'loggingObject':183
        , 'loggingRecord':184
        , 'loggingType':197
        , 'lowLimit':59
        , 'maintenanceRequired':158
        , 'manipulatedVariableReference':60
        , 'manualSlaveAddressBinding':170
        , 'maskedAlarmValues':234
        , 'masterExemption':284
        , 'maximumOutput':61
        , 'maximumValue':135
        , 'maximumValueTimestamp':149
        , 'maxApduLengthAccepted':62
        , 'maxFailedAttempts':285
        , 'maxInfoFrames':63
        , 'maxMaster':64
        , 'maxPresValue':65
        , 'maxSegmentsAccepted':167
        , 'memberOf':159
        , 'memberStatusFlags':347
        , 'members':286
        , 'minimumOffTime':66
        , 'minimumOnTime':67
        , 'minimumOutput':68
        , 'minimumValue':136
        , 'minimumValueTimestamp':150
        , 'minPresValue':69
        , 'mode':160
        , 'modelName':70
        , 'modificationDate':71
        , 'musterPoint':287
        , 'negativeAccessRules':288
        , 'networkAccessSecurityPolicies':332
        , 'nodeSubtype':207
        , 'nodeType':208
        , 'notificationClass':17
        , 'notificationThreshold':137
        , 'notifyType':72
        , 'numberOfApduRetries':73
        , 'numberOfAuthenticationPolicies':289
        , 'numberOfStates':74
        , 'objectIdentifier':75
        , 'objectList':76
        , 'objectName':77
        , 'objectPropertyReference':78
        , 'objectType':79
        , 'occupancyCount':290
        , 'occupancyCountAdjust':291
        , 'occupancyCountEnable':292
        , 'occupancyExemption':293
        , 'occupancyLowerLimit':294
        , 'occupancyLowerLimitEnforced':295
        , 'occupancyState':296
        , 'occupancyUpperLimit':297
        , 'occupancyUpperLimitEnforced':298
        , 'operationExpected':161
        , 'optional':80
        , 'outOfService':81
        , 'outputUnits':82
        , 'packetReorderTime':333
        , 'passbackExemption':299
        , 'passbackMode':300
        , 'passbackTimeout':301
        , 'polarity':84
        , 'positiveAccessRules':302
        , 'prescale':185
        , 'presentValue':85
        , 'priority':86
        , 'priorityArray':87
        , 'priorityForWriting':88
        , 'processIdentifier':89
        , 'profileName':168
        , 'programChange':90
        , 'programLocation':91
        , 'programState':92
        , 'propertyList':371
        , 'proportionalConstant':93
        , 'proportionalConstantUnits':94
        , 'protocolObjectTypesSupported':96
        , 'protocolRevision':139
        , 'protocolServicesSupported':97
        , 'protocolVersion':98
        , 'pulseRate':186
        , 'readOnly':99
        , 'reasonForDisable':303
        , 'reasonForHalt':100
        , 'recipientList':102
        , 'recordsSinceNotification':140
        , 'recordCount':141
        , 'reliability':103
        , 'relinquishDefault':104
        , 'requestedShedLevel':218
        , 'requestedUpdateInterval':348
        , 'required':105
        , 'resolution':106
        , 'restartNotificationRecipients':202
        , 'restoreCompletionTime':340
        , 'restorePreparationTime':341
        , 'scale':187
        , 'scaleFactor':188
        , 'scheduleDefault':174
        , 'securedStatus':235
        , 'securityPduTimeout':334
        , 'securityTimeWindow':335
        , 'segmentationSupported':107
        , 'setpoint':108
        , 'setpointReference':109
        , 'setting':162
        , 'shedDuration':219
        , 'shedLevelDescriptions':220
        , 'shedLevels':221
        , 'silenced':163
        , 'slaveAddressBinding':171
        , 'slaveProxyEnable':172
        , 'startTime':142
        , 'stateDescription':222
        , 'stateText':110
        , 'statusFlags':111
        , 'stopTime':143
        , 'stopWhenFull':144
        , 'structuredObjectList':209
        , 'subordinateAnnotations':210
        , 'subordinateList':211
        , 'supportedFormats':304
        , 'supportedFormatClasses':305
        , 'supportedSecurityAlgorithms':336
        , 'systemStatus':112
        , 'threatAuthority':306
        , 'threatLevel':307
        , 'timeDelay':113
        , 'timeOfActiveTimeReset':114
        , 'timeOfDeviceRestart':203
        , 'timeOfStateCountReset':115
        , 'timeSynchronizationInterval':204
        , 'timeSynchronizationRecipients':116
        , 'totalRecordCount':145
        , 'traceFlag':308
        , 'trackingValue':164
        , 'transactionNotificationClass':309
        , 'trigger':205
        , 'units':117
        , 'updateInterval':118
        , 'updateKeySetTimeout':337
        , 'updateTime':189
        , 'userExternalIdentifier':310
        , 'userInformationReference':311
        , 'userName':317
        , 'userType':318
        , 'usesRemaining':319
        , 'utcOffset':119
        , 'utcTimeSynchronizationRecipients':206
        , 'validSamples':146
        , 'valueBeforeChange':190
        , 'valueSet':191
        , 'valueChangeTime':192
        , 'varianceValue':151
        , 'vendorIdentifier':120
        , 'vendorName':121
        , 'verificationTime':326
        , 'vtClassesSupported':122
        , 'weeklySchedule':123
        , 'windowInterval':147
        , 'windowSamples':148
        , 'zoneFrom':320
        , 'zoneMembers':165
        , 'zoneTo':321
        }

class Reliability(Enumerated):
    _owl_prefix = 'rel'
    _owl_lolim = 64
    _owl_hilim = 65535
    enumerations = \
        { 'noFaultDetected':0
        , 'noSensor':1
        , 'overRange':2
        , 'underRange':3
        , 'openLoop':4
        , 'shortedLoop':5
        , 'noOutput':6
        , 'unreliableOther':7
        , 'processError':8
        , 'multiStateFault':9
        , 'configurationError':10
        , 'communicationFailure':12
        , 'numberFault':13
        }

class RestartReason(Enumerated):
    _owl_prefix = 'rsr'
    _owl_lolim = 64
    _owl_hilim = 255
    enumerations = \
        { 'unknown':0
        , 'coldstart':1
        , 'warmstart':2
        , 'detectedPowerLost':3
        , 'detectedPoweredOff':4
        , 'hardwareWatchdog':5
        , 'softwareWatchdog':6
        , 'suspended':7
        }

class SecurityLevel(Enumerated):
    _owl_prefix = 'secl'
    enumerations = \
        { 'incapable':0
        , 'plain':1
        , 'signed':2
        , 'encrypted':3
        , 'signedEndToEnd':4
        , 'encryptedEndToEnd':4
        }

class SecurityPolicy(Enumerated):
    _owl_prefix = 'secp'
    enumerations = \
        { 'plainNonTrusted':0
        , 'plainTrusted':1
        , 'signedTrusted':2
        , 'encryptedTrusted':3
        }

class ShedState(Enumerated):
    _owl_prefix = 'shedState'
    enumerations = \
        { 'shedInactive':0
        , 'shedRequestPending':1
        , 'shedCompliant':2
        , 'shedNonCompliant':3
        }

class Segmentation(Enumerated):
    _owl_prefix = 'seg'
    enumerations = \
        { 'segmentedBoth':0
        , 'segmentedTransmit':1
        , 'segmentedReceive':2
        , 'noSegmentation':3
        }

class SilencedState(Enumerated):
    _owl_prefix = 'silencedStats'
    _owl_lolim = 64
    _owl_hilim = 65535
    enumerations = \
        { 'unsilenced':0
        , 'audibleSilenced':1
        , 'visibleSilenced':2
        , 'allSilenced':3
        }

class VTClass(Enumerated):
    _owl_prefix = 'vtc'
    _owl_lolim = 64
    _owl_hilim = 65535
    enumerations = \
        { 'defaultTerminal':0
        , 'ansiX3-64':1
        , 'decVt52':2
        , 'decVt100':3
        , 'decVt220':4
        , 'hp-700-94':5
        , 'ibm-3130':6
        }

class WriteStatus(Enumerated):
    _owl_prefix = 'ws'
    enumerations = \
        { 'idle':0
        , 'inProgress':1
        , 'successful':2
        , 'failed':3
        }

#
#   Forward Sequences
#

class DeviceAddress(Sequence):
    _owl_prefix = 'da'
    sequenceElements = \
        [ Element('networkNumber', Unsigned)
        , Element('macAddress', OctetString)
        ]

class DeviceObjectPropertyReference(Sequence):
    _owl_prefix = 'dopr'
    sequenceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 0)
        , Element('propertyIdentifier', PropertyIdentifier, 1)
        , Element('propertyArrayIndex', Unsigned, 2, True)
        , Element('deviceIdentifier', ObjectIdentifier, 3, True)
        ]

class DeviceObjectReference(Sequence):
    _owl_prefix = 'dor'
    sequenceElements = \
        [ Element('deviceIdentifier', ObjectIdentifier, 0, True)
        , Element('objectIdentifier', ObjectIdentifier, 1)
        ]

class DateTime(Sequence):
    _owl_prefix = 'dt'
    sequenceElements = \
        [ Element('date', Date)
        , Element('time', Time)
        ]

class DateRange(Sequence):
    _owl_prefix = 'dr'
    sequenceElements = \
        [ Element('startDate', Date)
        , Element('endDate', Date)
        ]

class ErrorType(Sequence):
    _owl_prefix = 'errType'
    sequenceElements = \
        [ Element('errorClass', ErrorClass)
        , Element('errorCode', ErrorCode)
        ]

class ObjectPropertyReference(Sequence):
    _owl_prefix = 'opr'
    sequenceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 0)
        , Element('propertyIdentifier', PropertyIdentifier, 1)
        , Element('propertyArrayIndex', Unsigned, 2, True)
        ]

class PropertyStates(Choice):
    _owl_prefix = 'propStates'
    _owl_lolim = 64
    _owl_hilim = 254
    choiceElements = \
        [ Element('booleanValue', Boolean, 0)
        , Element('binaryValue', BinaryPV, 1)
        , Element('eventType', EventType, 2)
        , Element('polarity', Polarity, 3)
        , Element('programChange', ProgramRequest, 4)
        , Element('programState', ProgramState, 5)
        , Element('reasonForHalt', ProgramError, 6)
        , Element('reliability', Reliability, 7)
        , Element('state', EventState, 8)
        , Element('systemStatus', DeviceStatus, 9)
        , Element('units', EngineeringUnits, 10)
        , Element('unsignedValue', Unsigned, 11)
        , Element('lifeSafetyMode', LifeSafetyMode, 12)
        , Element('lifeSafetyState', LifeSafetyState, 13)
        , Element('restartReason', RestartReason, 14)
        , Element('doorAlarmState', DoorAlarmState, 15)
        , Element('action', Action, 16)
        , Element('doorSecuredStatus', DoorSecuredStatus, 17)
        , Element('doorStatus', DoorStatus, 18)
        , Element('doorValue', DoorValue, 19)
        , Element('fileAccessMethod', FileAccessMethod, 20)
        , Element('lockStatus', LockStatus, 21)
        , Element('lifeSafetyOperation', LifeSafetyOperation, 22)
        , Element('maintenance', Maintenance, 23)
        , Element('nodeType', NodeType, 24)
        , Element('notifyType', NotifyType, 25)
        , Element('securityLevel', SecurityLevel, 26)
        , Element('shedState', ShedState, 27)
        , Element('silencedState', SilencedState, 28)
        , Element('accessEvent', AccessEvent, 30)
        , Element('zoneOccupancyState', AccessZoneOccupancyState, 31)
        , Element('accessCredentialDisableReason', AccessCredentialDisableReason, 32)
        , Element('accessCredentialDisable', AccessCredentialDisable, 33)
        , Element('authenticationStatus', AuthenticationStatus, 34)
        , Element('backupState', BackupState, 36)
        , Element('writeStatus', WriteStatus, 37)
        , Element('lightingInProgress', LightingInProgress, 38)
        , Element('lightingOperation', LightingOperation, 39)
        , Element('lightingTransition', LightingTransition, 40)
        ]

class PropertyValue(Sequence):
    _owl_prefix = 'propValue'
    sequenceElements = \
        [ Element('propertyIdentifier', PropertyIdentifier, 0)
        , Element('propertyArrayIndex', Unsigned, 1, True)
        , Element('value', Any, 2)
        , Element('priority', Unsigned, 3, True)
        ]

class Recipient(Choice):
    _owl_prefix = 'recip'
    choiceElements = \
        [ Element('device', ObjectIdentifier, 0)
        , Element('address', DeviceAddress, 1)
        ]

class RecipientProcess(Sequence):
    _owl_prefix = 'recipProc'
    sequenceElements = \
        [ Element('recipient', Recipient, 0)
        , Element('processIdentifier', Unsigned, 1)
        ]

class TimeStamp(Choice):
    _owl_prefix = 'ts'
    choiceElements = \
        [ Element('time', Time, 0)
        , Element('sequenceNumber', Unsigned, 1)
        , Element('dateTime', DateTime, 2)
        ]

class TimeValue(Sequence):
    _owl_prefix = 'tv'
    sequenceElements = \
        [ Element('time', Time)
        , Element('value', Any)
        ]

class WeekNDay(OctetString):
    _owl_prefix = 'wnd'

    def __str__(self):
        if len(self.value) != 3:
            return "WeekNDay(?): " + OctetString.__str__(self)
        else:
            return "WeekNDay(%d, %d, %d)" % (ord(self.value[0]), ord(self.value[1]), ord(self.value[2]))

#
#   Sequences
#

class AccessRule(Sequence):
    _owl_prefix = 'arule'
    sequenceElements = \
        [ Element('timeRangeSpecifier', AccessRuleTimeRangeSpecifier, 0)
        , Element('timeRange', DeviceObjectPropertyReference, 1, True)
        , Element('locationSpecifier', AccessRuleLocationSpecifier, 2)
        , Element('location', DeviceObjectReference, 3, True)
        , Element('enable', Boolean, 4)
        ]

class AccessThreatLevel(Unsigned):
    pass

class AccumulatorRecord(Sequence):
    _owl_prefix = 'aRec'
    sequenceElements = \
        [ Element('timestamp', DateTime, 0)
        , Element('presentValue', Unsigned, 1)
        , Element('accumulatedValue', Unsigned, 2)
        , Element('accumulatorStatus', AccumulatorRecordAccumulatorStatus, 3)
        ]

class ActionCommand(Sequence):
    _owl_prefix = 'ac'
    sequenceElements = \
        [ Element('deviceIdentifier', ObjectIdentifier, 0, True)
        , Element('objectIdentifier', ObjectIdentifier, 1)
        , Element('propertyIdentifier', PropertyIdentifier, 2)
        , Element('propertyArrayIndex', Unsigned, 3, True)
        , Element('propertyValue', Any, 4)
        , Element('priority', Unsigned, 5, True)
        , Element('postDelay', Unsigned, 6, True)
        , Element('quiteOnFailure', Boolean, 7)
        , Element('writeSuccessFul', Boolean, 8)
        ]

class ActionList(Sequence):
    _owl_prefix = 'al'
    sequenceElements = \
        [ Element('action', SequenceOf(ActionCommand))
        ]

class AddressBinding(Sequence):
    _owl_prefix = 'ab'
    sequenceElements = \
        [ Element('deviceObjectIdentifier', ObjectIdentifier)
        , Element('deviceAddress', DeviceAddress)
        ]

class AssignedAccessRights(Sequence):
    _owl_prefix = 'aar'
    serviceChoice = 15
    sequenceElements = \
        [ Element('assignedAccessRights', DeviceObjectReference, 0)
        , Element('enable', Boolean, 1)
        ]

class AuthenticationFactor(Sequence):
    _owl_prefix = 'af'
    sequenceElements = \
        [ Element('formatType', AuthenticationFactorType, 0)
        , Element('formatClass', Unsigned, 1)
        , Element('value', OctetString, 2)
        ]

class AuthenticationFactorFormat(Sequence):
    _owl_prefix = 'aff'
    sequenceElements = \
        [ Element('formatType', AuthenticationFactorType, 0)
        , Element('vendorId', Unsigned, 1, True)
        , Element('vendorFormat', Unsigned, 2, True)
        ]

class AuthenticationPolicyPolicy(Sequence):
    _owl_prefix = 'app'
    sequenceElements = \
        [ Element('credentialDataInput', DeviceObjectReference, 0)
        , Element('index', Unsigned, 1)
        ]

class AuthenticationPolicy(Sequence):
    _owl_prefix = 'ap'
    sequenceElements = \
        [ Element('policy', SequenceOf(AuthenticationPolicyPolicy), 0)
        , Element('orderEnforced', Boolean, 1)
        , Element('timeout', Unsigned, 2)
        ]

class CalendarEntry(Choice):
    _owl_prefix = 'ce'
    choiceElements = \
        [ Element('date', Date, 0)
        , Element('dateRange', DateRange, 1)
        , Element('weekNDay', WeekNDay, 2)
        ]

class ChannelValue(Choice):
    _owl_prefix = 'cv'
    choiceElements = [
        ### needs help
        ]

class ClientCOV(Choice):
    _owl_prefix = 'ccov'
    choiceElements = \
        [ Element('realIncrement', Real, 0)
        , Element('defaultIncrement', Null, 0)
        ]

class COVSubscription(Sequence):
    _owl_prefix = 'covSub'
    sequenceElements = \
        [ Element('recipient', RecipientProcess, 0)
        , Element('monitoredPropertyReference', ObjectPropertyReference, 1)
        , Element('issueConfirmedNotifications', Boolean, 2)
        , Element('timeRemaining', Unsigned, 3)
        , Element('covIncrement', Real, 4, True)
        ]

class CredentialAuthenticationFactor(Sequence):
    _owl_prefix = 'caf'
    sequenceElements = \
        [ Element('disable', AccessAuthenticationFactorDisable, 0)
        , Element('authenticationFactor', AuthenticationFactor, 1)
        ]

class DailySchedule(Sequence):
    _owl_prefix = 'ds'
    sequenceElements = \
        [ Element('daySchedule', SequenceOf(TimeValue), 0)
        ]

class Destination(Sequence):
    _owl_prefix = 'dest'
    sequenceElements = \
        [ Element('validDays', DaysOfWeek)
        , Element('fromTime', Time)
        , Element('toTime', Time)
        , Element('recipient', Recipient)
        , Element('processIdentifier', Unsigned)
        , Element('issueConfirmedNotifications', Boolean)
        , Element('transitions', EventTransitionBits)
        ]

class DeviceObjectPropertyValue(Sequence):
    _owl_prefix = 'dopv'
    sequenceElements = \
        [ Element('deviceIdentifier', ObjectIdentifier, 0)
        , Element('objectIdentifier', ObjectIdentifier, 1)
        , Element('propertyIdentifier', PropertyIdentifier, 2)
        , Element('arrayIndex', Unsigned, 3, True)
        , Element('value', Any, 4)
        ]

class EventParameterChangeOfBitstring(Sequence):
    _owl_prefix = 'epcob'
    sequenceElements = \
        [ Element('timeDelay', Unsigned, 0)
        , Element('bitmask', BitString, 1)
        , Element('listOfBitstringValues', SequenceOf(BitString), 2)
        ]

class EventParameterChangeOfState(Sequence):
    _owl_prefix = 'epcos'
    sequenceElements = \
        [ Element('timeDelay', Unsigned, 0)
        , Element('listOfValues', SequenceOf(PropertyStates), 1)
        ]

class EventParameterChangeOfValueCOVCriteria(Choice):
    _owl_prefix = 'epcovc'
    choiceElements = \
        [ Element('bitmask', BitString, 0)
        , Element('referencedPropertyIncrement', Real, 1)
        ]

class EventParameterChangeOfValue(Sequence):
    _owl_prefix = 'epcov'
    sequenceElements = \
        [ Element('timeDelay', Unsigned, 0)
        , Element('covCriteria', EventParameterChangeOfValueCOVCriteria, 1)
        ]

class EventParameterCommandFailure(Sequence):
    _owl_prefix = 'epcf'
    sequenceElements = \
        [ Element('timeDelay', Unsigned, 0)
        , Element('feedbackPropertyReference', DeviceObjectPropertyReference, 1)
        ]

class EventParameterFloatingLimit(Sequence):
    _owl_prefix = 'epfl'
    sequenceElements = \
        [ Element('timeDelay', Unsigned, 0)
        , Element('setpointReference', DeviceObjectPropertyReference, 1)
        , Element('lowDiffLimit', Real, 2)
        , Element('highDiffLimit', Real, 3)
        , Element('deadband', Real, 4)
        ]

class EventParameterOutOfRange(Sequence):
    _owl_prefix = 'epoor'
    sequenceElements = \
        [ Element('timeDelay', Unsigned, 0)
        , Element('lowLimit', Real, 1)
        , Element('highLimit', Real, 2)
        , Element('deadband', Real, 3)
        ]

class EventParameterChangeOfLifeSafety(Sequence):
    _owl_prefix = 'epcols'
    sequenceElements = \
        [ Element('timeDelay', Unsigned, 0)
        , Element('listOfLifeSafetyAlarmValues', SequenceOf(LifeSafetyState), 1)
        , Element('listOfAlarmValues', SequenceOf(LifeSafetyState), 2)
        , Element('modePropertyReference', DeviceObjectPropertyReference, 3)
        ]

class EventParameterExtendedParameters(Choice):
    _owl_prefix = 'epep'
    choiceElements = \
        [ Element('null', Null, 0)
        , Element('real', Real, 1)
        , Element('integer', Unsigned, 2)
        , Element('boolean', Boolean, 3)
        , Element('double', Double, 4)
        , Element('octet', OctetString, 5)
        , Element('bitstring', BitString, 6)
        , Element('enum', Enumerated, 7)
        , Element('reference', DeviceObjectPropertyReference, 8)
        ]

class EventParameterExtended(Sequence):
    _owl_prefix = 'epe'
    sequenceElements = \
        [ Element('vendorId', Unsigned, 0)
        , Element('extendedEventType', Unsigned, 1)
        , Element('parameters', SequenceOf(EventParameterExtendedParameters), 2)
        ]

class EventParameterBufferReady(Sequence):
    _owl_prefix = 'epbr'
    sequenceElements = \
        [ Element('notificationThreshold', Unsigned, 0)
        , Element('previousNotificationCount', Unsigned, 1)
        ]

class EventParameterUnsignedRange(Sequence):
    _owl_prefix = 'epur'
    sequenceElements = \
        [ Element('timeDelay', Unsigned, 0)
        , Element('lowLimit', Unsigned, 1)
        , Element('highLimit', Unsigned, 2)
        ]

class EventParameterAccessEventAccessEvent(Sequence):
    _owl_prefix = 'epaeae'
    sequenceevents = \
        [ Element('listOfAccessEvents', SequenceOf(AccessEvent), 0)
        , Element('accessEventTimeReference', DeviceObjectPropertyReference, 0)
        ]

class EventParameterAccessEvent(Sequence):
    _owl_prefix = 'epae'
    sequenceElements = \
        [ Element('accessEvent', SequenceOf(EventParameterAccessEventAccessEvent), 0)
        ]

class EventParameterDoubleOutOfRange(Sequence):
    _owl_prefix = 'epdoor'
    sequenceElements = \
        [ Element('timeDelay', Unsigned, 0)
        , Element('lowLimit', Double, 1)
        , Element('highLimit', Double, 2)
        , Element('deadband', Double, 3)
        ]

class EventParameterSignedOutOfRange(Sequence):
    _owl_prefix = 'epsoor'
    sequenceElements = \
        [ Element('timeDelay', Unsigned, 0)
        , Element('lowLimit', Integer, 1)
        , Element('highLimit', Integer, 2)
        , Element('deadband', Unsigned, 3)
        ]

class EventParameterUnsignedOutOfRange(Sequence):
    _owl_prefix = 'epuoor'
    sequenceElements = \
        [ Element('timeDelay', Unsigned, 0)
        , Element('lowLimit', Unsigned, 1)
        , Element('highLimit', Unsigned, 2)
        , Element('deadband', Unsigned, 3)
        ]

class EventParameterChangeOfCharacterString(Sequence):
    _owl_prefix = 'epcocs'
    sequenceElements = \
        [ Element('timeDelay', Unsigned, 0)
        , Element('listOfAlarmValues', SequenceOf(CharacterString), 1)
        ]

class EventParameterChangeOfStatusFlags(Sequence):
    _owl_prefix = 'epcosf'
    sequenceElements = \
        [ Element('timeDelay', Unsigned, 0)
        , Element('selectedFlags', StatusFlags, 1)
        ]

class EventParameter(Choice):
    _owl_prefix = 'ep'
    choiceElements = \
        [ Element('changeOfBitstring', EventParameterChangeOfBitstring, 0)
        , Element('changeOfState', EventParameterChangeOfState, 1)
        , Element('changeOfValue', EventParameterChangeOfValue, 2)
        , Element('commandFailure', EventParameterCommandFailure, 3)
        , Element('floatingLimit', EventParameterFloatingLimit, 4)
        , Element('outOfRange', EventParameterOutOfRange, 5)
        , Element('changeOfLifesafety', EventParameterChangeOfLifeSafety, 8)
        , Element('extended', EventParameterExtended, 9)
        , Element('bufferReady', EventParameterBufferReady, 10)
        , Element('unsignedRange', EventParameterUnsignedRange, 11)
        , Element('accessEvent', EventParameterAccessEvent, 13)
        , Element('doubleOutOfRange', EventParameterDoubleOutOfRange, 14)
        , Element('signedOutOfRange', EventParameterSignedOutOfRange, 15)
        , Element('unsignedOutOfRange', EventParameterUnsignedOutOfRange, 16)
        , Element('changeOfCharacterstring', EventParameterChangeOfCharacterString, 17)
        , Element('changeOfStatusflags', EventParameterChangeOfStatusFlags, 18)
        ]

class KeyIdentifier(Sequence):
    _owl_prefix = 'ki'
    sequenceElements = \
        [ Element('algorithm', Unsigned, 0)
        , Element('keyId', Unsigned, 1)
        ]

class LogDataLogData(Choice):
    _owl_prefix = 'ldld'
    choiceElements = \
        [ Element('booleanValue', Boolean, 0)
        , Element('realValue', Real, 1)
        , Element('enumValue', Enumerated, 2)
        , Element('unsignedValue', Unsigned, 3)
        , Element('signedValue', Integer, 4)
        , Element('bitstringValue', BitString, 5)
        , Element('nullValue', Null, 6)
        , Element('failure', ErrorType, 7)
        , Element('anyValue', Any, 8)
        ]

class LogData(Choice):
    _owl_prefix = 'ld'
    choiceElements = \
        [ Element('logStatus', LogStatus, 0)
        , Element('logData', SequenceOf(LogDataLogData), 1)
        , Element('timeChange', Real, 2)
        ]

class LogMultipleRecord(Sequence):
    _owl_prefix = 'lmr'
    sequenceElements = \
        [ Element('timestamp', DateTime, 0)
        , Element('logData', LogData, 1)
        ]

class LogRecordLogDatum(Choice):
    _owl_prefix = 'lrld'
    choiceElements = \
        [ Element('logStatus', LogStatus, 0)
        , Element('booleanValue', Boolean, 1)
        , Element('realValue', Real, 2)
        , Element('enumValue', Enumerated, 3)
        , Element('unsignedValue', Unsigned, 4)
        , Element('signedValue', Integer, 5)
        , Element('bitstringValue', BitString, 6)
        , Element('nullValue', Null, 7)
        , Element('failure', ErrorType, 8)  
        , Element('timeChange', Real, 9)
        , Element('anyValue', Any, 10)
        ]

class LogRecord(Sequence):
    _owl_prefix = 'lr'
    sequenceElements = \
        [ Element('timestamp', DateTime, 0)
        , Element('logDatum', LogRecordLogDatum, 1)
        , Element('statusFlags', StatusFlags, 2, True)
        ]

class NetworkSecurityPolicy(Sequence):
    _owl_prefix = 'nsp'
    sequenceElements = \
        [ Element('portId', Unsigned, 0)
        , Element('securityLevel', SecurityPolicy, 1)
        ]

class NotificationParametersChangeOfBitstring(Sequence):
    _owl_prefix = 'npcobs'
    sequenceElements = \
        [ Element('referencedBitstring', BitString, 0)
        , Element('statusFlags', StatusFlags, 1)
        ]

class NotificationParametersChangeOfState(Sequence):
    _owl_prefix = 'npcos'
    sequenceElements = \
        [ Element('newState', PropertyStates, 0)
        , Element('statusFlags', StatusFlags, 1)
        ]
        
class NotificationParametersChangeOfValueNewValue(Choice):
    _owl_prefix = 'npcovnv'
    choiceElements = \
        [ Element('changedBits', BitString, 0)
        , Element('changedValue', Real, 1)
        ]
        
class NotificationParametersChangeOfValue(Sequence):
    _owl_prefix = 'npcov'
    sequenceElements = \
        [ Element('newValue', NotificationParametersChangeOfValueNewValue, 0)
        , Element('statusFlags', StatusFlags, 1)
        ]
        
class NotificationParametersCommandFailure(Sequence):
    _owl_prefix = 'npcf'
    sequenceElements = \
        [ Element('commandValue', Any, 0)
        , Element('statusFlags', StatusFlags, 1)
        , Element('feedbackValue', Any, 2)
        ]

class NotificationParametersFloatingLimit(Sequence):
    _owl_prefix = 'npfl'
    sequenceElements = \
        [ Element('referenceValue', Real, 0)
        , Element('statusFlags', StatusFlags, 1)
        , Element('setpointValue', Real, 2)
        , Element('errorLimit', Real, 3)
        ]

class NotificationParametersOutOfRange(Sequence):
    _owl_prefix = 'npoor'
    sequenceElements = \
        [ Element('exceedingValue', Real, 0)
        , Element('statusFlags', StatusFlags, 1)
        , Element('deadband', Real, 2)
        , Element('exceededLimit', Real, 3)
        ]

class NotificationParametersExtendedParametersType(Choice):
    _owl_prefix = 'npept'
    choiceElements = \
        [ Element('null', Null)
        , Element('real', Real)
        , Element('integer', Unsigned)
        , Element('boolean', Boolean)
        , Element('double', Double)
        , Element('octet', OctetString)
        , Element('bitstring', BitString)
        , Element('enum', Enumerated)
        , Element('propertyValue', DeviceObjectPropertyValue)
        ]

class NotificationParametersExtended(Sequence):
    _owl_prefix = 'npe'
    sequenceElements = \
        [ Element('vendorId', Unsigned, 0)
        , Element('extendedEventType', Unsigned, 1)
        , Element('parameters', NotificationParametersExtendedParametersType, 2)
        ]

class NotificationParametersBufferReady(Sequence):
    _owl_prefix = 'npbr'
    sequenceElements = \
        [ Element('bufferProperty', DeviceObjectPropertyReference, 0)
        , Element('previousNotification', Unsigned, 1)
        , Element('currentNotification', Unsigned, 2)
        ]
 
class NotificationParametersUnsignedRange(Sequence):    
    _owl_prefix = 'npur'
    sequenceElements = \
        [ Element('exceedingValue', Unsigned, 0)
        , Element('statusFlags', StatusFlags, 1)
        , Element('exceedingLimit', Unsigned, 2)
        ]

class NotificationParametersComplexEventType(Sequence):
    _owl_prefix = 'npcet'
    sequenceElements = \
        [ Element('complexEventType', PropertyValue, 0)
        ]

class NotificationParametersChangeOfLifeSafety(Sequence):
    _owl_prefix = 'npcols'
    sequenceElements = \
        [ Element('newState', LifeSafetyState, 0)
        , Element('newMode', LifeSafetyMode, 1)
        , Element('statusFlags',StatusFlags, 2)
        , Element('operationExpected', LifeSafetyOperation, 3)
        ]

class NotificationParametersAccessEventType(Sequence):
    _owl_prefix = 'npaet'
    sequenceElements = \
        [ Element('accessEvent', AccessEvent, 0)
        , Element('statusFlags', StatusFlags, 1)
        , Element('accessEventTag', Unsigned, 2)
        , Element('accessEventTime', TimeStamp, 3)
        , Element('accessCredential', DeviceObjectReference, 4)
        , Element('authenicationFactor', AuthenticationFactorType, 5, True)
        ]

class NotificationParametersDoubleOutOfRangeType(Sequence):
    _owl_prefix = 'npdoort'
    sequenceElements = \
        [ Element('exceedingValue', Double, 0)
        , Element('statusFlags', StatusFlags, 1)
        , Element('deadband', Double, 2)
        , Element('exceededLimit', Double, 3)
        ]

class NotificationParametersSignedOutOfRangeType(Sequence):
    _owl_prefix = 'npsoort'
    sequenceElements = \
        [ Element('exceedingValue', Integer, 0)
        , Element('statusFlags', StatusFlags, 1)
        , Element('deadband', Unsigned, 2)
        , Element('exceededLimit', Integer, 3)
        ]

class NotificationParametersUnsignedOutOfRangeType(Sequence):
    _owl_prefix = 'npuoort'
    sequenceElements = \
        [ Element('exceedingValue', Unsigned, 0)
        , Element('statusFlags', StatusFlags, 1)
        , Element('deadband', Unsigned, 2)
        , Element('exceededLimit', Unsigned, 3)
        ]

class NotificationParametersChangeOfCharacterStringType(Sequence):
    _owl_prefix = 'npcocst'
    sequenceElements = \
        [ Element('changedValue', CharacterString, 0)
        , Element('statusFlags', StatusFlags, 1)
        , Element('alarmValue', CharacterString, 2)
        ]

class NotificationParametersChangeOfStatusFlagsType(Sequence):
    _owl_prefix = 'npcosft'
    sequenceElements = \
        [ Element('presentValue', CharacterString, 0)
        , Element('referencedFlags', StatusFlags, 1)
        ]

class NotificationParameters(Choice):
    _owl_prefix = 'np'
    choiceElements = \
        [ Element('changeOfBitstring', NotificationParametersChangeOfBitstring, 0)
        , Element('changeOfState', NotificationParametersChangeOfState, 1)
        , Element('changeOfValue', NotificationParametersChangeOfValue, 2)
        , Element('commandFailure', NotificationParametersCommandFailure, 3)
        , Element('floatingLimit', NotificationParametersFloatingLimit, 4)
        , Element('outOfRange', NotificationParametersOutOfRange, 5)
        , Element('complexEventType', NotificationParametersComplexEventType, 6)
        , Element('changeOfLifeSafety', NotificationParametersChangeOfLifeSafety, 8)
        , Element('extended', NotificationParametersExtended, 9)
        , Element('bufferReady', NotificationParametersBufferReady, 10)
        , Element('unsignedRange', NotificationParametersUnsignedRange, 11)
        , Element('accessEvent', NotificationParametersAccessEventType, 13)
        , Element('doubleOutOfRange', NotificationParametersDoubleOutOfRangeType, 14)
        , Element('signedOutOfRange', NotificationParametersSignedOutOfRangeType, 15)
        , Element('unsignedOutOfRange', NotificationParametersUnsignedOutOfRangeType, 16)
        , Element('changeOfCharacterString', NotificationParametersChangeOfCharacterStringType, 17)
        , Element('changeOfStatusFlags', NotificationParametersChangeOfStatusFlagsType, 18)
        ]

class ObjectPropertyValue(Sequence):
    _owl_prefix = 'opv'
    sequenceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 0)
        , Element('propertyIdentifier', PropertyIdentifier, 1)
        , Element('propertyArrayIndex', Unsigned, 2, True)
        , Element('value', Any, 3)
        , Element('priority', Unsigned, 4, True)
        ]

class OptionalCharacterString(Choice):  
    _owl_prefix = 'ocs'
    choiceElements = \
        [ Element('null', Null)
        , Element('characterString', CharacterString)
        ]

class Prescale(Sequence):
    _owl_prefix = 'prescale'
    sequenceElements = \
        [ Element('multiplier', Unsigned, 0)
        , Element('moduloDivide', Unsigned, 1)
        ]

class PriorityValue(Choice):
    _owl_prefix = 'pv'
    choiceElements = \
        [ Element('null', Null)
        , Element('real', Real)
        , Element('enumerated', Enumerated)
        , Element('unsigned', Unsigned)
        , Element('boolean', Boolean)
        , Element('signed', Integer)
        , Element('double', Double)
        , Element('time', Time)
        , Element('characterString', CharacterString)
        , Element('octetString', OctetString)
        , Element('bitString', BitString)
        , Element('date', Date)
        , Element('objectid', ObjectIdentifier)
        , Element('constructedValue', Any, 0)
        , Element('datetime', DateTime, 1)
        ]

class PriorityArray(ArrayOf(PriorityValue)):
    _owl_prefix = 'pa'
    pass

class PropertyAccessResultAccessResult(Choice):
    _owl_prefix = 'parar'
    choiceElements = \
        [ Element('propertyValue', Any, 4)
        , Element('propertyAccessError', ErrorType, 5)
        ]

class PropertyAccessResult(Sequence):
    _owl_prefix = 'par'
    sequenceElements = \
        [ Element('objectIdentifier', ObjectIdentifier, 0)
        , Element('propertyIdentifier', PropertyIdentifier, 1)
        , Element('propertyArrayIndex', Unsigned, 2, True)
        , Element('deviceIdentifier', ObjectIdentifier, 3, True)
        , Element('accessResult', PropertyAccessResultAccessResult)
        ]

class PropertyReference(Sequence):
    _owl_prefix = 'pr'
    sequenceElements = \
        [ Element('propertyIdentifier', PropertyIdentifier, 0)
        , Element('propertyArrayIndex', Unsigned, 1, True)
        ]

class Scale(Choice):
    _owl_prefix = 'scale'
    choiceElements = \
        [ Element('floatScale', Real)
        , Element('integerScale', Integer)
        ]

class SecurityKeySet(Sequence):
    _owl_prefix = 'secks'
    sequenceElements = \
        [ Element('keyRevision', Unsigned, 0)
        , Element('activationTime', DateTime, 1)
        , Element('expirationTime', DateTime, 2)
        , Element('keyIds', SequenceOf(KeyIdentifier), 3)
        ]

class ShedLevel(Choice):
    _owl_prefix = 'shedLvl'
    choiceElements = \
        [ Element('percent', Unsigned, 0)
        , Element('level', Unsigned, 1)
        , Element('amount', Real, 2)
        ]

class SetpointReference(Sequence):
    _owl_prefix = 'sr'
    sequenceElements = \
        [ Element('setpointReference', ObjectPropertyReference, 0, True)
        ]

class SpecialEventPeriod(Choice):
    _owl_prefix = 'sep'
    choiceElements = \
        [ Element('calendarEntry', CalendarEntry, 0)
        , Element('calendarReference', ObjectIdentifier, 1)
        ]

class SpecialEvent(Sequence):
    _owl_prefix = 'se'
    sequenceElements = \
        [ Element('period', SpecialEventPeriod)
        , Element('listOfTimeValues', SequenceOf(TimeValue), 2)
        , Element('eventPriority', Unsigned, 3)
        ]

class VTSession(Sequence):
    _owl_prefix = 'vts'
    sequenceElements = \
        [ Element('localVtSessionID', Unsigned)
        , Element('remoteVtSessionID', Unsigned)
        , Element('remoteVtAddress', DeviceAddress)
        ]

