import sys

from BACpypes.CommunicationsCore import Thread
if ("--debugThread" in sys.argv):
    print "imported", Thread

from BACpypes.Application import BIPSimpleApplication
from BACpypes.Object import LocalDeviceObject

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
        BIPSimpleApplication.Request(self, apdu)

    def Indication(self, apdu):
        print "MyApplication.Indication:", apdu
        BIPSimpleApplication.Indication(self, apdu)

    def Response(self, apdu):
        print "MyApplication.Response:", apdu
        BIPSimpleApplication.Response(self, apdu)

    def Confirmation(self, apdu):
        print "MyApplication.Confirmation:", apdu
        BIPSimpleApplication.Confirmation(self, apdu)

# make a simple application
myApp = MyApplication()

# start the threads
Thread.StartThreads()

go = True
while go:
    try:
        line = sys.stdin.readline()[:-1]
    except KeyboardInterrupt:
        break
    
# halt
Thread.HaltThreads()
