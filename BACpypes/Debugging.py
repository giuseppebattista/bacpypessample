#!/usr/bin/env python

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

# some debugging
_log = logging.getLogger(__name__)

#
#   DebugContents
#

class DebugContents(object):

    def DebugContents(self, indent=1, file=sys.stdout, _ids=None):
        """Debug the contents of an object."""
        _log.debug("DebugContents indent=%r file=%r _ids=%r", indent, file, _ids)

        klasses = list(self.__class__.__mro__)
        klasses.reverse()
        _log.debug("    - klasses: %r", klasses)
        
        # loop through the classes and look for _debugContents
        attrs = []
        cids = []
        ownFn = []
        for klass in klasses:
            if klass is DebugContents:
                continue
                
            if not issubclass(klass, DebugContents) and hasattr(klass, 'DebugContents'):
                for i, seenAlready in enumerate(ownFn):
                    if issubclass(klass, seenAlready):
                        del ownFn[i]
                        break
                ownFn.append(klass)
                continue
            
            # look for a tuple of attribute names
            if not hasattr(klass, '_debugContents'):
                continue
                
            debugContents = klass._debugContents
            if not isinstance(debugContents, types.TupleType):
                raise RuntimeError, "%s._debugContents must be a tuple" % (klass.__name__,)
                
            # already seen it?
            if id(debugContents) in cids:
                continue
            cids.append(id(debugContents))
            
            for attr in debugContents:
                if attr not in attrs:
                    attrs.append(attr)
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
            
            # attribute list might want to go deep
            if attr.endswith("-"):
                goDeep = False
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
                    if goDeep and hasattr(elem, 'DebugContents'):
                        if id(elem) not in _ids:
                            _ids.append(id(elem))
                            elem.DebugContents(indent + 1, file, _ids)
                indent -= 1
                file.write("%s    ]\n" % ('    ' * indent,))
            elif goListDict and isinstance(value, types.DictType) and value:
                file.write("%s%s = {\n" % ('    ' * indent, attr))
                indent += 1
                for key, elem in value.items():
                    file.write("%s%r : %r\n" % ('    ' * indent, key, elem))
                    if goDeep and hasattr(elem, 'DebugContents'):
                        if id(elem) not in _ids:
                            _ids.append(id(elem))
                            elem.DebugContents(indent + 1, file, _ids)
                indent -= 1
                file.write("%s    }\n" % ('    ' * indent,))
            else:
                file.write("%s%s = %r\n" % ('    ' * indent, attr, value))
            
                # go nested if it is debugable
                if goDeep and hasattr(value, 'DebugContents'):
                    if id(value) not in _ids:
                        _ids.append(id(value))
                        value.DebugContents(indent + 1, file, _ids)
                    
        # go through the functions
        ownFn.reverse()
        for klass in ownFn:
            klass.DebugContents(self, indent, file, _ids)

#
#
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
#   FunctionLogging
#
#   This decorator is used to wrap a function.
#

def FunctionLogging(f):
    # add a wrapper to the function
    _LoggingWrapper(f)
    return f

