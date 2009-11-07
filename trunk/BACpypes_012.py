#!/usr/bin/python

"""
BACpypes_012.py
"""

import sys
import logging

from BACpypes.Debugging import Logging
from BACpypes.CommandLogging import ConsoleLogHandler

from BACpypes.Core import run
from BACpypes.CommunicationsCore import Bind

from BACpypes.BVLL import Address
from BACpypes.BVLL import UDPMultiplexer, AnnexJCodec, BIPBBMD
from BACpypes.NetworkService import NetworkServiceAccessPoint, NetworkServiceElement

# some debugging
_log = logging.getLogger(__name__)

#
#   TestBBMD
#

class TestBBMD(BIPBBMD, Logging):

    def __init__(self, addr):
        TestBBMD._debug("TestBBMD %r", addr)
        BIPBBMD.__init__(self, addr)

        # save the address
        self.address = addr

        # make the lower layers
        self.annexj = AnnexJCodec()
        self.mux = UDPMultiplexer(self.address)

        # bind the bottom layers
        Bind(self, self.annexj, self.mux.annexJ)

        # give this a generic network layer service access point and element
        self.nsap = NetworkServiceAccessPoint()
        self.nse = NetworkServiceElement()
        self.nsap.Bind(self)
        Bind(self.nse, self.nsap)

#
#   __main__
#

try:
    if ('--debug' in sys.argv):
        indx = sys.argv.index('--debug')
        for i in range(indx+1, len(sys.argv)):
            ConsoleLogHandler(sys.argv[i])
        del sys.argv[indx:]

    _log.debug("initialization")

    # make a simple application
    vlan1 = TestBBMD(Address("192.168.1.10/24"))
    vlan1.AddPeer(Address("192.168.0.11"))

    vlanTest = TestBBMD(Address("192.168.0.11/24"))
    vlanTest.AddPeer(Address("192.168.1.10"))

    _log.debug("running")
    run()
except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")

