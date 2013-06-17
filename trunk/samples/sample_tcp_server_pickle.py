#!/usr/bin/python

"""
sample_tcp_server_pickle

Rather than just using plain text messages, pickle arbitrary Python objects.
"""

import sys
import logging

from bacpypes.debugging import Logging, ModuleLogger
from bacpypes.consolelogging import ConsoleLogHandler

from bacpypes.core import run
from bacpypes.comm import PDU, Client, bind, ApplicationServiceElement
from bacpypes.tcp import TCPServerDirector, TCPPickleServerActor

# some debugging
_debug = 0
_log = ModuleLogger(globals())

# globals
server_addr = ('127.0.0.1', 9000)

#
#   EchoMaster
#

class EchoMaster(Client, Logging):

    def confirmation(self, pdu):
        if _debug: EchoMaster._debug('confirmation %r', pdu)

        self.request(PDU(pdu.pduData, destination=pdu.pduSource))

#
#   ConnectionASE
#

class ConnectionASE(ApplicationServiceElement, Logging):

    def indication(self, *args, **kwargs):
        if _debug: ConnectionASE._debug('indication %r %r', args, kwargs)

        if 'addPeer' in kwargs:
            if _debug: ConnectionASE._info("    - add peer %s", kwargs['addPeer'])

        if 'delPeer' in kwargs:
            if _debug: ConnectionASE._info("    - delete peer %s", kwargs['delPeer'])

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
        i = indx + 1
        while (i < len(sys.argv)) and (not sys.argv[i].startswith('--')):
            ConsoleLogHandler(sys.argv[i])
            i += 1
        del sys.argv[indx:i]

    _log.debug("initialization")

    director = TCPServerDirector(server_addr, actorClass=TCPPickleServerActor)
    echo_master = EchoMaster()
    bind(echo_master, director)
    bind(ConnectionASE(), director)

    _log.debug("running")

    run()

except Exception, e:
    _log.exception("an error has occurred: %s", e)
finally:
    _log.debug("finally")
