#!/usr/bin/python

"""
Debugging
"""

import sys
import types
import logging

# set the level of the root logger
_root = logging.getLogger()
_root.setLevel(1)

# add a stream handler for warnings and up
hdlr = logging.StreamHandler()
if ('--debugDebugging' in sys.argv):
    hdlr.setLevel(logging.DEBUG)
else:
    hdlr.setLevel(logging.WARNING)
hdlr.setFormatter(logging.Formatter(logging.BASIC_FORMAT, None))
_root.addHandler(hdlr)
del hdlr

#
#   _str_to_hex
#

def _str_to_hex(x, sep=''):
    return sep.join(["%02X" % (ord(c),) for c in x])

#
#   ModuleLogger
#

def ModuleLogger(globs):
    """Create a module level logger."""
    # make sure that _debug is defined
    if not globs.has_key('_debug'):
        raise RuntimeError, "define _debug before creating a module logger"

    # create a logger to be assgined to _log
    logger = logging.getLogger(globs['__name__'])

    # put in a reference to the module globals
    logger.globs = globs

    return logger

#
#   Typical Use
#
#   Create a _debug variable in the module, then use the ModuleLogger function
#   to create a "module level" logger.  When a handler is added to this logger
#   or a child of this logger, the _debug variable will be incremented.
#

# some debugging
_debug = 0
_log = ModuleLogger(globals())

#
#   DebugContents
#

class DebugContents(object):

    def debug_contents(self, indent=1, file=sys.stdout, _ids=None):
        """Debug the contents of an object."""
        if _debug: _log.debug("DebugContents indent=%r file=%r _ids=%r", indent, file, _ids)

        klasses = list(self.__class__.__mro__)
        klasses.reverse()
        if _debug: _log.debug("    - klasses: %r", klasses)

        # loop through the classes and look for _debug_contents
        attrs = []
        cids = []
        ownFn = []
        for klass in klasses:
            if klass is DebugContents:
                continue

            if not issubclass(klass, DebugContents) and hasattr(klass, 'debug_contents'):
                for i, seenAlready in enumerate(ownFn):
                    if issubclass(klass, seenAlready):
                        del ownFn[i]
                        break
                ownFn.append(klass)
                continue

            # look for a tuple of attribute names
            if not hasattr(klass, '_debug_contents'):
                continue

            debugContents = klass._debug_contents
            if not isinstance(debugContents, types.TupleType):
                raise RuntimeError, "%s._debug_contents must be a tuple" % (klass.__name__,)

            # already seen it?
            if id(debugContents) in cids:
                continue
            cids.append(id(debugContents))

            for attr in debugContents:
                if attr not in attrs:
                    attrs.append(attr)

        # a bit of debugging
        if _debug:
            _log.debug("    - attrs: %r", attrs)
            _log.debug("    - ownFn: %r", ownFn)

        # make/extend the list of objects already seen
        if _ids is None:
            _ids = []

        # loop through the attributes
        for attr in attrs:
            # assume you're going deep, but not into lists and dicts
            goDeep = True
            goListDict = False
            goHexed = False

            # attribute list might want to go deep
            if attr.endswith("-"):
                goDeep = False
                attr = attr[:-1]
            elif attr.endswith("*"):
                goHexed = True
                attr = attr[:-1]
            elif attr.endswith("+"):
                goDeep = False
                goListDict = True
                attr = attr[:-1]
                if attr.endswith("+"):
                    goDeep = True
                    attr = attr[:-1]

            value = getattr(self, attr, None)

            # skip None
            if value is None:
                continue

            # standard output
            if goListDict and isinstance(value, types.ListType) and value:
                file.write("%s%s = [\n" % ('    ' * indent, attr))
                indent += 1
                for i, elem in enumerate(value):
                    file.write("%s[%d] %r\n" % ('    ' * indent, i, elem))
                    if goDeep and hasattr(elem, 'debug_contents'):
                        if id(elem) not in _ids:
                            _ids.append(id(elem))
                            elem.debug_contents(indent + 1, file, _ids)
                indent -= 1
                file.write("%s    ]\n" % ('    ' * indent,))
            elif goListDict and isinstance(value, types.DictType) and value:
                file.write("%s%s = {\n" % ('    ' * indent, attr))
                indent += 1
                for key, elem in value.items():
                    file.write("%s%r : %r\n" % ('    ' * indent, key, elem))
                    if goDeep and hasattr(elem, 'debug_contents'):
                        if id(elem) not in _ids:
                            _ids.append(id(elem))
                            elem.debug_contents(indent + 1, file, _ids)
                indent -= 1
                file.write("%s    }\n" % ('    ' * indent,))
            elif goHexed and isinstance(value, types.StringType):
                if len(value) > 20:
                    hexed = _str_to_hex(value[:20],'.') + "..."
                else:
                    hexed = _str_to_hex(value,'.')
                file.write("%s%s = x'%s'\n" % ('    ' * indent, attr, hexed))
#           elif goHexed and isinstance(value, types.IntType):
#               file.write("%s%s = 0x%X\n" % ('    ' * indent, attr, value))
            else:
                file.write("%s%s = %r\n" % ('    ' * indent, attr, value))

                # go nested if it is debugable
                if goDeep and hasattr(value, 'debug_contents'):
                    if id(value) not in _ids:
                        _ids.append(id(value))
                        value.debug_contents(indent + 1, file, _ids)

        # go through the functions
        ownFn.reverse()
        for klass in ownFn:
            klass.debug_contents(self, indent, file, _ids)

#
#   LoggingFormatter
#

class LoggingFormatter(logging.Formatter):

    def __init__(self):
        logging.Formatter.__init__(self, logging.BASIC_FORMAT, None)

    def format(self, record):
        try:
            # use the basic formatting
            msg = logging.Formatter.format(self, record) + '\n'

            # look for detailed arguments
            for arg in record.args:
                if isinstance(arg, DebugContents):
                    if msg:
                        sio = cStringIO.StringIO()
                        sio.write(msg)
                        msg = None
                    sio.write("    %r\n" % (arg,))
                    arg.debug_contents(indent=2, file=sio)

            # get the message from the StringIO buffer
            if not msg:
                msg = sio.getvalue()

            # trim off the last '\n'
            msg = msg[:-1]
        except Exception, e:
            msg = "LoggingFormatter exception: " + str(e)

        return msg

#
#   _LoggingWrapper
#

def _LoggingWrapper(obj):
    # create a logger for this object
    logger = logging.getLogger(obj.__module__ + '.' + obj.__name__)
    
    # make it available to instances
    obj._logger = logger
    obj._debug = logger.debug
    obj._info = logger.info
    obj._warning = logger.warning
    obj._error = logger.error
    obj._exception = logger.exception
    obj._fatal = logger.fatal

#
#   _LoggingMetaclass
#

class _LoggingMetaclass(type):
    
    def __init__(cls, *args):
        # wrap the class
        _LoggingWrapper(cls)
        
#
#   Logging
#

class Logging(object):
    __metaclass__ = _LoggingMetaclass

#
#   function_debugging
#
#   This decorator is used to wrap a function.
#

def function_debugging(f):
    # add a wrapper to the function
    _LoggingWrapper(f)
    return f
