
import sys
import traceback

from Exceptions import *

from copy import copy as _copy
from time import time as _time

from CommunicationsCore import Client, Server, Bind, \
    ServiceAccessPoint, ApplicationServiceElement
from Task import OneShotTask

from APDU import *

# some debuging
_debug = ('--debugApplicationService' in sys.argv)
_debugSegmentation = _debug or ('--debugSegmentation' in sys.argv)

#
#   DeviceInfo
#

class DeviceInfo:

    def __init__(self, address=None, segmentationSupported='no-segmentation', maxApduLengthAccepted=1024, maxSegmentsAccepted=None):
        if address is None:
            pass
        elif isinstance(address, Address):
            pass
        elif isinstance(address, LocalStation):
            pass
        elif isinstance(address, RemoteStation):
            pass
        else:
            raise TypeError, "address"
                
        self.address = address                              # LocalStation or RemoteStation
        self.segmentationSupported = segmentationSupported  # normally no segmentation
        self.maxApduLengthAccepted = maxApduLengthAccepted  # how big to divide up apdu's
        self.maxSegmentsAccepted = maxSegmentsAccepted      # limit on how many segments to recieve

    def DebugContents(self):
        print "    address =", self.address
        print "    segmentationSupported =", self.segmentationSupported
        print "    maxApduLengthAccepted =", self.maxApduLengthAccepted
        print "    maxSegmentsAccepted =", self.maxSegmentsAccepted
    
#----------------------------------------------------------------------

#
#   SSM - Segmentation State Machine
#

# transaction states
IDLE = 0
SEGMENTED_REQUEST = 1
AWAIT_CONFIRMATION = 2
AWAIT_RESPONSE = 3
SEGMENTED_RESPONSE = 4
SEGMENTED_CONFIRMATION = 5
COMPLETED = 6
ABORTED = 7

class SSM(OneShotTask):

    transactionLabels = ['IDLE'
        , 'SEGMENTED_REQUEST', 'AWAIT_CONFIRMATION', 'AWAIT_RESPONSE'
        , 'SEGMENTED_RESPONSE', 'SEGMENTED_CONFIRMATION', 'COMPLETED', 'ABORTED'
        ]

    def __init__(self, sap):
        """Common parts for client and server segmentation."""
        OneShotTask.__init__(self)

        self.ssmSAP = sap                   # reference to the service access point
        self.remoteDevice = None            # remote device
        self.invokeID = None                # invoke ID

        self.state = IDLE                   # initial state
        self.segmentAPDU = None             # refers to request or response
        self.segmentSize = None             # how big the pieces are
        self.segmentCount = None
        self.maxSegmentsAccepted = None     # maximum number of segments client will accept

        self.retryCount = None
        self.segmentRetryCount = None
        self.sentAllSegments = None
        self.lastSequenceNumber = None
        self.initialSequenceNumber = None
        self.actualWindowSize = None
        self.proposedWindowSize = None

    def StartTimer(self, msecs):
        if _debugSegmentation:
            print self, "SSM.StartTimer", msecs

        # if this is active, pull it
        if self.isScheduled:
            self.SuspendTask()

        # now install this
        self.InstallTask(_time() + (msecs / 1000.0))

    def StopTimer(self):
        if _debugSegmentation:
            print self, "SSM.StopTimer"

        self.SuspendTask()

    def RestartTimer(self, msecs):
        if _debugSegmentation:
            print self, "SSM.RestartTimer", msecs

        # if this is active, pull it
        if self.isScheduled:
            self.SuspendTask()

        # now install this
        self.InstallTask(_time() + (msecs / 1000.0))

    def SetState(self, newState, timer=0):
        """This function is called when the derived class wants to change
        state."""
        if _debugSegmentation:
            print self, "SSM.SetState", SSM.transactionLabels[newState]

        # make sure we have a correct transition
        if (self.state == COMPLETED) or (self.state == ABORTED):
            raise RuntimeError, "invalid state transition from %s to %s" % (SSM.transactionLabels[self.state], SSM.transactionLabels[newState])

        self.state = newState

        # stop any current timer
        self.StopTimer()

        # make the change
        self.state = newState

        # if another timer should be started, start it
        if timer:
            self.StartTimer(timer)

    def SetSegmentationContext(self, apdu):
        """This function is called to set the segmentation context."""
        if _debugSegmentation:
            print self, "SSM.SetSegmentationContext", apdu

        # set the context
        self.segmentAPDU = apdu

    def GetSegment(self, indx):
        """This function returns an APDU coorisponding to a particular
        segment of a confirmed request or complex ack.  The segmentAPDU
        is the context."""
        if _debugSegmentation:
            print self, "SSM.GetSegment", indx

        # check for no context
        if not self.segmentAPDU:
            raise RuntimeError, "no segmentation context established"

        # check for invalid segment number
        if indx >= self.segmentCount:
            raise RuntimeError, "invalid segment number %d, APDU has %d segments" % (indx, self.segmentCount)

        if self.segmentAPDU.apduType == ConfirmedRequestPDU.pduType:
            if _debugSegmentation:
                print "    - confirmed request context"

            segAPDU = ConfirmedRequestPDU(self.segmentAPDU.apduService)

            segAPDU.apduMaxSegs = self.maxSegmentsAccepted
            segAPDU.apduMaxResp = self.ssmSAP.maxApduLengthAccepted
            segAPDU.apduInvokeID = self.invokeID;

            # segmented response accepted?
            segAPDU.apduSA = ((self.ssmSAP.segmentationSupported == 'segmented-both') \
                    or (self.ssmSAP.segmentationSupported == 'segmented-receive'))
            if _debugSegmentation:
                print "    - segmented response accepted:", segAPDU.apduSA
                print "        - self.ssmSAP.segmentationSupported", self.ssmSAP.segmentationSupported

        elif self.segmentAPDU.apduType == ComplexAckPDU.pduType:
            if _debugSegmentation:
                print "    - complex ack context"

            segAPDU = ComplexAckPDU(self.segmentAPDU.apduService, self.segmentAPDU.apduInvokeID)
        else:
            raise RuntimeError, "invalid APDU type for segmentation context"

        # make sure the destination is set
        segAPDU.pduDestination = self.remoteDevice.address

        # segmented message?
        if (self.segmentCount != 1):
            segAPDU.apduSeg = True
            segAPDU.apduMor = (indx < (self.segmentCount - 1)) # more follows
            segAPDU.apduSeq = indx % 256                       # sequence number
            segAPDU.apduWin = self.proposedWindowSize          # window size
        else:
            segAPDU.apduSeg = False
            segAPDU.apduMor = False

        # add the content
        offset = indx * self.segmentSize
        segAPDU.PutData( self.segmentAPDU.pduData[offset:offset+self.segmentSize] )

        if _debugSegmentation:
            print "-segAPDU-"
            segAPDU.DebugContents()
            
        # success
        return segAPDU

    def AppendSegment(self, apdu):
        """This function appends the apdu content to the end of the current
        APDU being built.  The segmentAPDU is the context."""
        if _debugSegmentation:
            print self, "SSM.AppendSegment"
            print "-apdu-"
            apdu.DebugContents()

        # check for no context
        if not self.segmentAPDU:
            raise RuntimeError, "no segmentation context established"

        # append the data
        self.segmentAPDU.PutData(apdu.pduData)

    def InWindow(self, seqA, seqB):
        if _debugSegmentation:
            print self, "SSM.InWindow", seqA, seqB
            print "    - actualWindowSize", self.actualWindowSize

        rslt = ((seqA - seqB + 256) % 256) < self.actualWindowSize
        if _debugSegmentation:
            print "    - rslt", rslt

        return rslt

    def FillWindow(self, seqNum):
        """This function sends all of the packets necessary to fill
        out the segmentation window."""
        if _debugSegmentation:
            print self, "SSM.FillWindow", seqNum
            print "    - actualWindowSize", self.actualWindowSize

        for ix in range(self.actualWindowSize):
            apdu = self.GetSegment(seqNum + ix)

            # send the message
            self.ssmSAP.Request(apdu)

            # check for no more follows
            if not apdu.apduMor:
                self.sentAllSegments = True
                break

    def DebugContents(self, indent=1):
        print "%s%s =" % ("    " * indent, 'state'), self.state, SSM.transactionLabels[self.state]
        print "%s%s =" % ("    " * indent, 'segmentSize'), self.segmentSize
        print "%s%s =" % ("    " * indent, 'segmentCount'), self.segmentCount
        print "%s%s =" % ("    " * indent, 'maxSegmentsAccepted'), self.maxSegmentsAccepted
        print "%s%s =" % ("    " * indent, 'retryCount'), self.retryCount
        print "%s%s =" % ("    " * indent, 'segmentRetryCount'), self.segmentRetryCount
        print "%s%s =" % ("    " * indent, 'sentAllSegments'), self.sentAllSegments
        print "%s%s =" % ("    " * indent, 'lastSequenceNumber'), self.lastSequenceNumber
        print "%s%s =" % ("    " * indent, 'initialSequenceNumber'), self.initialSequenceNumber
        print "%s%s =" % ("    " * indent, 'actualWindowSize'), self.actualWindowSize
        print "%s%s =" % ("    " * indent, 'proposedWindowSize'), self.proposedWindowSize
        print "%s%s =" % ("    " * indent, 'segmentAPDU'), self.segmentAPDU
        if self.segmentAPDU:
            self.segmentAPDU.DebugContents()
    
#
#   ClientSSM - Client Segmentation State Machine
#

class ClientSSM(SSM):

    def __init__(self, sap):
        SSM.__init__(self, sap)
        
        # initialize the retry count
        self.retryCount = 0

    def SetState(self, newState, timer=0):
        """This function is called when the client wants to change state."""
        if _debugSegmentation:
            print self, "ClientSSM.SetState"

        # pass the change down
        SSM.SetState(self, newState, timer)

        # completed or aborted, remove tracking
        if (newState == COMPLETED) or (newState == ABORTED):
            self.ssmSAP.clientTransactions.remove(self)

    def Request(self, apdu):
        """This function is called by client transaction functions when it wants
        to send a message to the device."""
        if _debugSegmentation:
            print self, "ClientSSM.Request", apdu

        # make sure it has a good source and destination
        apdu.pduSource = None
        apdu.pduDestination = self.remoteDevice.address

        # send it via the device
        self.ssmSAP.Request(apdu)

    def Indication(self, apdu):
        """This function is called after the device has bound a new transaction
        and wants to start the process rolling."""
        if _debugSegmentation:
            print self, "ClientSSM.Indication", apdu
            self.DebugContents()

        # make sure we're getting confirmed requests
        if (apdu.apduType != ConfirmedRequestPDU.pduType):
            raise RuntimeError, "invalid APDU (1)"

        # save the request and set the segmentation context
        self.SetSegmentationContext(apdu)

        # save the maximum number of segments acceptable in the reply
        if apdu.apduMaxSegs is not None:
            # this request overrides the default
            self.maxSegmentsAccepted = apdu.apduMaxSegs
        else:
            # use the default in the device definition
            self.maxSegmentsAccepted = self.ssmSAP.maxSegmentsAccepted

        # save the invoke ID
        self.invokeID = apdu.apduInvokeID
        if _debugSegmentation:
            print "    - invoke ID", self.invokeID

        # get information about the device
        self.remoteDevice = self.ssmSAP.GetDeviceInfo(apdu.pduDestination)
        if _debugSegmentation:
            self.remoteDevice.DebugContents()

        # the segment size is the minimum of what I want to transmit and
        # what the device can receive
        self.segmentSize = min(self.ssmSAP.maxApduLengthAccepted, self.remoteDevice.maxApduLengthAccepted)
        if _debugSegmentation:
            print "    - segment size =", self.segmentSize

        # compute the segment count ### minus the header?
        self.segmentCount, more = divmod(len(apdu.pduData), self.segmentSize)
        if more:
            self.segmentCount += 1
        if _debugSegmentation:
            print "    - segment count =", self.segmentCount

        # make sure we support segmented transmit if we need to
        if self.segmentCount > 1:
            if (self.ssmSAP.segmentationSupported != 'segmented-transmit') and (self.ssmSAP.segmentationSupported != 'segmented-both'):
                if _debugSegmentation:
                    print "    - local device can't send segmented messages"
                abort = self.Abort(BACnetAbortReason.SEGMENTATIONNOTSUPPORTED)
                self.Response(abort)
                return
            if (self.remoteDevice.segmentationSupported != 'segmented-receive') and (self.remoteDevice.segmentationSupported != 'segmented-both'):
                if _debugSegmentation:
                    print "    - remote device can't receive segmented messages"
                abort = self.Abort(BACnetAbortReason.SEGMENTATIONNOTSUPPORTED)
                self.Response(abort)
                return

        # send out the first segment (or the whole thing)
        if self.segmentCount == 1:
            # SendConfirmedUnsegmented
            self.sentAllSegments = True
            self.retryCount = 0
            self.SetState(AWAIT_CONFIRMATION, self.ssmSAP.retryTimeout)
        else:
            # SendConfirmedSegmented
            self.sentAllSegments = False
            self.retryCount = 0
            self.segmentRetryCount = 0
            self.initialSequenceNumber = 0
            self.proposedWindowSize = self.ssmSAP.maxSegmentsAccepted
            self.actualWindowSize = 1
            self.SetState(SEGMENTED_REQUEST, self.ssmSAP.segmentTimeout)

        # deliver to the device
        self.Request(self.GetSegment(0))

    def Response(self, apdu):
        """This function is called by client transaction functions when they want
        to send a message to the application."""
        if _debugSegmentation:
            print self, "ClientSSM.Response", apdu

        # make sure it has a good source and destination
        apdu.pduSource = self.remoteDevice.address
        apdu.pduDestination = None

        # send it to the application
        self.ssmSAP.SAPResponse(apdu)

    def Confirmation(self, apdu):
        """This function is called by the device for all upstream messages related
        to the transaction."""
        if _debugSegmentation:
            print self, "ClientSSM.Confirmation", apdu
            self.DebugContents()

        if self.state == SEGMENTED_REQUEST:
            self.SegmentedRequest(apdu)
        elif self.state == AWAIT_CONFIRMATION:
            self.AwaitConfirmation(apdu)
        elif self.state == SEGMENTED_CONFIRMATION:
            self.SegmentedConfirmation(apdu)
        else:
            raise RuntimeError, "invalid state"

    def ProcessTask(self):
        """This function is called when something has taken too long."""
        if _debugSegmentation:
            print self, "ClientSSM.ProcessTask"
            self.DebugContents()

        if self.state == SEGMENTED_REQUEST:
            self.SegmentedRequestTimeout()
        elif self.state == AWAIT_CONFIRMATION:
            self.AwaitConfirmationTimeout()
        elif self.state == SEGMENTED_CONFIRMATION:
            self.SegmentedConfirmationTimeout()
        elif self.state == COMPLETED:
            pass
        elif self.state == ABORTED:
            pass
        else:
            raise RuntimeError, "invalid state"

    def Abort(self, reason):
        """This function is called when the transaction should be aborted."""
        if _debugSegmentation:
            print "=" * 20, "ABORT", reason, "=" * 20
            print self, "ClientSSM.Abort", reason

        # change the state to aborted
        self.SetState(ABORTED)

        # return an abort APDU
        return AbortPDU(False, self.invokeID, reason)

    def SegmentedRequest(self, apdu):
        """This function is called when the client is sending a segmented request
        and receives an apdu."""
        if _debugSegmentation:
            print self, "ClientSSM.SegmentedRequest", apdu

        # client is ready for the next segment
        if apdu.apduType == SegmentAckPDU.pduType:
            if _debugSegmentation:
                print "    - segment ack"
                print "        - apdu.apduSeq", apdu.apduSeq
                print "        - apdu.apduNak", apdu.apduNak

            # duplicate ack received?
            if not self.InWindow(apdu.apduSeq, self.initialSequenceNumber):
                if _debugSegmentation:
                    print "    - not in window"
                self.RestartTimer(self.ssmSAP.segmentTimeout)

            # final ack received?
            elif self.sentAllSegments:
                if _debugSegmentation:
                    print "    - all done sending request"
                self.SetState(AWAIT_CONFIRMATION, self.ssmSAP.retryTimeout)

            # more segments to send
            else:
                if _debugSegmentation:
                    print "    - more segments to send"

                self.initialSequenceNumber = (apdu.apduSeq + 1) % 256
                self.actualWindowSize = apdu.apduWin
                self.segmentRetryCount = 0
                self.FillWindow(self.initialSequenceNumber)
                self.RestartTimer(self.ssmSAP.segmentTimeout)

        # simple ack
        elif (apdu.apduType == SimpleAckPDU.pduType):
            if _debugSegmentation:
                print "    - simple ack"

            if not self.sentAllSegments:
                abort = self.Abort(BACnetAbortReason.INVALIDAPDUINTHISSTATE)
                self.Request(abort)     # send it to the device
                self.Response(abort)    # send it to the application
            else:
                self.SetState(COMPLETED)
                self.Response(apdu)

        elif (apdu.apduType == ComplexAckPDU.pduType):
            if _debugSegmentation:
                print "    - complex ack"

            if not self.sentAllSegments:
                abort = self.Abort(BACnetAbortReason.INVALIDAPDUINTHISSTATE)
                self.Request(abort)     # send it to the device
                self.Response(abort)    # send it to the application

            elif not apdu.apduSeg:
                self.SetState(COMPLETED)
                self.Response(apdu)

            else:
                # set the segmented response context
                self.SetSegmentationContext(apdu)

                self.actualWindowSize = min(apdu.apduWin, self.ssmSAP.maxSegmentsAccepted)
                self.lastSequenceNumber = 0
                self.initialSequenceNumber = 0
                self.SetState(SEGMENTED_CONFIRMATION, self.ssmSAP.segmentTimeout)

        # some kind of problem
        elif (apdu.apduType == ErrorPDU.pduType) or (apdu.apduType == RejectPDU.pduType) or (apdu.apduType == AbortPDU.pduType):
            if _debugSegmentation:
                print "    - error/reject/abort"

            self.SetState(COMPLETED)
            self.response = apdu
            self.Response(apdu)

        else:
            raise RuntimeError, "invalid APDU (2)"

    def SegmentedRequestTimeout(self):
        if _debugSegmentation:
            print self, "ClientSSM.SegmentedRequestTimeout"

        # try again
        if self.segmentRetryCount < self.ssmSAP.retryCount:
            if _debugSegmentation:
                print "    - retry segmented request"

            self.segmentRetryCount += 1
            self.StartTimer(self.ssmSAP.segmentTimeout)
            self.FillWindow(self.initialSequenceNumber)
        else:
            if _debugSegmentation:
                print "    - abort, no response from the device"

            abort = self.Abort(BACnetAbortReason.NORESPONSE)
            self.Response(abort)

    def AwaitConfirmation(self, apdu):
        if _debugSegmentation:
            print self, "ClientSSM.AwaitConfirmation", apdu

        if (apdu.apduType == AbortPDU.pduType):
            if _debugSegmentation:
                print "    - server aborted"

            self.SetState(ABORTED)
            self.Response(apdu)

        elif (apdu.apduType == SimpleAckPDU.pduType) or (apdu.apduType == ErrorPDU.pduType) or (apdu.apduType == RejectPDU.pduType):
            if _debugSegmentation:
                print "    - simple ack, error, or reject"

            self.SetState(COMPLETED)
            self.Response(apdu)

        elif (apdu.apduType == ComplexAckPDU.pduType):
            if _debugSegmentation:
                print "    - complex ack"

            # if the response is not segmented, we're done
            if not apdu.apduSeg:
                if _debugSegmentation:
                    print "    - unsegmented"

                self.SetState(COMPLETED)
                self.Response(apdu)

            elif (self.ssmSAP.segmentationSupported != 'segmented-receive') and (self.ssmSAP.segmentationSupported != 'segmented-both'):
                if _debugSegmentation:
                    print "    - local device can't receive segmented messages"
                abort = self.Abort(BACnetAbortReason.SEGMENTATIONNOTSUPPORTED)
                self.Response(abort)

            elif apdu.apduSeq == 0:
                if _debugSegmentation:
                    print "    - segmented response"

                # set the segmented response context
                self.SetSegmentationContext(apdu)

                self.actualWindowSize = min(apdu.apduWin, self.ssmSAP.maxSegmentsAccepted)
                self.lastSequenceNumber = 0
                self.initialSequenceNumber = 0
                self.SetState(SEGMENTED_CONFIRMATION, self.ssmSAP.segmentTimeout)

                # send back a segment ack
                segack = SegmentAckPDU( 0, 0, self.invokeID, self.initialSequenceNumber, self.actualWindowSize )
                self.Request(segack)

            else:
                if _debugSegmentation:
                    print "    - invalid APDU in this state"

                abort = self.Abort(BACnetAbortReason.INVALIDAPDUINTHISSTATE)
                self.Request(abort) # send it to the device
                self.Response(abort) # send it to the application

        elif (apdu.apduType == SegmentAckPDU.pduType):
            if _debugSegmentation:
                print "    - segment ack(!?)"

            self.RestartTimer(self.ssmSAP.segmentTimeout)

        else:
            raise RuntimeError, "invalid APDU (3)"

    def AwaitConfirmationTimeout(self):
        if _debugSegmentation:
            print self, "ClientSSM.AwaitConfirmationTimeout"

        self.retryCount += 1
        if self.retryCount < self.ssmSAP.retryCount:
            if _debugSegmentation:
                print "    - no response, try again (%d < %d)" % (self.retryCount, self.ssmSAP.retryCount)

            # save the retry count, Indication acts like the request is coming
            # from the application so the retryCount gets re-initialized.
            saveCount = self.retryCount
            self.Indication(self.segmentAPDU)
            self.retryCount = saveCount
        else:
            if _debugSegmentation:
                print "    - retry count exceeded"
            abort = self.Abort(BACnetAbortReason.NORESPONSE)
            self.Response(abort)

    def SegmentedConfirmation(self, apdu):
        if _debugSegmentation:
            print self, "ClientSSM.SegmentedConfirmation", apdu

        # the only messages we should be getting are complex acks
        if (apdu.apduType != ComplexAckPDU.pduType):
            if _debugSegmentation:
                print "    - complex ack required"

            abort = self.Abort(BACnetAbortReason.INVALIDAPDUINTHISSTATE)
            self.Request(abort) # send it to the device
            self.Response(abort) # send it to the application
            return

        # it must be segmented
        if not apdu.apduSeg:
            if _debugSegmentation:
                print "    - must be segmented"

            abort = self.Abort(BACnetAbortReason.INVALIDAPDUINTHISSTATE)
            self.Request(abort) # send it to the device
            self.Response(abort) # send it to the application
            return

        # proper segment number
        if apdu.apduSeq != (self.lastSequenceNumber + 1) % 256:
            if _debugSegmentation:
                print "    - segment", apdu.apduSeq, "received out of order, should be", (self.lastSequenceNumber + 1) % 256

            # segment received out of order
            self.RestartTimer(self.ssmSAP.segmentTimeout)
            segack = SegmentAckPDU( 1, 0, self.invokeID, self.lastSequenceNumber, self.actualWindowSize )
            self.Request(segack)
            return

        # add the data
        self.AppendSegment(apdu)

        # update the sequence number
        self.lastSequenceNumber = (self.lastSequenceNumber + 1) % 256

        # last segment received
        if not apdu.apduMor:
            if _debugSegmentation:
                print "    - no more follows"

            # send a final ack
            segack = SegmentAckPDU( 0, 0, self.invokeID, self.lastSequenceNumber, self.actualWindowSize )
            self.Request(segack)

            self.SetState(COMPLETED)
            self.Response(self.segmentAPDU)

        elif apdu.apduSeq == ((self.initialSequenceNumber + self.actualWindowSize) % 256):
            if _debugSegmentation:
                print "    - last segment in the group"

            self.initialSequenceNumber = self.lastSequenceNumber
            self.RestartTimer(self.ssmSAP.segmentTimeout)
            segack = SegmentAckPDU( 0, 0, self.invokeID, self.lastSequenceNumber, self.actualWindowSize )
            self.Request(segack)

        else:
            # wait for more segments
            if _debugSegmentation:
                print "    - wait for more segments"

            self.RestartTimer(self.ssmSAP.segmentTimeout)

    def SegmentedConfirmationTimeout(self):
        if _debugSegmentation:
            print self, "ClientSSM.SegmentedConfirmationTimeout"

        abort = self.Abort(BACnetAbortReason.NORESPONSE)
        self.Response(abort)

#
#   ServerSSM - Server Segmentation State Machine
#

class ServerSSM(SSM):

    def __init__(self, sap):
        SSM.__init__(self, sap)

    def SetState(self, newState, timer=0):
        """This function is called when the client wants to change state."""
        if _debugSegmentation:
            print self, "ServerSSM.SetState"

        # pass the change down
        SSM.SetState(self, newState, timer)

        # completed or aborted, remove tracking
        if (newState == COMPLETED) or (newState == ABORTED):
            self.ssmSAP.serverTransactions.remove(self)

    def Request(self, apdu):
        """This function is called by transaction functions to send
        to the application."""
        if _debugSegmentation:
            print self, "ServerSSM.Request", apdu

        # make sure it has a good source and destination
        apdu.pduSource = self.remoteDevice.address
        apdu.pduDestination = None

        # send it via the device
        self.ssmSAP.SAPRequest(apdu)

    def Indication(self, apdu):
        """This function is called for each downstream packet related to
        the transaction."""
        if _debugSegmentation:
            print self, "ServerSSM.Indication", apdu
            self.DebugContents()

        if self.state == IDLE:
            self.Idle(apdu)
        elif self.state == SEGMENTED_REQUEST:
            self.SegmentedRequest(apdu)
        elif self.state == AWAIT_RESPONSE:
            self.AwaitResponse(apdu)
        elif self.state == SEGMENTED_RESPONSE:
            self.SegmentedResponse(apdu)
        else:
            print "RuntimeError - invalid state"
            self.DebugContents()
            apdu.DebugContents()
            print

    def Response(self, apdu):
        """This function is called by transaction functions when they want
        to send a message to the device."""
        if _debugSegmentation:
            print self, "ServerSSM.Response", apdu

        # make sure it has a good source and destination
        apdu.pduSource = None
        apdu.pduDestination = self.remoteDevice.address

        # send it via the device
        self.ssmSAP.Request(apdu)

    def Confirmation(self, apdu):
        """This function is called when the application has provided a response
        and needs it to be sent to the client."""
        if _debugSegmentation:
            print self, "ServerSSM.Confirmation", apdu
            self.DebugContents()

        if (apdu.apduType == AbortPDU.pduType):
            if _debugSegmentation:
                print "    - abort"

            self.SetState(ABORTED)

            # send the response to the device
            self.Response(apdu)
            return

        if self.state != AWAIT_RESPONSE:
            if _debugSegmentation:
                print "    - warning: not expecting a response"

        # simple response
        if (apdu.apduType == SimpleAckPDU.pduType) or (apdu.apduType == ErrorPDU.pduType) or (apdu.apduType == RejectPDU.pduType):
            if _debugSegmentation:
                print "    - simple ack, error, or reject"

            # transaction completed
            self.SetState(COMPLETED)

            # send the response to the device
            self.Response(apdu)
            return

        if (apdu.apduType == ComplexAckPDU.pduType):
            if _debugSegmentation:
                print "    - complex ack"

            # save the response and set the segmentation context
            self.SetSegmentationContext(apdu)

            # the segment size is the minimum of what I want to transmit and
            # what the device can receive
            self.segmentSize = min(self.ssmSAP.maxApduLengthAccepted, self.remoteDevice.maxApduLengthAccepted)
            if _debugSegmentation:
                print "    - segment size =", self.segmentSize

            # compute the segment count ### minus the header?
            self.segmentCount, more = divmod(len(apdu.pduData), self.segmentSize)
            if more:
                self.segmentCount += 1
            if _debugSegmentation:
                print "    - segment count =", self.segmentCount

            # make sure we support segmented transmit if we need to
            if self.segmentCount > 1:
                if _debugSegmentation:
                    print "    - segmentation required,", self.segmentCount, "segments"

                if (self.ssmSAP.segmentationSupported != 'segmented-transmit') and (self.ssmSAP.segmentationSupported != 'segmented-both'):
                    abort = self.Abort(BACnetAbortReason.SEGMENTATIONNOTSUPPORTED)
                    self.Request(abort)
                    return
                if (self.remoteDevice.segmentationSupported != 'segmented-receive') and (self.remoteDevice.segmentationSupported != 'segmented-both'):
                    abort = self.Abort(BACnetAbortReason.SEGMENTATIONNOTSUPPORTED)
                    self.Request(abort)
                    return

            ### check to make sure the client can receive that many
            ### look at apduMaxSegs

            # initialize the state
            self.segmentRetryCount = 0
            self.initialSequenceNumber = 0
            self.proposedWindowSize = self.ssmSAP.maxSegmentsAccepted
            self.actualWindowSize = 1

            # send out the first segment (or the whole thing)
            if self.segmentCount == 1:
                self.Response(apdu)
                self.SetState(COMPLETED)
            else:
                self.Response(self.GetSegment(0))
                self.SetState(SEGMENTED_RESPONSE, self.ssmSAP.segmentTimeout)

        else:
            raise RuntimeError, "invalid APDU (4)"

    def ProcessTask(self):
        """This function is called when the client has failed to send all of the
        segments of a segmented request, the application has taken too long to
        complete the request, or the client failed to ack the segments of a
        segmented response."""
        if _debugSegmentation:
            print self, "ServerSSM.ProcessTask"
            self.DebugContents()

        if self.state == SEGMENTED_REQUEST:
            self.SegmentedRequestTimeout()
        elif self.state == AWAIT_RESPONSE:
            self.AwaitResponseTimeout()
        elif self.state == SEGMENTED_RESPONSE:
            self.SegmentedResponseTimeout()
        elif self.state == COMPLETED:
            pass
        elif self.state == ABORTED:
            pass
        else:
            raise RuntimeError, "invalid state"

    def Abort(self, reason):
        """This function is called when the application would like to abort the
        transaction.  There is no notification back to the application."""
        if _debugSegmentation:
            print "=" * 20, "ABORT", reason, "=" * 20
            print self, "ServerSSM.Abort", reason

        # change the state to aborted
        self.SetState(ABORTED)

        # return an abort APDU
        return AbortPDU(True, self.invokeID, reason)

    def Idle(self, apdu):
        if _debugSegmentation:
            print self, "ServerSSM.Idle", apdu

        # make sure we're getting confirmed requests
        if not isinstance(apdu, ConfirmedRequestPDU):
            raise RuntimeError, "invalid APDU (5)"

        # save the invoke ID
        self.invokeID = apdu.apduInvokeID
        if _debugSegmentation:
            print "    - invoke ID", self.invokeID

        # get information about the device
        self.remoteDevice = self.ssmSAP.GetDeviceInfo(apdu.pduSource)
        if _debugSegmentation:
            self.remoteDevice.DebugContents()

        # save the number of segments the client is willing to accept in the ack
        self.maxSegmentsAccepted = apdu.apduMaxSegs

        # unsegmented request
        if not apdu.apduSeg:
            self.SetState(AWAIT_RESPONSE, self.ssmSAP.applicationTimeout)
            self.Request(apdu)
            return

        # make sure we support segmented requests
        if (self.ssmSAP.segmentationSupported != 'segmented-receive') and (self.ssmSAP.segmentationSupported != 'segmented-both'):
            abort = self.Abort(BACnetAbortReason.SEGMENTATIONNOTSUPPORTED)
            self.Response(abort)
            return

        # save the request and set the segmentation context
        self.SetSegmentationContext(apdu)

        # the window size is the minimum of what I'm willing to receive and
        # what the device has said it would like to send
        self.actualWindowSize = min(apdu.apduWin, self.ssmSAP.maxSegmentsAccepted)

        # initialize the state
        self.lastSequenceNumber = 0
        self.initialSequenceNumber = 0
        self.SetState(SEGMENTED_REQUEST, self.ssmSAP.segmentTimeout)

        # send back a segment ack
        segack = SegmentAckPDU( 0, 1, self.invokeID, self.initialSequenceNumber, self.actualWindowSize )
        if _debugSegmentation:
            print "-segack-"
            segack.DebugContents()
            
        self.Response(segack)

    def SegmentedRequest(self, apdu):
        if _debugSegmentation:
            print self, "ServerSSM.SegmentedRequest", apdu

        # some kind of problem
        if (apdu.apduType == AbortPDU.pduType):
            if _debugSegmentation:
                print "    - abort"

            self.SetState(COMPLETED)
            self.Response(apdu)
            return

        # the only messages we should be getting are confirmed requests
        elif (apdu.apduType != ConfirmedRequestPDU.pduType):
            if _debugSegmentation:
                print "    - confirmed request required"

            abort = self.Abort(BACnetAbortReason.INVALIDAPDUINTHISSTATE)
            if _debugSegmentation:
                print "-abort-"
                abort.DebugContents()
                
            self.Request(abort) # send it to the device
            self.Response(abort) # send it to the application
            return

        # it must be segmented
        elif not apdu.apduSeg:
            abort = self.Abort(BACnetAbortReason.INVALIDAPDUINTHISSTATE)
            if _debugSegmentation:
                print "-abort-"
                abort.DebugContents()
                
            self.Request(abort) # send it to the application
            self.Response(abort) # send it to the device
            return

        # proper segment number
        if apdu.apduSeq != (self.lastSequenceNumber + 1) % 256:
            if _debugSegmentation:
                print "    - segment", apdu.apduSeq, "received out of order, should be", (self.lastSequenceNumber + 1) % 256

            # segment received out of order
            self.RestartTimer(self.ssmSAP.segmentTimeout)

            # send back a segment ack
            segack = SegmentAckPDU( 1, 1, self.invokeID, self.initialSequenceNumber, self.actualWindowSize )
            if _debugSegmentation:
                print "-segack-"
                segack.DebugContents()
                
            self.Response(segack)
            return

        # add the data
        self.AppendSegment(apdu)

        # update the sequence number
        self.lastSequenceNumber = (self.lastSequenceNumber + 1) % 256

        # last segment?
        if not apdu.apduMor:
            if _debugSegmentation:
                print "    - no more follows"

            # send back a final segment ack
            segack = SegmentAckPDU( 0, 1, self.invokeID, self.lastSequenceNumber, self.actualWindowSize )
            self.Response(segack)

            # forward the whole thing to the application
            self.SetState(AWAIT_RESPONSE, self.ssmSAP.applicationTimeout)
            self.Request(self.segmentAPDU)

        elif apdu.apduSeq == ((self.initialSequenceNumber + self.actualWindowSize) % 256):
                if _debugSegmentation:
                    print "    - last segment in the group"

                self.initialSequenceNumber = self.lastSequenceNumber
                self.RestartTimer(self.ssmSAP.segmentTimeout)

                # send back a segment ack
                segack = SegmentAckPDU( 0, 1, self.invokeID, self.initialSequenceNumber, self.actualWindowSize )
                self.Response(segack)

        else:
            # wait for more segments
            if _debugSegmentation:
                print "    - wait for more segments"

            self.RestartTimer(self.ssmSAP.segmentTimeout)

    def SegmentedRequestTimeout(self):
        if _debugSegmentation:
            print self, "ServerSSM.SegmentedRequestTimeout"

        # give up
        self.SetState(ABORTED)

    def AwaitResponse(self, apdu):
        if _debugSegmentation:
            print self, "ServerSSM.AwaitResponse", apdu

        if isinstance(apdu, ConfirmedRequestPDU):
            if _debugSegmentation:
                print "    - client is trying this request again"

        elif isinstance(apdu, AbortPDU):
            if _debugSegmentation:
                print "    - client aborting this request"

            # forward abort to the application
            self.SetState(ABORTED)
            self.Request(apdu)

        else:
            raise RuntimeError, "invalid APDU (6)"

    def AwaitResponseTimeout(self):
        """This function is called when the application has taken too long
        to respond to a clients request.  The client has probably long since
        given up."""
        if _debugSegmentation:
            print self, "ServerSSM.AwaitResponseTimeout"

        abort = self.Abort(BACnetAbortReason.SERVERTIMEOUT)
        self.Request(abort)

    def SegmentedResponse(self, apdu):
        if _debugSegmentation:
            print self, "ServerSSM.SegmentedResponse", apdu

        # client is ready for the next segment
        if (apdu.apduType == SegmentAckPDU.pduType):
            if _debugSegmentation:
                print "    - segment ack"
                print "        - apdu.apduSeq", apdu.apduSeq
                print "        - apdu.apduNak", apdu.apduNak

            # duplicate ack received?
            if not self.InWindow(apdu.apduSeq, self.initialSequenceNumber):
                if _debugSegmentation:
                    print "    - not in window"
                self.RestartTimer(self.ssmSAP.segmentTimeout)

            # final ack received?
            elif self.sentAllSegments:
                if _debugSegmentation:
                    print "    - all done sending response"
                self.SetState(COMPLETED)

            else:
                if _debugSegmentation:
                    print "    - more segments to send"

                self.initialSequenceNumber = (apdu.apduSeq + 1) % 256
                self.actualWindowSize = apdu.apduWin
                self.segmentRetryCount = 0
                self.FillWindow(self.initialSequenceNumber)
                self.RestartTimer(self.ssmSAP.segmentTimeout)

        # some kind of problem
        elif (apdu.apduType == AbortPDU.pduType):
            self.SetState(COMPLETED)
            self.Response(apdu)

        else:
            raise RuntimeError, "invalid APDU (7)"

    def SegmentedResponseTimeout(self):
        if _debugSegmentation:
            print self, "ServerSSM.SegmentedResponseTimeout"

        # try again
        if self.segmentRetryCount < self.ssmSAP.retryCount:
            self.segmentRetryCount += 1
            self.StartTimer(self.ssmSAP.segmentTimeout)
            self.FillWindow(self.initialSequenceNumber)
        else:
            # give up
            self.SetState(ABORTED)

#
#   StateMachineAccessPoint
#

class StateMachineAccessPoint(DeviceInfo, Client, ServiceAccessPoint):

    def __init__(self, device, sap=None, cid=None):
        if _debug:
            print "StateMachineAccessPoint.__init__", device, sap, cid
            
        # basic initialization
        DeviceInfo.__init__(self)
        Client.__init__(self, cid)
        ServiceAccessPoint.__init__(self, sap)

        # device information from the device object
        self.segmentationSupported = device.segmentationSupported   # normally no segmentation
        self.segmentTimeout = device.apduSegmentTimeout             # how long to wait for a segAck
        self.maxApduLengthAccepted = device.maxApduLengthAccepted   # how big to divide up apdu's
        self.maxSegmentsAccepted = device.maxSegmentsAccepted       # limit on how many segments to recieve
        
        # client settings
        self.clientTransactions = []
        self.retryCount = device.numberOfApduRetries        # how many times to repeat the request
        self.retryTimeout = device.apduTimeout              # how long between retrying the request
        self.nextInvokeID = 1

        # server settings
        self.serverTransactions = []
        self.applicationTimeout = device.apduTimeout        # how long the application has to respond

    def GetNextInvokeID(self):
        """Called by clients to get an unused invoke ID."""
        if _debug:
            print "StateMachineAccessPoint.GetNextInvokeID"
            
        initialID = self.nextInvokeID
        while 1:
            invokeID = self.nextInvokeID
            self.nextInvokeID = (self.nextInvokeID + 1) % 256

            # see if we've checked for them all
            if initialID == self.nextInvokeID:
                raise RuntimeError, "no available invoke ID"

            for tr in self.clientTransactions:
                if invokeID == tr.invokeID:
                    break
            else:
                break

        return invokeID

    def GetDeviceInfo(self, addr):
        """Get the segmentation supported and max APDU length accepted for a device."""
        if _debug:
            print "StateMachineAccessPoint.GetDeviceInfo", addr
    
        # return a generic info object
        return DeviceInfo(addr)
    
    def Confirmation(self, pdu):
        """Packets coming up the stack are APDU's."""
        if _debug:
            print "StateMachineAccessPoint.Confirmation"
            print "-pdu-"
            pdu.DebugContents()

        # make a more focused interpretation
        atype = APDUTypes.get(pdu.apduType)
        if not atype:
            if _debug:
                print "    - unknown apduType:", pdu.apduType
            ### log this
            return
            
        # decode it
        apdu = atype()
        apdu.Decode(pdu)
        if _debug:
            print "-apdu-"
            apdu.DebugContents()
        
        if isinstance(apdu, ConfirmedRequestPDU):
            if _debug:
                print "    - confirmed request"

            # find duplicates of this request
            for tr in self.serverTransactions:
                if _debug:
                    print "        -", tr, tr.remoteDevice.address, tr.invokeID
                if (apdu.pduSource == tr.remoteDevice.address) and (apdu.apduInvokeID == tr.invokeID):
                    break
            else:
                # build a server transaction
                tr = ServerSSM(self)

                # add it to our transactions to track it
                self.serverTransactions.append(tr)

            # let it run with the apdu
            tr.Indication(apdu)

        elif isinstance(apdu, UnconfirmedRequestPDU):
            if _debug:
                print "    - unconfirmed request"

            # deliver directly to the application
            self.SAPRequest(apdu)

        elif isinstance(apdu, SimpleAckPDU) \
            or isinstance(apdu, ComplexAckPDU) \
            or isinstance(apdu, ErrorPDU) \
            or isinstance(apdu, RejectPDU):
            if _debug:
                print "    - ack/error/reject"

            if _debug:
                print "        - matching (client)", apdu.pduSource, apdu.apduInvokeID
            # find the client transaction this is acking
            for tr in self.clientTransactions:
                if _debug:
                    print "        -", tr, tr.remoteDevice.address, tr.invokeID
                if (apdu.apduInvokeID == tr.invokeID):
                    if not (apdu.pduSource == tr.remoteDevice.address):
                        if _debug:
                            print "    - warning, %s != %s" % (apdu.pduSource, tr.remoteDevice.address)
                    break
            else:
                if _debug:
                    print "    - no matching client transaction"
                return

            # send the packet on to the transaction
            tr.Confirmation(apdu)

        elif isinstance(apdu, AbortPDU):
            if _debug:
                print "    - abort"

            # find the transaction being aborted
            if apdu.apduSrv:
                if _debug:
                    print "        - matching (client)", apdu.pduSource, apdu.apduInvokeID
                for tr in self.clientTransactions:
                    if _debug:
                        print "        -", tr, tr.remoteDevice.address, tr.invokeID
                    if (apdu.apduInvokeID == tr.invokeID):
                        if not(apdu.pduSource == tr.remoteDevice.address):
                            if _debug:
                                print "    - warning, %s != %s" % (apdu.pduSource, tr.remoteDevice.address)
                        break
                else:
                    if _debug:
                        print "    - no matching client transaction"
                    return

                # send the packet on to the transaction
                tr.Confirmation(apdu)
            else:
                if _debug:
                    print "        - matching (server)", apdu.pduSource, apdu.apduInvokeID
                for tr in self.serverTransactions:
                    if _debug:
                        print "        -", tr, tr.remoteDevice.address, tr.invokeID
                    if (apdu.pduSource == tr.remoteDevice.address) and (apdu.apduInvokeID == tr.invokeID):
                        break
                else:
                    if _debug:
                        print "    - no matching server transaction (1)"
                        print self.serverTransactions
                    return

                # send the packet on to the transaction
                tr.Indication(apdu)

        elif isinstance(apdu, SegmentAckPDU):
            if _debug:
                print "    - segment ack"

            # find the transaction being aborted
            if apdu.apduSrv:
                if _debug:
                    print "        - matching (client)", apdu.pduSource, apdu.apduInvokeID
                for tr in self.clientTransactions:
                    if _debug:
                        print "        -", tr, tr.remoteDevice.address, tr.invokeID
                    if (apdu.apduInvokeID == tr.invokeID):
                        if not(apdu.pduSource == tr.remoteDevice.address):
                            if _debug:
                                print "    - warning, %s != %s" % (apdu.pduSource, tr.remoteDevice.address)
                        break
                else:
                    if _debug:
                        print "    - no matching client transaction"
                    return

                # send the packet on to the transaction
                tr.Confirmation(apdu)
            else:
                if _debug:
                    print "        - matching (server)", apdu.pduSource, apdu.apduInvokeID
                for tr in self.serverTransactions:
                    if _debug:
                        print "        -", tr, tr.remoteDevice.address, tr.invokeID
                    if (apdu.pduSource == tr.remoteDevice.address) and (apdu.apduInvokeID == tr.invokeID):
                        break
                else:
                    if _debug:
                        print "    - no matching server transaction (2)"
                        print self.serverTransactions
                    return

                # send the packet on to the transaction
                tr.Indication(apdu)

        else:
            raise RuntimeError, "invalid APDU (8)"

    def SAPIndication(self, apdu):
        """This function is called when the application is requesting
        a new transaction as a client."""
        if _debug:
            print "StateMachineAccessPoint.SAPIndication"
            print "-apdu-"
            apdu.DebugContents()

        if isinstance(apdu, UnconfirmedRequestPDU):
            if _debug:
                print "    - unconfirmed request"

            # deliver to the device
            self.Request(apdu)

        elif isinstance(apdu, ConfirmedRequestPDU):
            if _debug:
                print "    - confirmed request"

            # make sure it has an invoke ID
            if apdu.apduInvokeID is None:
                apdu.apduInvokeID = self.GetNextInvokeID()
            else:
                # verify the invoke ID isn't already being used
                for tr in self.clientTransactions:
                    if apdu.apduInvokeID == tr.invokeID:
                        raise RuntimeError, "invoke ID in use"

            # warning for bogus requests
            if (apdu.pduDestination.addrType != Address.localStationAddr) and (apdu.pduDestination.addrType != Address.remoteStationAddr):
                if _debug:
                    print "    - warning, %s is not a local or remote station" % (apdu.pduDestination,)

            # create a client transaction state machine
            tr = ClientSSM(self)

            # add it to our transactions to track it
            self.clientTransactions.append(tr)

            # let it run
            tr.Indication(apdu)

        else:
            print "StateMachineAccessPoint.SAPIndication"
            print "-apdu-"
            apdu.DebugContents()
            traceback.print_exc(file=sys.stdout)
            raise RuntimeError, "invalid APDU (9)"

    def SAPConfirmation(self, apdu):
        """This function is called when the application is responding
        to a request, the apdu may be a simple ack, complex ack, error, reject or abort."""
        if _debug:
            print "StateMachineAccessPoint.SAPConfirmation"
            print "-apdu-"
            apdu.DebugContents()

        if isinstance(apdu, SimpleAckPDU) \
            or isinstance(apdu, ComplexAckPDU) \
            or isinstance(apdu, ErrorPDU) \
            or isinstance(apdu, RejectPDU) \
            or isinstance(apdu, AbortPDU):
            # find the appropriate server transaction
            if _debug:
                print "        - matching", apdu.pduDestination, apdu.apduInvokeID
            for tr in self.serverTransactions:
                if _debug:
                    print "        -", tr, tr.remoteDevice.address, tr.invokeID
                if (apdu.pduDestination == tr.remoteDevice.address) and (apdu.apduInvokeID == tr.invokeID):
                    break
            else:
                if _debug:
                    print "    - no matching server transaction (3)"
                    print self.serverTransactions
                return

            # pass control to the transaction
            tr.Confirmation(apdu)

        else:
            print "StateMachineAccessPoint.SAPConfirmation"
            print "-apdu-"
            apdu.DebugContents()
            traceback.print_exc(file=sys.stdout)
            raise RuntimeError, "invalid APDU (10)"

#
#   ApplicationServiceAccessPoint 
#

class ApplicationServiceAccessPoint(ApplicationServiceElement, ServiceAccessPoint):

    def __init__(self, aseID=None, sapID=None):
        ApplicationServiceElement.__init__(self, aseID)
        ServiceAccessPoint.__init__(self, sapID)

    def Indication(self, apdu):
        if _debug:
            print "ApplicationServiceAccessPoint.Indication"
            apdu.DebugContents()
            
        if isinstance(apdu, ConfirmedRequestPDU):
            atype = ConfirmedRequestTypes.get(apdu.apduService)
            if not atype:
                if _debug:
                    print "    - no confirmed request decoder"
                return
                
            try:
                xpdu = atype()
                xpdu.Decode(apdu)
            except Exception, e:
                print "Confirmed Request Decoding Error:", e
                print "    - atype:", atype
                apdu.DebugContents()
                print
                return
            
        elif isinstance(apdu, UnconfirmedRequestPDU):
            atype = UnconfirmedRequestTypes.get(apdu.apduService)
            if not atype:
                if _debug:
                    print "    - no unconfirmed request decoder"
                return
                
            try:
                xpdu = atype()
                xpdu.Decode(apdu)
            except Exception, e:
                print "Unconfirmed Request Decoding Error:", e
                print "    - atype:", atype
                apdu.DebugContents()
                print
                return
                
        else:
            if _debug:
                print "    - invalid APDU, should be a confirmed or unconfirmed request"
            return
        
        # forward the decoded packet
        self.SAPRequest(xpdu)
        
    def SAPIndication(self, apdu):
        if _debug:
            print "ApplicationServiceAccessPoint.SAPIndication"
            apdu.DebugContents()
        
        if isinstance(apdu, ConfirmedRequestPDU):
            try:
                xpdu = ConfirmedRequestPDU()
                apdu.Encode(xpdu)
            except Exception, e:
                print "Confirmed Request Encoding Error:", e
                apdu.DebugContents()
                print
                return
            
        elif isinstance(apdu, UnconfirmedRequestPDU):
            try:
                xpdu = UnconfirmedRequestPDU()
                apdu.Encode(xpdu)
            except:
                print "Unconfirmed Request Encoding Error:", e
                apdu.DebugContents()
                print
                return
                
        else:
            if _debug:
                print "    - invalid APDU, should be a confirmed or unconfirmed request"
            return
        
        # forward the encoded packet
        self.Request(xpdu)
        
    def Confirmation(self, apdu):
        if _debug:
            print "ApplicationServiceAccessPoint.Confirmation"
            apdu.DebugContents()
        
        if isinstance(apdu, SimpleAckPDU):
            xpdu = apdu
            
        elif isinstance(apdu, ComplexAckPDU):
            atype = ComplexAckTypes.get(apdu.apduService)
            if not atype:
                if _debug:
                    print "    - no decoder"
                return
                
            xpdu = atype()
            xpdu.Decode(apdu)
                
        elif isinstance(apdu, ErrorPDU):
            atype = ErrorTypes.get(apdu.apduService)
            if not atype:
                if _debug:
                    print "    - no decoder"
                return
                
            xpdu = atype()
            xpdu.Decode(apdu)
                
        elif isinstance(apdu, RejectPDU):
            xpdu = apdu
            
        elif isinstance(apdu, AbortPDU):
            xpdu = apdu
            
        else:
            if _debug:
                print "    - invalid APDU, should be a simple ack, complex ack, error, reject, or abort"
            return
        
        # forward the decoded packet
        self.SAPResponse(xpdu)

    def SAPConfirmation(self, apdu):
        if _debug:
            print "ApplicationServiceAccessPoint.SAPConfirmation"
            apdu.DebugContents()
        
        if isinstance(apdu, SimpleAckPDU):
            xpdu = apdu
            
        elif isinstance(apdu, ComplexAckPDU):
            xpdu = ComplexAckPDU()
            apdu.Encode(xpdu)
                
        elif isinstance(apdu, ErrorPDU):
            xpdu = ErrorPDU()
            apdu.Encode(xpdu)
                
        elif isinstance(apdu, RejectPDU):
            xpdu = apdu
            
        elif isinstance(apdu, AbortPDU):
            xpdu = apdu
            
        else:
            if _debug:
                print "    - invalid APDU, should be a simple ack, complex ack, error, reject, or abort"
            return
        
        # forward the encoded packet
        self.Response(xpdu)
        
#
#   DebugApplicationServiceAccessPoint 
#

class DebugApplicationServiceAccessPoint(ApplicationServiceElement, ServiceAccessPoint):

    def __init__(self, aseID=None, sapID=None):
        ApplicationServiceElement.__init__(self, aseID)
        ServiceAccessPoint.__init__(self, sapID)

    def Indication(self, apdu):
        print "-" * 20, "DebugApplicationServiceAccessPoint.Indication", "-" * 20
        apdu.DebugContents()
        print
        
        # chain this along
        self.SAPRequest(apdu)
        
    def SAPIndication(self, apdu):
        print "-" * 20, "DebugApplicationServiceAccessPoint.SAPIndication", "-" * 20
        apdu.DebugContents()
        print
        
        # chain this along
        self.Request(apdu)
        
    def Confirmation(self, apdu):
        print "-" * 20, "DebugApplicationServiceAccessPoint.Confirmation", "-" * 20
        apdu.DebugContents()
        print
        
        # chain this along
        self.SAPResponse(apdu)
        
    def SAPConfirmation(self, apdu):
        print "-" * 20, "DebugApplicationServiceAccessPoint.SAPConfirmation", "-" * 20
        apdu.DebugContents()
        print
        
        # chain this along
        self.Response(apdu)
