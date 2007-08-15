import sys
import random

from BACpypes.CommunicationsCore import Thread
if ("--debugThread" in sys.argv):
    print "imported", Thread

from BACpypes.PrimativeData import Real
from BACpypes.Application import BIPSimpleApplication
from BACpypes.Object import LocalDeviceObject, AnalogInputObject, Property, RegisterObjectType

from BACpypes.APDU import UnconfirmedRequestPDU

# some debugging
_debug = 0

# make a device object from a configuration file
from ConfigParser import ConfigParser
config = ConfigParser()
config.read('BACpypes.ini')

thisDevice = \
    LocalDeviceObject( objectName=config.get('BACpypes','objectName')
        , objectIdentifier=config.getint('BACpypes','objectIdentifier')
        , maxApduLengthAccepted=config.getint('BACpypes','maxApduLengthAccepted')
        , segmentationSupported=config.get('BACpypes','segmentationSupported')
        , vendorIdentifier=config.getint('BACpypes','vendorIdentifier')
        )

#
#   MyApplication
#

class MyApplication(BIPSimpleApplication):

    def __init__(self):
        BIPSimpleApplication.__init__(self, thisDevice, config.get('BACpypes','address'))
        
    def Request(self, apdu):
        print "MyApplication.Request:", apdu
        apdu.DebugContents()
        print
        
        BIPSimpleApplication.Request(self, apdu)

    def Indication(self, apdu):
        # cut down on debug messages on busy networks
        if not isinstance(apdu, UnconfirmedRequestPDU):
            print "MyApplication.Indication:", apdu
            apdu.DebugContents()
            print
            
        BIPSimpleApplication.Indication(self, apdu)

    def Response(self, apdu):
        print "MyApplication.Response:", apdu
        apdu.DebugContents()
        print
        
        BIPSimpleApplication.Response(self, apdu)

    def Confirmation(self, apdu):
        print "MyApplication.Confirmation:", apdu
        apdu.DebugContents()
        print

# make a simple application
myApp = MyApplication()

#
#   RandomValueProperty
#

class RandomValueProperty(Property):

    def __init__(self, identifier):
        Property.__init__(self, identifier, Real, default=None, optional=True, mutable=False)
        
    def ReadProperty(self, obj, arrayIndex=None):
        # access an array
        if arrayIndex is not None:
            raise Error(errorClass='property', errorCode='property-is-not-an-array')
            
        # return a random value
        return random.random() * 100.0
        
    def WriteProperty(self, obj, value, arrayIndex=None, priority=None):
        raise Error(errorClass='property', errorCode='write-access-denied')
    
#
#   Random Value Object Type
#

class RandomAnalogInputObject(AnalogInputObject):
    properties = \
        [ RandomValueProperty('present-value')
        ]

RegisterObjectType(RandomAnalogInputObject)

# make one
raio = RandomAnalogInputObject(objectIdentifier=('analog-input', 1), objectName='Random')

# add it to the device
myApp.AddObject(raio)

# start the threads
Thread.StartThreads()

go = True
while go:
    try:
        line = sys.stdin.readline()[:-1]
    except KeyboardInterrupt:
        break
    
    print "thisDevice:"
    thisDevice.DebugContents()
    print
    print "raio:"
    raio.DebugContents()
    print
    
# halt
Thread.HaltThreads()
