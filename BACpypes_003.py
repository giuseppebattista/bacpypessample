#!/usr/bin/python

import sys

from BACpypes.CommunicationsCore import Thread
if ("--debugThread" in sys.argv):
    print "imported", Thread

from BACpypes.Application import BIPSimpleApplication
from BACpypes.Object import LocalDeviceObject

from BACpypes.APDU import WhoHasRequest, IHaveRequest

# some debugging
_debug = 0

# counters
counterLock = Thread.Lock()
whoHasCounter = {}
iHaveCounter = {}

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
        
    def do_WhoHasRequest(self, apdu):
        """Respond to a Who-Has request."""
        if _debug:
            print "MyApplication.do_WhoHasRequest"
            
        key = (str(apdu.pduSource),)
        if apdu.object.objectIdentifier is not None:
            key += (str(apdu.object.objectIdentifier),)
        if apdu.object.objectName is not None:
            key += (apdu.object.objectName,)
        else:
            print "(rejected APDU:"
            apdu.DebugContents()
            print ")"
            return
            
        counterLock.acquire()
        whoHasCounter[key] = whoHasCounter.get(key,0) + 1
        counterLock.release()
            
    def do_IHaveRequest(self, apdu):
        """Respond to a I-Have request."""
        if _debug:
            print "MyApplication.do_IHaveRequest"
            
        key = (str(apdu.pduSource), str(apdu.deviceIdentifier), str(apdu.objectIdentifier), apdu.objectName)
        
        counterLock.acquire()
        iHaveCounter[key] = iHaveCounter.get(key,0) + 1
        counterLock.release()

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
    print "----- Who Has -----"
    for (src, objname), count in sorted(whoHasCounter.items()):
        print "%-20s %-30s %4d" % (src, objname, count)
    print
    print "----- I Have -----"
    for (src, devid, objid, objname), count in sorted(iHaveCounter.items()):
        print "%-20s %-20s %-20s %-20s %4d" % (src, devid, objid, objname, count)
    print
    counterLock.release()
    
# halt
Thread.HaltThreads()
