#!/usr/bin/env python

"""
Module that wraps threads with a name and puts them in a list.  While 
threads already have a name and there is a way to get a list of the 
currently active threads (see threading.enumerate()), I needed a way to 
list of all of them to show the ones that should be running but are not.
"""

import sys
import time
import thread
import threading
import traceback

from pprint import pprint

# some debugging
_debug = 0
_debugLock = ('--debugLock' in sys.argv)

#
#   Thread
#

gThreads = []

class Thread(threading.Thread):
    def __init__(self,name):
        threading.Thread.__init__(self, name=name)
        
        # save the name
        self.threadName = name
        
        # add this to the list of threads
        gThreads.append(self)

    def setName(self, name):
        # pass to the threading object
        threading.Thread.setName(self, name)
        
        # keep a copy
        self.threadName = name

    def getName(self):
        return self.threadName

#

lockMapLock = threading.Lock()

# indexed by lock
lockPending = {}        # list of threads waiting for a lock
lockAcquired = {}       # thread that acquired a lock
lockSignature = {}      # signatures of how a lock was acquired

# indexed by thread
threadPending = {}      # lock attempting to be acquired by a thread
threadAcquired = {}     # list of locks held by a thread

#
#   Snapshot
#

def Snapshot(lockit=True):
    """Print a snapshot of the lock map."""
    if lockit:
        lockMapLock.acquire()
        
    print
    print "===== lockPending ====="
    for lock, waitingList in lockPending.items():
        print lock
        for aThread, aLock, aTrace in waitingList:
            print "   ", aThread
            for aThing in aTrace:
                print "       ", aThing
    print
    print "===== lockAcquired ====="
    pprint(lockAcquired)
    print
    print "===== lockSignature ====="
    for lock, sig in lockSignature.items():
        print lock
        aThread, aLock, aTrace = sig
        print "   ", aThread
        for aThing in aTrace:
            print "       ", aThing
    print
    print "===== threadPending ====="
    pprint(threadPending)
    print
    print "===== threadAcquired ====="
    pprint(threadAcquired)
    print
    
    if lockit:
        lockMapLock.release()

    sys.stdout.flush()

#
#   LockBase
#

class LockBase:

    def __init__(self, obj=None):
        """Initialize, note that the debug print is after the initialization, so it can print!"""
        # the actual lock used depends on the derived class
        self.lock = None
        
        # a reference to some object
        self.obj = obj
        
        if _debugLock:
            print self, "initialized"
            
    def acquire(self):
        # lock transition
        lockMapLock.acquire()
        currentThread = threading.currentThread()
        currentSignature = (currentThread, self, traceback.extract_stack()[:-1])
        if _debugLock:
            print currentThread, "acquiring", self
            print "   ", currentSignature[2:]
        
        # add the current thread to the waiting list
        waitingList = lockPending.get(self, [])
        waitingList.append(currentSignature)
        lockPending[self] = waitingList
        
        # record which lock this thread is waiting on
        threadPending[currentThread] = self
        
        # check for everyone pending on a lock that is held
        if Deadlock():
            print "***** DEADLOCK *****"
            print currentThread, "acquiring", self
            Snapshot(False)
            
        # now we're ready to wait
        lockMapLock.release()
        
        # now try and get the real lock
        self.lock.acquire()
        
        # lock transition
        lockMapLock.acquire()
        if _debugLock:
            print currentThread, "acquired", self
        
        # remove it from the waiting list
        waitingList.remove(currentSignature)
        if not waitingList:
            del lockPending[self]
        
        # cancel the pending reference
        del threadPending[currentThread]
        
        # this might be a reentrant lock we have already acquired
        if isinstance(self, RLock) and (self.lock._RLock__count > 1):
            if _debugLock:
                print "    - already holding this lock"
        else:
            # see if a different thread still thinks it is holding the lock
            otherThread = lockAcquired.get(self, None)
            if otherThread:
                if _debugLock:
                    print "    -", otherThread, "still thinks it's holding it"
                try:
                    del lockAcquired[self]
                    del lockSignature[self]
                    
                    # remove it from the list of locks the thread acquired
                    heldList = threadAcquired[otherThread]
                    heldList.remove(self)
                    if not heldList:
                        del threadAcquired[otherThread]
                except:
                    print "!Exception  otherThread couldn't be released"
                    Snapshot(False)
                    sys.exit(1)
            
            # record which thread is holding this lock
            lockAcquired[self] = currentThread
            lockSignature[self] = currentSignature
            
            try:
                # update the list of the locks this thread has acquired
                heldList = threadAcquired.get(currentThread,[])
                heldList.append(self)
                threadAcquired[currentThread] = heldList
            except:
                print "!Exception  heldList couldn't be updated"
                Snapshot(False)
                sys.exit(1)
        
        lockMapLock.release()
        
    def release(self):
        # lock transition
        lockMapLock.acquire()
        currentThread = threading.currentThread()
        if _debugLock:
            print currentThread, "releasing", self
            print "    lockAcquired:", lockAcquired.get(self, None)
        # allow other lock transitions
        lockMapLock.release()
        
        # release the lock
        self.lock.release()

        # lock transition
        lockMapLock.acquire()
        currentThread = threading.currentThread()
        if _debugLock:
            print currentThread, "released", self
        
        # see who thinks has this lock
        otherThread = lockAcquired.get(self, None)
        if otherThread is None:
            if _debugLock:
                print "    - some other thread has acquired and released it"
        elif otherThread is not currentThread:
            if _debugLock:
                print "    - some other thread has acquired and still has it"
        else:
            # flag if this is a reentrant lock we are holding more than once
            multiHold = isinstance(self, RLock) and (self.lock._RLock__count >= 1)
            
            if multiHold:
                if _debugLock:
                    print "    - reentrant lock held more than once"
            else:
                # remove the record of which thread is holding this lock
                try:
                    del lockAcquired[self]
                except:
                    print "Exception!  lockAcquired does not have", self
                    Snapshot(False)
                    sys.exit(1)
                    
                try:
                    del lockSignature[self]
                except:
                    print "Exception!  lockSignature does not have", self
                    Snapshot(False)
                    sys.exit(1)
                    
                    # remove it from the list of locks this thread has acquired
                try:
                    heldList = threadAcquired[currentThread]
                    heldList.remove(self)
                    if not heldList:
                        del threadAcquired[currentThread]
                except:
                    print "Exception!  threadAcquired problem"
                    Snapshot(False)
                    sys.exit(1)
                
        # allow other lock transitions
        lockMapLock.release()
        
    def __repr__(self):
        return "<Thread(%s) 0x%08X %s>" % (self.__class__.__name__, -id(self), self.obj)
       
#
#   Lock
#

class Lock(LockBase):

    def __init__(self, obj=None):
        LockBase.__init__(self, obj)
        self.lock = threading.Lock()
        
    def locked(self):
        return self.lock.locked()
        
#
#   RLock
#

class RLock(LockBase):

    def __init__(self, obj=None):
        LockBase.__init__(self, obj)
        self.lock = threading.RLock()
        
#
#   Deadlock
#

def Deadlock(rlock=False):
    """Detect deadlock conditions."""
    if _debugLock:
        print "DeadLock"
        
    # assume the worst
    deadlockFound = True
    
    # check for everyone pending on a lock that is held
    for someThread, someLock in threadPending.items():
        otherThread = lockAcquired.get(someLock, None)
        if not otherThread:
            if _debugLock:
                print "    =", someThread, "waiting for", someLock, "will be satisified"
            deadlockFound = False
        elif otherThread is someThread:
            # circular reference
            if isinstance(someLock, RLock):
                if _debugLock:
                    print "    =", someThread, "waiting for", someLock, "will be satisified (reentrant)"
                deadlockFound = False
            else:
                if _debugLock:
                    print "    =", someThread, "waiting for", someLock, "is a circular deadlock"
#                return True
        elif not threadPending.has_key(otherThread):
            if _debugLock:
                print "    =", someThread, "waiting for", someLock, "will be satisified when", otherThread, "completes"
            deadlockFound = False
    else:
        if _debugLock:
            print "    = deadlock found:", deadlockFound
        return deadlockFound

#
#   GetThreadList
#

def GetThreadList():
    return gThreads

#
#   DeleteThread
#

def DeleteThread(threadName):
    """Remove a thread from the list, usually to keep it from starting."""
    for i in range(len(gThreads)):
        if gThreads[i].threadName == threadName:
            del gThreads[i]
            return
            
    raise RuntimeError, "no such thread '%s'" % (threadName,)

#
#   StartThreads
#

def StartThreads():
    """When applications initialize the threads have not been started,
    this function is called to start them."""
    if _debug:
        print "StartThreads"
        
    for thread in gThreads:
        if _debug:
            print "    - starting:", thread.threadName
        thread.start()

#
#   HaltThreads
#

def HaltThreads():
    """Stop the threads, it would be nice if they could be started back up."""
    if _debug:
        print "HaltThreads"
        
    for thread in gThreads:
        if thread.isAlive():
            if _debug:
                print "    - halting:", thread.threadName
            thread.halt()
            
    if _debug:
        print "    - wait a bit"
        
    time.sleep(0.100)

#
#   AliveThreads
#

def AliveThreads():
    """Return a list of the names of threads that are still alive."""
    rslt = []
    for thread in gThreads:
        if thread.isAlive():
            rslt.append(thread.threadName)
    return rslt
    
#
#   DaemonicThreads
#

def DaemonicThreads():
    """Return a list of the names of threads that are daemonic."""
    rslt = []
    for thread in gThreads:
        if thread.isDaemon():
            rslt.append(thread.threadName)
    return rslt
    
#
#   DeadThreads
#

def DeadThreads():
    """Return a list of the names of threads that have died."""
    rslt = []
    for thread in gThreads:
        if not thread.isAlive():
            rslt.append(thread.threadName)
    return rslt
