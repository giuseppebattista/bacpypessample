#!/usr/bin/python

"""
Console Logging
"""

import types
import logging

from debugging import LoggingFormatter, ModuleLogger

# some debugging
_debug = 0
_log = ModuleLogger(globals())

#
#   ConsoleLogHandler
#

def ConsoleLogHandler(loggerRef='', level=logging.DEBUG):
    """Add a stream handler to stderr with our custom formatter to a logger."""
    if isinstance(loggerRef, logging.Logger):
        pass

    elif isinstance(loggerRef, types.StringType):
        # check for root
        if not loggerRef:
            loggerRef = _log

        # check for a valid logger name
        elif loggerRef not in logging.Logger.manager.loggerDict:
            raise RuntimeError, "not a valid logger name: %r" % (loggerRef,)

        # get the logger
        loggerRef = logging.getLogger(loggerRef)

    else:
        raise RuntimeError, "not a valid logger reference: %r" % (loggerRef,)

    # see if this (or its parent) is a module level logger
    if hasattr(loggerRef, 'globs'):
        loggerRef.globs['_debug'] += 1
    elif hasattr(loggerRef.parent, 'globs'):
        loggerRef.parent.globs['_debug'] += 1

    # make a debug handler
    hdlr = logging.StreamHandler()
    hdlr.setLevel(level)

    # use our formatter
    hdlr.setFormatter(LoggingFormatter())

    # add it to the logger
    loggerRef.addHandler(hdlr)

    # make sure the logger has at least this level
    loggerRef.setLevel(level)
