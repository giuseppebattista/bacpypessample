#!/usr/bin/python

"""
BACpypes_013.py
"""

import sys
import logging

from BACpypes.Debugging import Logging
from BACpypes.CommandLogging import ConsoleLogHandler
from BACpypes.ConsoleCommunications import ConsoleCmd

from BACpypes.Core import run
from BACpypes.CommunicationsCore import Bind, Debug
from BACpypes.BVLL import AnnexJCodec, UDPMultiplexer

from BACpypes.PDU import Address, PDU
from BACpypes.Application import ApplicationServiceAccessPoint, Application
from BACpypes.ApplicationService import StateMachineAccessPoint
from BACpypes.NetworkService import NetworkServiceAccessPoint, NetworkServiceElement
from BACpypes.Object import LocalDeviceObject
from BACpypes.VLAN import VLAN, VLANNode
from BACpypes.BVLL import BIPSimple, AnnexJCodec, UDPMultiplexer

# some debugging
_log = logging.getLogger(__name__)

#
#   GatewayDevice
#

class GatewayDevice(Application, Logging):

    def __init__(self, deviceName, deviceIdentifier, deviceAddress, aseID=None):
        GatewayDevice._debug("__init__ %r %r %r aseID=%r", deviceName,
            deviceIdentifier, deviceAddress, aseID)

        # create an instance of a LocalDeviceObject
        localDevice = LocalDeviceObject(objectName=deviceName
            , objectIdentifier=deviceIdentifier
            , vendorIdentifier=15
            )
        GatewayDevice._debug("    - localDevice: %r", localDevice)

        # make a BACnet address out of the parameter
        localAddress = Address(deviceAddress)
        GatewayDevice._debug("    - localAddress: %r", localAddress)

        # now the application 
        Application.__init__(self, localDevice, localAddress, aseID)

        # include a application decoder
        self.asap = ApplicationServiceAccessPoint()

        # pass the device object to the state machine access point so it
        # can know if it should support segmentation
        self.smap = StateMachineAccessPoint(localDevice)

        # a network service access point will be needed
        self.nsap = NetworkServiceAccessPoint()

        # give the NSAP a generic network layer service element
        self.nse = NetworkServiceElement()
        Bind(self.nse, self.nsap)

        # bind the top layers
        Bind(self, self.asap, self.smap, self.nsap)

        # create a node to be connected to a VLAN
        self.node = VLANNode(localAddress)

        # bind the NSAP to the stack, no network number
        self.nsap.Bind(self.node)

#
#   __main__
#

try:
    if ('--buggers' in sys.argv):
        loggers = logging.Logger.manager.loggerDict.keys()
        loggers.sort()
        for loggerName in loggers:
            sys.stdout.write(loggerName + '\n')
        sys.exit(0)

    if ('--debug' in sys.argv):
        indx = sys.argv.index('--debug')
        for i in range(indx+1, len(sys.argv)):
            ConsoleLogHandler(sys.argv[i])
        del sys.argv[indx:]

    _log.debug("initialization")
    
    # create a VLAN
    vlan = VLAN()

    # create a GatewayDevice object and add its node to the vlan
    dev10 = GatewayDevice('Sample-10', 810, 10)
    vlan.AddNode(dev10.node)

    # do another one
    dev11 = GatewayDevice('Sample-11', 811, 11)
    vlan.AddNode(dev11.node)

    # a network service access point will be needed to act as a router
    nsap = NetworkServiceAccessPoint()

    # give the NSAP a generic network layer service element
    Bind(NetworkServiceElement(), nsap)

    # this is our local IP address
    localAddress = Address("128.253.109.54/24")

    # create a generic BIP stack, bound to the Annex J server 
    # on the UDP multiplexer
    bip = BIPSimple()
    annexj = AnnexJCodec()
    mux = UDPMultiplexer(localAddress)

    # bind the bottom layers
    Bind(bip, annexj, mux.annexJ)

    # bind the NSAP to the stack, network 5
    nsap.Bind(bip, 5, localAddress)

    # create a node to be connected to the vlan
    node = VLANNode(Address(1))
    vlan.AddNode(node)

    # now connect the NSAP to the VLAN, it will be the router between 5 and 8
    nsap.Bind(node, 8)

    _log.debug("running")

    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")
