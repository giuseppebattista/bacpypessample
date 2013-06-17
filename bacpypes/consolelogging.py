#!/usr/bin/python

"""
Console Logging
"""

import sys
import types
import logging
import argparse

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

#
#   ArgumentParser
#

class ArgumentParser(argparse.ArgumentParser):

    """
    ArgumentParser extends the one with the same name from the argparse module
    by adding the common command line arguments found in BACpypes applications.

        --buggers                       list the debugging logger names
        --debug [DBEUG [DEBUG ...]]     attach a console to loggers
        --ini INI                       provide a separate INI file
    """

    def __init__(self, **kwargs):
        """Follow normal initialization and add BACpypes arguments."""
        if _debug: ArgumentParser._debug("__init__")
        argparse.ArgumentParser.__init__(self, **kwargs)

        # add a way to get a list of the debugging hooks
        self.add_argument("--buggers",
            help="list the debugging logger names",
            action="store_true",
            )

        # add a way to attach debuggers
        self.add_argument('--debug', nargs='*',
            help="add console log handler to each debugging logger",
            )

        # add a way to read a configuration file
        self.add_argument('--ini',
            help="device object configuration file",
            default="BACpypes.ini",
            )

    def parse_args(self):
        """Parse the arguments as usual, then add default processing."""
        if _debug: ArgumentParser._debug("parse_args")

        # pass along to the parent class
        args = argparse.ArgumentParser.parse_args(self)

        # check to dump labels
        if args.buggers:
            loggers = logging.Logger.manager.loggerDict.keys()
            loggers.sort()
            for loggerName in loggers:
                sys.stdout.write(loggerName + '\n')
            sys.exit(0)

        # check for debug
        if args.debug is None:
            # --debug not specified
            bug_list = []
        elif not args.debug:
            # --debug, but no arguments
            bug_list = ["__main__"]
        else:
            # --debug with arguments
            bug_list = args.debug

        # attach any that are specified
        for debug_name in bug_list:
            ConsoleLogHandler(debug_name)

        # return what was parsed
        return args
