import sys

from BACpypes.CommunicationsCore import Thread
if ("--debugThread" in sys.argv):
    print "imported", Thread

from BACpypes.Application import BIPSimpleApplication
from BACpypes.Object import LocalDeviceObject
from BACpypes.APDU import WhoIsRequest, IAmRequest

# some debugging
_debug = 0

# counters
counterLock = Thread.Lock()
whoIsCounter = {}
iAmCounter = {}

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
        
    def do_WhoIsRequest(self, apdu):
        """Respond to a Who-Is request."""
        if _debug:
            print "MyApplication.do_WhoIsRequest"
            
        key = (str(apdu.pduSource), apdu.deviceInstanceRangeLowLimit, apdu.deviceInstanceRangeHighLimit)
        
        counterLock.acquire()
        whoIsCounter[key] = whoIsCounter.get(key,0) + 1
        counterLock.release()
        
        # pass back to the default implementation
        BIPSimpleApplication.do_WhoIsRequest(self, apdu)
        
    def do_IAmRequest(self, apdu):
        """Given an I-Am request, cache it."""
        if _debug:
            print "MyApplication.do_IAmRequest"
            
        key = (str(apdu.pduSource), apdu.iAmDeviceIdentifier[1])
        
        counterLock.acquire()
        iAmCounter[key] = iAmCounter.get(key,0) + 1
        counterLock.release()
        
        # pass back to the default implementation
        BIPSimpleApplication.do_IAmRequest(self, apdu)
            
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
    
    counterLock.acquire()
    print
    print "----- Who Is -----"
    for (src, lowlim, hilim), count in sorted(whoIsCounter.items()):
        print "%-20s %8s %8s %4d" % (src, lowlim, hilim, count)
        
    print
    print "----- I Am -----"
    for (src, devid), count in sorted(iAmCounter.items()):
        print "%-20s %8d %4d" % (src, devid, count)
    print
    counterLock.release()
    
# halt
Thread.HaltThreads()
