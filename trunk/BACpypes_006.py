#!/usr/bin/python

"""
BACpypes_006.py
"""

import sys
import logging

from BACpypes.Debugging import Logging
from BACpypes.CommandLogging import ConsoleLogHandler
from BACpypes.ConsoleCommunications import ConsoleCmd

from BACpypes.Core import run
from BACpypes.CommunicationsCore import Debug

from BACpypes.VLAN import VLAN, VLANNode
from BACpypes.PDU import Address, PDU

# some debugging
_log = logging.getLogger(__name__)

#
#   A LAN with two nodes
#

lan = VLAN()

node1 = VLANNode(Address(1), lan, sid='node1')
debug1 = Debug(label='node1', cid='node1')

node2 = VLANNode(Address(2), lan, sid='node2')
debug2 = Debug(label='node2', cid='node2')

#
#   TestConsoleCmd
#

class TestConsoleCmd(ConsoleCmd, Logging):

    def default(self, line):
        """Called on an input line when the command prefix is not recognized."""
        TestConsoleCmd._debug("default %r", line)
        
        # get the address and data
        addr, data = line.split(' ', 1)
        addr = Address(addr)

        # simulate a downstream message on node1
        debug1.Indication(PDU(data, destination=addr))

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
    
    TestConsoleCmd()

    _log.debug("running")
    run()
except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")

