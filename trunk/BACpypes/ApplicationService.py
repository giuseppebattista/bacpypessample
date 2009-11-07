#!/bin/python

"""
Application Layer
"""

from time import time as _time
import logging

from Exceptions import *
from Debugging import DebugContents, Logging

from CommunicationsCore import Client, ServiceAccessPoint, ApplicationServiceElement
from Task import OneShotTask

from APDU import *

# some debuging
_log = logging.getLogger(__name__)

#
#   DeviceInfo
#

class DeviceInfo(DebugContents):

    _debugContents = ('address', 'segmentationSupported'
        , 'maxApduLengthAccepted', 'maxSegmentsAccepted'
        )
    
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

class SSM(OneShotTask, DebugContents, Logging):

    transactionLabels = ['IDLE'
        , 'SEGMENTED_REQUEST', 'AWAIT_CONFIRMATION', 'AWAIT_RESPONSE'
        , 'SEGMENTED_RESPONSE', 'SEGMENTED_CONFIRMATION', 'COMPLETED', 'ABORTED'
        ]

    _debugContents = ('ssmSAP', 'remoteDevice', 'invokeID'
        , 'state', 'segmentAPDU', 'segmentSize', 'segmentCount', 'maxSegmentsAccepted'
        , 'retryCount', 'segmentRetryCount', 'sentAllSegments', 'lastSequenceNumber'
        , 'initialSequenceNumber', 'actualWindowSize', 'proposedWindowSize'
        )
        
    def __init__(self, sap):
        """Common parts for client and server segmentation."""
        SSM._debug("__init__ %r", sap)
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
        SSM._debug("StartTimer %r", msecs)

        # if this is active, pull it
        if self.isScheduled:
            self.SuspendTask()

        # now install this
        self.InstallTask(_time() + (msecs / 1000.0))

    def StopTimer(self):
        SSM._debug("StopTimer")

        self.SuspendTask()

    def RestartTimer(self, msecs):
        SSM._debug("RestartTimer %r", msecs)

        # if this is active, pull it
        if self.isScheduled:
            self.SuspendTask()

        # now install this
        self.InstallTask(_time() + (msecs / 1000.0))

    def SetState(self, newState, timer=0):
        """This function is called when the derived class wants to change state."""
        SSM._debug("SetState %r (%s) timer=%r", newState, SSM.transactionLabels[newState], timer)

        # make sure we have a correct transition
        if (self.state == COMPLETED) or (self.state == ABORTED):
            e = RuntimeError("invalid state transition from %s to %s" % (SSM.transactionLabels[self.state], SSM.transactionLabels[newState]))
            SSM._exception(e)
            raise e

        # stop any current timer
        self.StopTimer()

        # make the change
        self.state = newState

        # if another timer should be started, start it
        if timer:
            self.StartTimer(timer)

    def SetSegmentationContext(self, apdu):
        """This function is called to set the segmentation context."""
        SSM._debug("SetSegmentationContext %s", repr(apdu))

        # set the context
        self.segmentAPDU = apdu

    def GetSegment(self, indx):
        """This function returns an APDU coorisponding to a particular
        segment of a confirmed request or complex ack.  The segmentAPDU
        is the context."""
        SSM._debug("GetSegment %r", indx)

        # check for no context
        if not self.segmentAPDU:
            raise RuntimeError, "no segmentation context established"

        # check for invalid segment number
        if indx >= self.segmentCount:
            raise RuntimeError, "invalid segment number %d, APDU has %d segments" % (indx, self.segmentCount)

        if self.segmentAPDU.apduType == ConfirmedRequestPDU.pduType:
            SSM._debug("    - confirmed request context")

            segAPDU = ConfirmedRequestPDU(self.segmentAPDU.apduService)

            segAPDU.apduMaxSegs = self.maxSegmentsAccepted
            segAPDU.apduMaxResp = self.ssmSAP.maxApduLengthAccepted
            segAPDU.apduInvokeID = self.invokeID;

            # segmented response accepted?
            segAPDU.apduSA = ((self.ssmSAP.segmentationSupported == 'segmented-both') \
                    or (self.ssmSAP.segmentationSupported == 'segmented-receive'))
            SSM._debug("    - segmented response accepted: %r", segAPDU.apduSA)
            SSM._debug("        - self.ssmSAP.segmentationSupported: %r", self.ssmSAP.segmentationSupported)

        elif self.segmentAPDU.apduType == ComplexAckPDU.pduType:
            SSM._debug("    - complex ack context")

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

        # success
        return segAPDU

    def AppendSegment(self, apdu):
        """This function appends the apdu content to the end of the current
        APDU being built.  The segmentAPDU is the context."""
        SSM._debug("AppendSegment %r", apdu)

        # check for no context
        if not self.segmentAPDU:
            raise RuntimeError, "no segmentation context established"

        # append the data
        self.segmentAPDU.PutData(apdu.pduData)

    def InWindow(self, seqA, seqB):
        SSM._debug("InWindow %r %r", seqA, seqB)

        rslt = ((seqA - seqB + 256) % 256) < self.actualWindowSize
        SSM._debug("    - rslt: %r", rslt)

        return rslt

    def FillWindow(self, seqNum):
        """This function sends all of the packets necessary to fill
        out the segmentation window."""
        SSM._debug("FillWindow %r", seqNum)

        for ix in range(self.actualWindowSize):
            apdu = self.GetSegment(seqNum + ix)

            # send the message
            self.ssmSAP.Request(apdu)

            # check for no more follows
            if not apdu.apduMor:
                self.sentAllSegments = True
                break

#
#   ClientSSM - Client Segmentation State Machine
#

class ClientSSM(SSM, Logging):

    def __init__(self, sap):
        SSM.__init__(self, sap)
        
        # initialize the retry count
        self.retryCount = 0

    def SetState(self, newState, timer=0):
        """This function is called when the client wants to change state."""
        ClientSSM._debug("SetState %r (%s) timer=%r", newState, SSM.transactionLabels[newState], timer)

        # pass the change down
        SSM.SetState(self, newState, timer)

        # completed or aborted, remove tracking
        if (newState == COMPLETED) or (newState == ABORTED):
            self.ssmSAP.clientTransactions.remove(self)

    def Request(self, apdu):
        """This function is called by client transaction functions when it wants
        to send a message to the device."""
        ClientSSM._debug("Request %r", apdu)

        # make sure it has a good source and destination
        apdu.pduSource = None
        apdu.pduDestination = self.remoteDevice.address

        # send it via the device
        self.ssmSAP.Request(apdu)

    def Indication(self, apdu):
        """This function is called after the device has bound a new transaction
        and wants to start the process rolling."""
        ClientSSM._debug("Indication %r", apdu)

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
        ClientSSM._debug("    - invoke ID: %r", self.invokeID)

        # get information about the device
        self.remoteDevice = self.ssmSAP.GetDeviceInfo(apdu.pduDestination)

        # the segment size is the minimum of what I want to transmit and
        # what the device can receive
        self.segmentSize = min(self.ssmSAP.maxApduLengthAccepted, self.remoteDevice.maxApduLengthAccepted)
        ClientSSM._debug("    - segment size: %r", self.segmentSize)

        # compute the segment count ### minus the header?
        self.segmentCount, more = divmod(len(apdu.pduData), self.segmentSize)
        if more:
            self.segmentCount += 1
        ClientSSM._debug("    - segment count: %r", self.segmentCount)

        # make sure we support segmented transmit if we need to
        if self.segmentCount > 1:
            if (self.ssmSAP.segmentationSupported != 'segmented-transmit') and (self.ssmSAP.segmentationSupported != 'segmented-both'):
                ClientSSM._debug("    - local device can't send segmented messages")
                abort = self.Abort(BACnetAbortReason.SEGMENTATIONNOTSUPPORTED)
                self.Response(abort)
                return
            if (self.remoteDevice.segmentationSupported != 'segmented-receive') and (self.remoteDevice.segmentationSupported != 'segmented-both'):
                ClientSSM._debug("    - remote device can't receive segmented messages")
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
        ClientSSM._debug("Response %r", apdu)

        # make sure it has a good source and destination
        apdu.pduSource = self.remoteDevice.address
        apdu.pduDestination = None

        # send it to the application
        self.ssmSAP.SAPResponse(apdu)

    def Confirmation(self, apdu):
        """This function is called by the device for all upstream messages related
        to the transaction."""
        ClientSSM._debug("Confirmation %r", apdu)

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
        ClientSSM._debug("ProcessTask")

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
            e = RuntimeError("invalid state")
            ClientSSM._exception("exception: %r", e)
            raise e
            
    def Abort(self, reason):
        """This function is called when the transaction should be aborted."""
        ClientSSM._debug("Abort %r", reason)

        # change the state to aborted
        self.SetState(ABORTED)

        # return an abort APDU
        return AbortPDU(False, self.invokeID, reason)

    def SegmentedRequest(self, apdu):
        """This function is called when the client is sending a segmented request
        and receives an apdu."""
        ClientSSM._debug("SegmentedRequest %r", apdu)

        # client is ready for the next segment
        if apdu.apduType == SegmentAckPDU.pduType:
            ClientSSM._debug("    - segment ack")

            # duplicate ack received?
            if not self.InWindow(apdu.apduSeq, self.initialSequenceNumber):
                ClientSSM._debug("    - not in window")
                self.RestartTimer(self.ssmSAP.segmentTimeout)

            # final ack received?
            elif self.sentAllSegments:
                ClientSSM._debug("    - all done sending request")
                self.SetState(AWAIT_CONFIRMATION, self.ssmSAP.retryTimeout)

            # more segments to send
            else:
                ClientSSM._debug("    - more segments to send")

                self.initialSequenceNumber = (apdu.apduSeq + 1) % 256
                self.actualWindowSize = apdu.apduWin
                self.segmentRetryCount = 0
                self.FillWindow(self.initialSequenceNumber)
                self.RestartTimer(self.ssmSAP.segmentTimeout)

        # simple ack
        elif (apdu.apduType == SimpleAckPDU.pduType):
            ClientSSM._debug("    - simple ack")

            if not self.sentAllSegments:
                abort = self.Abort(BACnetAbortReason.INVALIDAPDUINTHISSTATE)
                self.Request(abort)     # send it to the device
                self.Response(abort)    # send it to the application
            else:
                self.SetState(COMPLETED)
                self.Response(apdu)

        elif (apdu.apduType == ComplexAckPDU.pduType):
            ClientSSM._debug("    - complex ack")

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
            ClientSSM._debug("    - error/reject/abort")

            self.SetState(COMPLETED)
            self.response = apdu
            self.Response(apdu)

        else:
            raise RuntimeError, "invalid APDU (2)"

    def SegmentedRequestTimeout(self):
        ClientSSM._debug("SegmentedRequestTimeout")

        # try again
        if self.segmentRetryCount < self.ssmSAP.retryCount:
            ClientSSM._debug("    - retry segmented request")

            self.segmentRetryCount += 1
            self.StartTimer(self.ssmSAP.segmentTimeout)
            self.FillWindow(self.initialSequenceNumber)
        else:
            ClientSSM._debug("    - abort, no response from the device")

            abort = self.Abort(BACnetAbortReason.NORESPONSE)
            self.Response(abort)

    def AwaitConfirmation(self, apdu):
        ClientSSM._debug("AwaitConfirmation %r", apdu)

        if (apdu.apduType == AbortPDU.pduType):
            ClientSSM._debug("    - server aborted")

            self.SetState(ABORTED)
            self.Response(apdu)

        elif (apdu.apduType == SimpleAckPDU.pduType) or (apdu.apduType == ErrorPDU.pduType) or (apdu.apduType == RejectPDU.pduType):
            ClientSSM._debug("    - simple ack, error, or reject")

            self.SetState(COMPLETED)
            self.Response(apdu)

        elif (apdu.apduType == ComplexAckPDU.pduType):
            ClientSSM._debug("    - complex ack")

            # if the response is not segmented, we're done
            if not apdu.apduSeg:
                ClientSSM._debug("    - unsegmented")

                self.SetState(COMPLETED)
                self.Response(apdu)

            elif (self.ssmSAP.segmentationSupported != 'segmented-receive') and (self.ssmSAP.segmentationSupported != 'segmented-both'):
                ClientSSM._debug("    - local device can't receive segmented messages")
                abort = self.Abort(BACnetAbortReason.SEGMENTATIONNOTSUPPORTED)
                self.Response(abort)

            elif apdu.apduSeq == 0:
                ClientSSM._debug("    - segmented response")

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
                ClientSSM._debug("    - invalid APDU in this state")

                abort = self.Abort(BACnetAbortReason.INVALIDAPDUINTHISSTATE)
                self.Request(abort) # send it to the device
                self.Response(abort) # send it to the application

        elif (apdu.apduType == SegmentAckPDU.pduType):
            ClientSSM._debug("    - segment ack(!?)")

            self.RestartTimer(self.ssmSAP.segmentTimeout)

        else:
            raise RuntimeError, "invalid APDU (3)"

    def AwaitConfirmationTimeout(self):
        ClientSSM._debug("AwaitConfirmationTimeout")

        self.retryCount += 1
        if self.retryCount < self.ssmSAP.retryCount:
            ClientSSM._debug("    - no response, try again (%d < %d)", self.retryCount, self.ssmSAP.retryCount)

            # save the retry count, Indication acts like the request is coming
            # from the application so the retryCount gets re-initialized.
            saveCount = self.retryCount
            self.Indication(self.segmentAPDU)
            self.retryCount = saveCount
        else:
            ClientSSM._debug("    - retry count exceeded")
            abort = self.Abort(BACnetAbortReason.NORESPONSE)
            self.Response(abort)

    def SegmentedConfirmation(self, apdu):
        ClientSSM._debug("SegmentedConfirmation %r", apdu)

        # the only messages we should be getting are complex acks
        if (apdu.apduType != ComplexAckPDU.pduType):
            ClientSSM._debug("    - complex ack required")

            abort = self.Abort(BACnetAbortReason.INVALIDAPDUINTHISSTATE)
            self.Request(abort) # send it to the device
            self.Response(abort) # send it to the application
            return

        # it must be segmented
        if not apdu.apduSeg:
            ClientSSM._debug("    - must be segmented")

            abort = self.Abort(BACnetAbortReason.INVALIDAPDUINTHISSTATE)
            self.Request(abort) # send it to the device
            self.Response(abort) # send it to the application
            return

        # proper segment number
        if apdu.apduSeq != (self.lastSequenceNumber + 1) % 256:
            ClientSSM._debug("    - segment %s received out of order, should be %s", apdu.apduSeq, (self.lastSequenceNumber + 1) % 256)

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
            ClientSSM._debug("    - no more follows")

            # send a final ack
            segack = SegmentAckPDU( 0, 0, self.invokeID, self.lastSequenceNumber, self.actualWindowSize )
            self.Request(segack)

            self.SetState(COMPLETED)
            self.Response(self.segmentAPDU)

        elif apdu.apduSeq == ((self.initialSequenceNumber + self.actualWindowSize) % 256):
            ClientSSM._debug("    - last segment in the group")

            self.initialSequenceNumber = self.lastSequenceNumber
            self.RestartTimer(self.ssmSAP.segmentTimeout)
            segack = SegmentAckPDU( 0, 0, self.invokeID, self.lastSequenceNumber, self.actualWindowSize )
            self.Request(segack)

        else:
            # wait for more segments
            ClientSSM._debug("    - wait for more segments")

            self.RestartTimer(self.ssmSAP.segmentTimeout)

    def SegmentedConfirmationTimeout(self):
        ClientSSM._debug("SegmentedConfirmationTimeout")

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
        ServerSSM._debug("SetState %r (%s) timer=%r", newState, SSM.transactionLabels[newState], timer)

        # pass the change down
        SSM.SetState(self, newState, timer)

        # completed or aborted, remove tracking
        if (newState == COMPLETED) or (newState == ABORTED):
            self.ssmSAP.serverTransactions.remove(self)

    def Request(self, apdu):
        """This function is called by transaction functions to send
        to the application."""
        ServerSSM._debug("Request %r", apdu)

        # make sure it has a good source and destination
        apdu.pduSource = self.remoteDevice.address
        apdu.pduDestination = None

        # send it via the device
        self.ssmSAP.SAPRequest(apdu)

    def Indication(self, apdu):
        """This function is called for each downstream packet related to
        the transaction."""
        ServerSSM._debug("Indication %r", apdu)

        if self.state == IDLE:
            self.Idle(apdu)
        elif self.state == SEGMENTED_REQUEST:
            self.SegmentedRequest(apdu)
        elif self.state == AWAIT_RESPONSE:
            self.AwaitResponse(apdu)
        elif self.state == SEGMENTED_RESPONSE:
            self.SegmentedResponse(apdu)
        else:
            ServerSSM._debug("    - invalid state")

    def Response(self, apdu):
        """This function is called by transaction functions when they want
        to send a message to the device."""
        ServerSSM._debug("Response %r", apdu)

        # make sure it has a good source and destination
        apdu.pduSource = None
        apdu.pduDestination = self.remoteDevice.address

        # send it via the device
        self.ssmSAP.Request(apdu)

    def Confirmation(self, apdu):
        """This function is called when the application has provided a response
        and needs it to be sent to the client."""
        ServerSSM._debug("Confirmation %r", apdu)

        if (apdu.apduType == AbortPDU.pduType):
            ServerSSM._debug("    - abort")

            self.SetState(ABORTED)

            # send the response to the device
            self.Response(apdu)
            return

        if self.state != AWAIT_RESPONSE:
            ServerSSM._debug("    - warning: not expecting a response")

        # simple response
        if (apdu.apduType == SimpleAckPDU.pduType) or (apdu.apduType == ErrorPDU.pduType) or (apdu.apduType == RejectPDU.pduType):
            ServerSSM._debug("    - simple ack, error, or reject")

            # transaction completed
            self.SetState(COMPLETED)

            # send the response to the device
            self.Response(apdu)
            return

        if (apdu.apduType == ComplexAckPDU.pduType):
            ServerSSM._debug("    - complex ack")

            # save the response and set the segmentation context
            self.SetSegmentationContext(apdu)

            # the segment size is the minimum of what I want to transmit and
            # what the device can receive
            self.segmentSize = min(self.ssmSAP.maxApduLengthAccepted, self.remoteDevice.maxApduLengthAccepted)
            ServerSSM._debug("    - segment size: %r", self.segmentSize)

            # compute the segment count ### minus the header?
            self.segmentCount, more = divmod(len(apdu.pduData), self.segmentSize)
            if more:
                self.segmentCount += 1
            ServerSSM._debug("    - segment count: %r", self.segmentCount)

            # make sure we support segmented transmit if we need to
            if self.segmentCount > 1:
                ServerSSM._debug("    - segmentation required, %d segemnts", self.segmentCount)

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
        ServerSSM._debug("ProcessTask")

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
            ServerSSM._debug("invalid state")
            raise RuntimeError, "invalid state"
            
    def Abort(self, reason):
        """This function is called when the application would like to abort the
        transaction.  There is no notification back to the application."""
        ServerSSM._debug("Abort %r", reason)

        # change the state to aborted
        self.SetState(ABORTED)

        # return an abort APDU
        return AbortPDU(True, self.invokeID, reason)

    def Idle(self, apdu):
        ServerSSM._debug("Idle %r", apdu)

        # make sure we're getting confirmed requests
        if not isinstance(apdu, ConfirmedRequestPDU):
            raise RuntimeError, "invalid APDU (5)"

        # save the invoke ID
        self.invokeID = apdu.apduInvokeID
        ServerSSM._debug("    - invoke ID: %r", self.invokeID)

        # get information about the device
        self.remoteDevice = self.ssmSAP.GetDeviceInfo(apdu.pduSource)

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
        ServerSSM._debug("    - segAck: %r", segack)

        self.Response(segack)

    def SegmentedRequest(self, apdu):
        ServerSSM._debug("SegmentedRequest %r", apdu)

        # some kind of problem
        if (apdu.apduType == AbortPDU.pduType):
            self.SetState(COMPLETED)
            self.Response(apdu)
            return

        # the only messages we should be getting are confirmed requests
        elif (apdu.apduType != ConfirmedRequestPDU.pduType):
            abort = self.Abort(BACnetAbortReason.INVALIDAPDUINTHISSTATE)
            self.Request(abort) # send it to the device
            self.Response(abort) # send it to the application
            return

        # it must be segmented
        elif not apdu.apduSeg:
            abort = self.Abort(BACnetAbortReason.INVALIDAPDUINTHISSTATE)
            self.Request(abort) # send it to the application
            self.Response(abort) # send it to the device
            return

        # proper segment number
        if apdu.apduSeq != (self.lastSequenceNumber + 1) % 256:
            ServerSSM._debug("    - segment %d received out of order, should be %d", apdu.apduSeq, (self.lastSequenceNumber + 1) % 256)

            # segment received out of order
            self.RestartTimer(self.ssmSAP.segmentTimeout)

            # send back a segment ack
            segack = SegmentAckPDU( 1, 1, self.invokeID, self.initialSequenceNumber, self.actualWindowSize )
                
            self.Response(segack)
            return

        # add the data
        self.AppendSegment(apdu)

        # update the sequence number
        self.lastSequenceNumber = (self.lastSequenceNumber + 1) % 256

        # last segment?
        if not apdu.apduMor:
            ServerSSM._debug("    - no more follows")

            # send back a final segment ack
            segack = SegmentAckPDU( 0, 1, self.invokeID, self.lastSequenceNumber, self.actualWindowSize )
            self.Response(segack)

            # forward the whole thing to the application
            self.SetState(AWAIT_RESPONSE, self.ssmSAP.applicationTimeout)
            self.Request(self.segmentAPDU)

        elif apdu.apduSeq == ((self.initialSequenceNumber + self.actualWindowSize) % 256):
                ServerSSM._debug("    - last segment in the group")

                self.initialSequenceNumber = self.lastSequenceNumber
                self.RestartTimer(self.ssmSAP.segmentTimeout)

                # send back a segment ack
                segack = SegmentAckPDU( 0, 1, self.invokeID, self.initialSequenceNumber, self.actualWindowSize )
                self.Response(segack)

        else:
            # wait for more segments
            ServerSSM._debug("    - wait for more segments")

            self.RestartTimer(self.ssmSAP.segmentTimeout)

    def SegmentedRequestTimeout(self):
        ServerSSM._debug("SegmentedRequestTimeout")

        # give up
        self.SetState(ABORTED)

    def AwaitResponse(self, apdu):
        ServerSSM._debug("AwaitResponse %r", apdu)

        if isinstance(apdu, ConfirmedRequestPDU):
            ServerSSM._debug("    - client is trying this request again")

        elif isinstance(apdu, AbortPDU):
            ServerSSM._debug("    - client aborting this request")

            # forward abort to the application
            self.SetState(ABORTED)
            self.Request(apdu)

        else:
            raise RuntimeError, "invalid APDU (6)"

    def AwaitResponseTimeout(self):
        """This function is called when the application has taken too long
        to respond to a clients request.  The client has probably long since
        given up."""
        ServerSSM._debug("AwaitResponseTimeout")

        abort = self.Abort(BACnetAbortReason.SERVERTIMEOUT)
        self.Request(abort)

    def SegmentedResponse(self, apdu):
        ServerSSM._debug("SegmentedResponse %r", apdu)

        # client is ready for the next segment
        if (apdu.apduType == SegmentAckPDU.pduType):
            ServerSSM._debug("    - segment ack")

            # duplicate ack received?
            if not self.InWindow(apdu.apduSeq, self.initialSequenceNumber):
                ServerSSM._debug("    - not in window")
                self.RestartTimer(self.ssmSAP.segmentTimeout)

            # final ack received?
            elif self.sentAllSegments:
                ServerSSM._debug("    - all done sending response")
                self.SetState(COMPLETED)

            else:
                ServerSSM._debug("    - more segments to send")

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
        ServerSSM._debug("SegmentedResponseTimeout")

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

class StateMachineAccessPoint(DeviceInfo, Client, ServiceAccessPoint, Logging):

    def __init__(self, device, sap=None, cid=None):
        StateMachineAccessPoint._debug("__init__ %r sap=%r cid=%r", device, sap, cid)
            
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
        StateMachineAccessPoint._debug("GetNextInvokeID")
            
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
        StateMachineAccessPoint._debug("GetDeviceInfo %r", addr)
    
        # return a generic info object
        return DeviceInfo(addr)
    
    def Confirmation(self, pdu):
        """Packets coming up the stack are APDU's."""
        StateMachineAccessPoint._debug("Confirmation %r", pdu)

        # make a more focused interpretation
        atype = APDUTypes.get(pdu.apduType)
        if not atype:
            StateMachineAccessPoint._warning("    - unknown apduType: %r", pdu.apduType)
            return
            
        # decode it
        apdu = atype()
        apdu.Decode(pdu)
        StateMachineAccessPoint._debug("    - apdu: %r", apdu)
        
        if isinstance(apdu, ConfirmedRequestPDU):
            # find duplicates of this request
            for tr in self.serverTransactions:
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
            # deliver directly to the application
            self.SAPRequest(apdu)

        elif isinstance(apdu, SimpleAckPDU) \
            or isinstance(apdu, ComplexAckPDU) \
            or isinstance(apdu, ErrorPDU) \
            or isinstance(apdu, RejectPDU):
                
            # find the client transaction this is acking
            for tr in self.clientTransactions:
                if (apdu.apduInvokeID == tr.invokeID):
                    if not (apdu.pduSource == tr.remoteDevice.address):
                        StateMachineAccessPoint._warning("%s != %s (ack/error/reject)", apdu.pduSource, tr.remoteDevice.address)
                    break
            else:
                return
    
            # send the packet on to the transaction
            tr.Confirmation(apdu)

        elif isinstance(apdu, AbortPDU):
            # find the transaction being aborted
            if apdu.apduSrv:
                for tr in self.clientTransactions:
                    if (apdu.apduInvokeID == tr.invokeID):
                        if not(apdu.pduSource == tr.remoteDevice.address):
                            StateMachineAccessPoint._warning("%s != %s (abort)", apdu.pduSource, tr.remoteDevice.address)
                        break
                else:
                    return

                # send the packet on to the transaction
                tr.Confirmation(apdu)
            else:
                for tr in self.serverTransactions:
                    if (apdu.pduSource == tr.remoteDevice.address) and (apdu.apduInvokeID == tr.invokeID):
                        break
                else:
                    return
    
                # send the packet on to the transaction
                tr.Indication(apdu)

        elif isinstance(apdu, SegmentAckPDU):
            # find the transaction being aborted
            if apdu.apduSrv:
                for tr in self.clientTransactions:
                    if (apdu.apduInvokeID == tr.invokeID):
                        if not(apdu.pduSource == tr.remoteDevice.address):
                            StateMachineAccessPoint._warning("%s != %s (segment ack)", apdu.pduSource, tr.remoteDevice.address)
                        break
                else:
                    return

                # send the packet on to the transaction
                tr.Confirmation(apdu)
            else:
                for tr in self.serverTransactions:
                    if (apdu.pduSource == tr.remoteDevice.address) and (apdu.apduInvokeID == tr.invokeID):
                        break
                else:
                    return

                # send the packet on to the transaction
                tr.Indication(apdu)

        else:
            raise RuntimeError, "invalid APDU (8)"
        
    def SAPIndication(self, apdu):
        """This function is called when the application is requesting
        a new transaction as a client."""
        StateMachineAccessPoint._debug("SAPIndication %r", apdu)

        if isinstance(apdu, UnconfirmedRequestPDU):
            # deliver to the device
            self.Request(apdu)

        elif isinstance(apdu, ConfirmedRequestPDU):
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
                StateMachineAccessPoint._warning("%s is not a local or remote station", apdu.pduDestination)

            # create a client transaction state machine
            tr = ClientSSM(self)

            # add it to our transactions to track it
            self.clientTransactions.append(tr)

            # let it run
            tr.Indication(apdu)

        else:
            raise RuntimeError, "invalid APDU (9)"
        
    def SAPConfirmation(self, apdu):
        """This function is called when the application is responding
        to a request, the apdu may be a simple ack, complex ack, error, reject or abort."""
        StateMachineAccessPoint._debug("SAPConfirmation %r", apdu)

        if isinstance(apdu, SimpleAckPDU) \
                or isinstance(apdu, ComplexAckPDU) \
                or isinstance(apdu, ErrorPDU) \
                or isinstance(apdu, RejectPDU) \
                or isinstance(apdu, AbortPDU):
            # find the appropriate server transaction
            for tr in self.serverTransactions:
                if (apdu.pduDestination == tr.remoteDevice.address) and (apdu.apduInvokeID == tr.invokeID):
                    break
            else:
                return

            # pass control to the transaction
            tr.Confirmation(apdu)

        else:
            raise RuntimeError, "invalid APDU (10)"
        
#
#   ApplicationServiceAccessPoint 
#

class ApplicationServiceAccessPoint(ApplicationServiceElement, ServiceAccessPoint):

    def __init__(self, aseID=None, sapID=None):
        ApplicationServiceElement.__init__(self, aseID)
        ServiceAccessPoint.__init__(self, sapID)

    def Indication(self, apdu):
        ApplicationServiceAccessPoint._debug("Indication %r", apdu)
            
        if isinstance(apdu, ConfirmedRequestPDU):
            atype = ConfirmedRequestTypes.get(apdu.apduService)
            if not atype:
                ApplicationServiceAccessPoint._debug("    - no confirmed request decoder")
                return
                
            try:
                xpdu = atype()
                xpdu.Decode(apdu)
            except Exception, e:
                ApplicationServiceAccessPoint._exception("confirmed request decoding error: %r", e)
                return
            
        elif isinstance(apdu, UnconfirmedRequestPDU):
            atype = UnconfirmedRequestTypes.get(apdu.apduService)
            if not atype:
                ApplicationServiceAccessPoint._debug("    - no unconfirmed request decoder")
                return
                
            try:
                xpdu = atype()
                xpdu.Decode(apdu)
            except Exception, e:
                ApplicationServiceAccessPoint._exception("unconfirmed request decoding error: %r", e)
                return
                
        else:
            return
        
        # forward the decoded packet
        self.SAPRequest(xpdu)
        
    def SAPIndication(self, apdu):
        ApplicationServiceAccessPoint._debug("SAPIndication %r", apdu)
        
        if isinstance(apdu, ConfirmedRequestPDU):
            try:
                xpdu = ConfirmedRequestPDU()
                apdu.Encode(xpdu)
            except Exception, e:
                ApplicationServiceAccessPoint._exception("confirmed request decoding error: %r", e)
                raise e
            
        elif isinstance(apdu, UnconfirmedRequestPDU):
            try:
                xpdu = UnconfirmedRequestPDU()
                apdu.Encode(xpdu)
            except:
                ApplicationServiceAccessPoint._exception("unconfirmed request decoding error: %r", e)
                raise e
                
        else:
            return
        
        # forward the encoded packet
        self.Request(xpdu)
        
    def Confirmation(self, apdu):
        ApplicationServiceAccessPoint._debug("Confirmation %r", apdu)
        
        if isinstance(apdu, SimpleAckPDU):
            xpdu = apdu
            
        elif isinstance(apdu, ComplexAckPDU):
            atype = ComplexAckTypes.get(apdu.apduService)
            if not atype:
                ApplicationServiceAccessPoint._debug("    - no complex ack decoder")
                return
                
            xpdu = atype()
            xpdu.Decode(apdu)
                
        elif isinstance(apdu, ErrorPDU):
            atype = ErrorTypes.get(apdu.apduService)
            if not atype:
                ApplicationServiceAccessPoint._debug("    - no error decoder")
                return
                
            xpdu = atype()
            try:
               xpdu.Decode(apdu)
            except:
               xpdu = Error(errorClass=0, errorCode=0)
               
        elif isinstance(apdu, RejectPDU):
            xpdu = apdu
            
        elif isinstance(apdu, AbortPDU):
            xpdu = apdu
            
        else:
            return
        
        # forward the decoded packet
        self.SAPResponse(xpdu)

    def SAPConfirmation(self, apdu):
        ApplicationServiceAccessPoint._debug("SAPConfirmation %r", apdu)
        
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
            return
        
        # forward the encoded packet
        self.Response(xpdu)

