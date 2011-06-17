#!/usr/bin/python

"""
Constructed Data
"""

import sys

from errors import DecodingError
from debugging import ModuleLogger, Logging

from primitivedata import *

# some debugging
_debug = 0
_log = ModuleLogger(globals())

#
#   Element
#

class Element:

    def __init__(self, name, klass, context=None, optional=False):
        self.name = name
        self.klass = klass
        self.context = context
        self.optional = optional

#
#   Sequence
#

class Sequence(Logging):

    sequenceElements = []

    def __init__(self, **kwargs):
        for element in self.sequenceElements:
            setattr(self, element.name, kwargs.get(element.name, None))

    def encode(self, taglist):
        if _debug: Sequence._debug("encode %r", taglist)
        global _sequence_of_classes

        # make sure we're dealing with a tag list
        if not isinstance(taglist, TagList):
            raise TypeError, "TagList expected"

        for element in self.sequenceElements:
            value = getattr(self, element.name, None)
            if element.optional and value is None:
                continue
            if not element.optional and value is None:
                raise AttributeError, "'%s' is a required element of %s" % (element.name,self.__class__.__name__)
            if _sequence_of_classes.has_key(element.klass):
                # might need to encode an opening tag
                if element.context is not None:
                    taglist.append(OpeningTag(element.context))

                if _debug: Sequence._debug("    - build sequence helper: %r %r", element.klass, value)
                helper = element.klass(value)

                # encode the value
                helper.encode(taglist)

                # might need to encode a closing tag
                if element.context is not None:
                    taglist.append(ClosingTag(element.context))
            elif issubclass(element.klass, Atomic):
                # a helper cooperates between the atomic value and the tag
                if _debug: Sequence._debug("    - build helper: %r %r", element.klass, value)
                helper = element.klass(value)

                # build a tag and encode the data into it
                tag = Tag()
                helper.encode(tag)

                # convert it to context encoding iff necessary
                if element.context is not None:
                    tag = tag.app_to_context(element.context)

                # now append the tag
                taglist.append(tag)
            elif isinstance(value, element.klass):
                # might need to encode an opening tag
                if element.context is not None:
                    taglist.append(OpeningTag(element.context))

                # encode the value
                value.encode(taglist)

                # might need to encode a closing tag
                if element.context is not None:
                    taglist.append(ClosingTag(element.context))
            else:
                raise TypeError, "'%s' must be a %s" % (element.name, element.klass.__name__)

    def decode(self, taglist):
        if _debug: Sequence._debug("decode %r", taglist)

        # make sure we're dealing with a tag list
        if not isinstance(taglist, TagList):
            raise TypeError, "TagList expected"

        for element in self.sequenceElements:
            tag = taglist.Peek()

            # no more elements
            if tag is None:
                if not element.optional:
                    raise AttributeError, "'%s' is a required element of %s" % (element.name,self.__class__.__name__)

                # omitted optional element
                setattr(self, element.name, None)

            # we have been enclosed in a context
            elif tag.tagClass == Tag.closingTagClass:
                if not element.optional:
                    raise AttributeError, "'%s' is a required element of %s" % (element.name,self.__class__.__name__)

                # omitted optional element
                setattr(self, element.name, None)

            # check for a sequence element
            elif _sequence_of_classes.has_key(element.klass):
                # check for context encoding
                if element.context is not None:
                    if tag.tagClass != Tag.openingTagClass or tag.tagNumber != element.context:
                        if not element.optional:
                            raise DecodingError, "'%s' expected opening tag %d" % (element.name, element.context)
                        else:
                            # omitted optional element
                            setattr(self, element.name, [])
                            continue
                    taglist.Pop()

                # a helper cooperates between the atomic value and the tag
                helper = element.klass()
                helper.decode(taglist)

                # now save the value
                setattr(self, element.name, helper.value)

                # check for context closing tag
                if element.context is not None:
                    tag = taglist.Pop()
                    if tag.tagClass != Tag.closingTagClass or tag.tagNumber != element.context:
                        raise DecodingError, "'%s' expected closing tag %d" % (element.name, context)

            # check for an atomic element
            elif issubclass(element.klass, Atomic):
                # convert it to application encoding
                if element.context is not None:
                    if tag.tagClass != Tag.contextTagClass or tag.tagNumber != element.context:
                        if not element.optional:
                            raise DecodingError, "'%s' expected context tag %d" % (element.name, element.context)
                        else:
                            setattr(self, element.name, None)
                            continue
                    tag = tag.context_to_app(element.klass._app_tag)
                else:
                    if tag.tagClass != Tag.applicationTagClass or tag.tagNumber != element.klass._app_tag:
                        if not element.optional:
                            raise DecodingError, "'%s' expected application tag %s" % (element.name, Tag._app_tag_name[element.klass._app_tag])
                        else:
                            setattr(self, element.name, None)
                            continue

                # consume the tag
                taglist.Pop()

                # a helper cooperates between the atomic value and the tag
                helper = element.klass(tag)

                # now save the value
                setattr(self, element.name, helper.value)

            # some kind of structure
            else:
                if element.context is not None:
                    if tag.tagClass != Tag.openingTagClass or tag.tagNumber != element.context:
                        if not element.optional:
                            raise DecodingError, "'%s' expected opening tag %d" % (element.name, element.context)
                        else:
                            setattr(self, element.name, None)
                            continue
                    taglist.Pop()

                try:
                    # make a backup of the tag list in case the structure manages to
                    # decode some content but not all of it.  This is not supposed to
                    # happen if the ASN.1 has been formed correctly.
                    backup = taglist.tagList[:]

                    # build a value and decode it
                    value = element.klass()
                    value.decode(taglist)

                    # save the result
                    setattr(self, element.name, value)
                except DecodingError:
                    # if the context tag was matched, the substructure has to be decoded
                    # correctly.
                    if element.context is None and element.optional:
                        # omitted optional element
                        setattr(self, element.name, None)

                        # restore the backup
                        taglist.tagList = backup
                    else:
                        raise

                if element.context is not None:
                    tag = taglist.Pop()
                    if (not tag) or tag.tagClass != Tag.closingTagClass or tag.tagNumber != element.context:
                        raise DecodingError, "'%s' expected closing tag %d" % (element.name, element.context)

    def debug_contents(self, indent=1, file=sys.stdout, _ids=None):
        global _sequence_of_classes

        for element in self.sequenceElements:
            value = getattr(self, element.name, None)
            if element.optional and value is None:
                continue
            if not element.optional and value is None:
                file.write("%s'%s' is a required element of %s\n" % ("    " * indent, element.name, self.__class__.__name__))
                continue
                
            if _sequence_of_classes.has_key(element.klass):
                file.write("%s%s\n" % ("    " * indent, element.name))
                helper = element.klass(value)
                helper.debug_contents(indent+1, file, _ids)
                
            elif issubclass(element.klass, Atomic):
                file.write("%s%s = %r\n" % ("    " * indent, element.name, value))
                
            elif isinstance(value, element.klass):
                file.write("%s%s\n" % ("    " * indent, element.name))
                value.debug_contents(indent+1, file, _ids)
                
            else:
                file.write("%s'%s' must be a %s\n" % ("    " * indent, element.name, element.klass.__name__))

#
#   SequenceOf
#

_sequence_of_map = {}
_sequence_of_classes = {}

def SequenceOf(klass):
    """Function to return a class that can encode and decode a list of
    some other type."""
    global _sequence_of_map
    global _sequence_of_classes, _array_of_classes

    # if this has already been built, return the cached one
    if _sequence_of_map.has_key(klass):
        return _sequence_of_map[klass]

    # no SequenceOf(SequenceOf(...)) allowed
    if _sequence_of_classes.has_key(klass):
        raise TypeError, "nested sequences disallowed"
    # no SequenceOf(ArrayOf(...)) allowed
    if _array_of_classes.has_key(klass):
        raise TypeError, "sequences of arrays disallowed"

    # define a generic class for lists
    class SequenceOf(Logging):

        subtype = None

        def __init__(self,value=None):
            if value is None:
                self.value = []
            elif isinstance(value, types.ListType):
                self.value = value
            else:
                raise TypeError, "invalid constructor datatype"

        def append(self, value):
            if issubclass(self.subtype, Atomic):
                pass
            elif not isinstance(value, self.subtype):
                raise TypeError, "%s value required" % (value, self.subtype.__name__,)
            self.value.append(value)

        def __len__(self):
            return len(self.value)

        def __getitem__(self, item):
            return self.value[item]

        def encode(self, taglist):
            if _debug: SequenceOf._debug("(%r)encode %r", self.__class__.__name__, taglist)
            for value in self.value:
                if issubclass(self.subtype, Atomic):
                    # a helper cooperates between the atomic value and the tag
                    helper = self.subtype(value)

                    # build a tag and encode the data into it
                    tag = Tag()
                    helper.encode(tag)

                    # now encode the tag
                    taglist.append(tag)
                elif isinstance(value, self.subtype):
                    # it must have its own encoder
                    value.encode(taglist)
                else:
                    raise TypeError, "%s must be a %s" % (value, self.subtype.__name__)

        def decode(self, taglist):
            if _debug: SequenceOf._debug("(%r)decode %r", self.__class__.__name__, taglist)

            while len(taglist) != 0:
                tag = taglist.Peek()
                if tag.tagClass == Tag.closingTagClass:
                    return

                if issubclass(self.subtype, Atomic):
                    if _debug: SequenceOf._debug("    - building helper: %r %r", self.subtype, tag)
                    taglist.Pop()

                    # a helper cooperates between the atomic value and the tag
                    helper = self.subtype(tag)

                    # save the value
                    self.value.append(helper.value)
                else:
                    if _debug: SequenceOf._debug("    - building value: %r", self.subtype)
                    # build an element
                    value = self.subtype()

                    # let it decode itself
                    value.decode(taglist)

                    # save what was built
                    self.value.append(value)

        def debug_contents(self, indent=1, file=sys.stdout, _ids=None):
            i = 0
            for value in self.value:
                if issubclass(self.subtype, Atomic):
                    file.write("%s[%d] = %r\n" % ("    " * indent, i, value))
                elif isinstance(value, self.subtype):
                    file.write("%s[%d]" % ("    " * indent, i))
                    value.debug_contents(indent+1, file, _ids)
                else:
                    file.write("%s[%d] %s must be a %s" % ("    " * indent, i, value, self.subtype.__name__))
                i += 1

    # constrain it to a list of a specific type of item
    setattr(SequenceOf, 'subtype', klass)
    SequenceOf.__name__ = 'SequenceOf(%s.%s)' % (klass.__module__, klass.__name__)

    # cache this type
    _sequence_of_map[klass] = SequenceOf
    _sequence_of_classes[SequenceOf] = 1

    # return this new type
    return SequenceOf

#
#   Array
#
#   Arrays of things are a derived class of Array to make it easier to check
#   to see if a property is an array of something.
#

class Array(object):
    pass

#
#   ArrayOf
#

_array_of_map = {}
_array_of_classes = {}

def ArrayOf(klass):
    """Function to return a class that can encode and decode a list of
    some other type."""
    global _array_of_map
    global _array_of_classes, _sequence_of_classes

    # if this has already been built, return the cached one
    if _array_of_map.has_key(klass):
        return _array_of_map[klass]

    # no ArrayOf(ArrayOf(...)) allowed
    if _array_of_classes.has_key(klass):
        raise TypeError, "nested arrays disallowed"
    # no ArrayOf(SequenceOf(...)) allowed
    if _sequence_of_classes.has_key(klass):
        raise TypeError, "arrays of SequenceOf disallowed"

    # define a generic class for arrays
    class ArrayOf(Array, Logging):

        subtype = None

        def __init__(self, value=None):
            if value is None:
                self.value = [0]
            elif isinstance(value,types.ListType):
                self.value = [len(value)]
                self.value.extend(value)
            else:
                raise TypeError, "invalid constructor datatype"

        def append(self, value):
            if issubclass(self.subtype, Atomic):
                pass
            elif not isinstance(value, self.subtype):
                raise TypeError, "%s value required" % (self.subtype.__name__,)
            self.value.append(value)
            self.value[0] = len(self.value) - 1

        def __len__(self):
            return self.value[0]

        def __getitem__(self, item):
            # no wrapping index
            if (item < 0) or (item > self.value[0]):
                raise IndexError, "index out of range"
                
            return self.value[item]

        def __setitem__(self, item, value):
            # no wrapping index
            if (item < 1) or (item > self.value[0]):
                raise IndexError, "index out of range"
                
            # special length handling for index 0
            if item == 0:
                if value < self.value[0]:
                    # trim
                    self.value = self.value[0:value + 1]
                elif value > self.value[0]:
                    # extend
                    self.value.extend( [None] * (value - self.value[0]) )
                else:
                    return
                self.value[0] = value
            else:
                self.value[item] = value

        def __delitem__(self, item):
            # no wrapping index
            if (item < 1) or (item > self.value[0]):
                raise IndexError, "index out of range"
                
            # delete the item and update the length
            del self.value[item]
            self.value[0] -= 1

        def index(self, value):
            # only search through values
            for i in range(1, self.value[0] + 1):
                if value == self.value[i]:
                    return i

            # not found
            raise ValueError, "%r not in array" % (item,)

        def encode(self, taglist):
            if _debug: ArrayOf._debug("(%r)encode %r", self.__class__.__name__, taglist)

            for value in self.value[1:]:
                if issubclass(self.subtype, Atomic):
                    # a helper cooperates between the atomic value and the tag
                    helper = self.subtype(value)

                    # build a tag and encode the data into it
                    tag = Tag()
                    helper.encode(tag)

                    # now encode the tag
                    taglist.append(tag)
                elif isinstance(value, self.subtype):
                    # it must have its own encoder
                    value.encode(taglist)
                else:
                    raise TypeError, "%s must be a %s" % (value, self.subtype.__name__)

        def decode(self, taglist):
            if _debug: ArrayOf._debug("(%r)decode %r", self.__class__.__name__, taglist)

            # start with an empty array
            self.value = [0]
            
            while len(taglist) != 0:
                tag = taglist.Peek()
                if tag.tagClass == Tag.closingTagClass:
                    break

                if issubclass(self.subtype, Atomic):
                    if _debug: ArrayOf._debug("    - building helper: %r %r", self.subtype, tag)
                    taglist.Pop()

                    # a helper cooperates between the atomic value and the tag
                    helper = self.subtype(tag)

                    # save the value
                    self.value.append(helper.value)
                else:
                    if _debug: ArrayOf._debug("    - building value: %r", self.subtype)
                    # build an element
                    value = self.subtype()

                    # let it decode itself
                    value.decode(taglist)

                    # save what was built
                    self.value.append(value)

            # update the length
            self.value[0] = len(self.value) - 1
            
        def encode_item(self, item, taglist):
            if _debug: ArrayOf._debug("(%r)encode_item %r %r", self.__class__.__name__, item, taglist)
                
            if item == 0:
                # a helper cooperates between the atomic value and the tag
                helper = Unsigned(self.value[0])

                # build a tag and encode the data into it
                tag = Tag()
                helper.encode(tag)

                # now encode the tag
                taglist.append(tag)
            else:
                value = self.value[item]
                
                if issubclass(self.subtype, Atomic):
                    # a helper cooperates between the atomic value and the tag
                    helper = self.subtype(self.value[item])
        
                    # build a tag and encode the data into it
                    tag = Tag()
                    helper.encode(tag)
        
                    # now encode the tag
                    taglist.append(tag)
                elif isinstance(value, self.subtype):
                    # it must have its own encoder
                    value.encode(taglist)
                else:
                    raise TypeError, "%s must be a %s" % (value, self.subtype.__name__)

        def decode_item(self, item, taglist):
            if _debug: ArrayOf._debug("(%r)decode_item %r %r", self.__class__.__name__, item, taglist)

            if item == 0:
                # a helper cooperates between the atomic value and the tag
                helper = Unsigned(taglist.Pop())

                # save the value
                self.value = helper.value
            elif issubclass(self.subtype, Atomic):
                if _debug: ArrayOf._debug("    - building helper: %r", self.subtype)
                    
                # a helper cooperates between the atomic value and the tag
                helper = self.subtype(taglist.Pop())

                # save the value
                self.value = helper.value
            else:
                if _debug: ArrayOf._debug("    - building value: %r", self.subtype)
                # build an element
                value = self.subtype()

                # let it decode itself
                value.decode(taglist)

                # save what was built
                self.value = value

        def debug_contents(self, indent=1, file=sys.stdout, _ids=None):
            try:
                value_list = enumerate(self.value)
            except TypeError:
                file.write("%s(non-sequence) %r\n" % ("    " * indent, self.value))
                return
                
            for i, value in value_list:
                if i == 0:
                    file.write("%slength = %d\n" % ("    " * indent, value))
                elif issubclass(self.subtype, Atomic):
                    file.write("%s[%d] = %r\n" % ("    " * indent, i, value))
                elif isinstance(value, self.subtype):
                    file.write("%s[%d]\n" % ("    " * indent, i))
                    value.debug_contents(indent+1, file, _ids)
                else:
                    file.write("%s%s must be a %s" % ("    " * indent, value, self.subtype.__name__))

    # constrain it to a list of a specific type of item
    setattr(ArrayOf, 'subtype', klass)
    ArrayOf.__name__ = 'ArrayOf(%s.%s)' % (klass.__module__, klass.__name__)

    # cache this type
    _array_of_map[klass] = ArrayOf
    _array_of_classes[ArrayOf] = 1

    # return this new type
    return ArrayOf

#
#   Choice
#

class Choice(Logging):

    choiceElements = []

    def __init__(self, **kwargs):
        for element in self.choiceElements:
            setattr(self, element.name, kwargs.get(element.name, None))

    def encode(self, taglist):
        if _debug: Choice._debug("(%r)encode %r %r", self.__class__.__name__, taglist)

        for element in self.choiceElements:
            value = getattr(self, element.name, None)
            if value is None:
                continue

            if issubclass(element.klass,Atomic):
                # a helper cooperates between the atomic value and the tag
                helper = element.klass(value)

                # build a tag and encode the data into it
                tag = Tag()
                helper.encode(tag)

                # convert it to context encoding
                if element.context is not None:
                    tag = tag.app_to_context(element.context)

                # now encode the tag
                taglist.append(tag)
                break

            elif isinstance(value, element.klass):
                # encode an opening tag
                if element.context is not None:
                    taglist.append(OpeningTag(element.context))

                # encode the value
                value.encode(taglist)

                # encode a closing tag
                if element.context is not None:
                    taglist.append(ClosingTag(element.context))
                break

            else:
                raise TypeError, "'%s' must be a %s" % (element.name, element.klass.__name__)
        else:
            raise AttributeError, "missing choice of %s" % (self.__class__.__name__,)

    def decode(self, taglist):
        if _debug: Choice._debug("(%r)decode %r %r", self.__class__.__name__, taglist)

        # peek at the element
        tag = taglist.Peek()
        if tag is None:
            raise AttributeError, "missing choice of %s" % (self.__class__.__name__,)
        if tag.tagClass == Tag.closingTagClass:
            raise AttributeError, "missing choice of %s" % (self.__class__.__name__,)

        # keep track of which one was found
        foundElement = {}

        # figure out which choice it is
        for element in self.choiceElements:
            if _debug: Choice._debug("    - checking choice: %s", element.name)

            # check for a sequence element
            if _sequence_of_classes.has_key(element.klass):
                # check for context encoding
                if element.context is None:
                    raise NotImplementedError, "choice of a SequenceOf must be context encoded"
                # match the context tag number
                if tag.tagClass != Tag.contextTagClass or tag.tagNumber != element.context:
                    continue
                taglist.Pop()

                # a helper cooperates between the atomic value and the tag
                helper = element.klass()
                helper.decode(taglist)

                # now save the value
                foundElement[element.name] = helper.value

                # check for context closing tag
                tag = taglist.Pop()
                if tag.tagClass != Tag.closingTagClass or tag.tagNumber != element.context:
                    raise DecodingError, "'%s' expected closing tag %d" % (element.name, context)

                # done
                if _debug: Choice._debug("    - found choice (sequence)")
                break

            # check for an atomic element
            elif issubclass(element.klass, Atomic):
                # convert it to application encoding
                if element.context is not None:
                    if tag.tagClass != Tag.contextTagClass or tag.tagNumber != element.context:
                        continue
                    tag = tag.context_to_app(element.klass._app_tag)
                else:
                    if tag.tagClass != Tag.applicationTagClass or tag.tagNumber != element.klass._app_tag:
                        continue

                # consume the tag
                taglist.Pop()

                # a helper cooperates between the atomic value and the tag
                helper = element.klass(tag)

                # now save the value
                foundElement[element.name] = helper.value

                # done
                if _debug: Choice._debug("    - found choice (atomic)")
                break

            # some kind of structure
            else:
                # check for context encoding
                if element.context is None:
                    raise NotImplementedError, "choice of non-atomic data must be context encoded"
                if tag.tagClass != Tag.openingTagClass or tag.tagNumber != element.context:
                    continue
                taglist.Pop()

                # build a value and decode it
                value = element.klass()
                value.decode(taglist)

                # now save the value
                foundElement[element.name] = value

                # check for the correct closing tag
                tag = taglist.Pop()
                if tag.tagClass != Tag.closingTagClass or tag.tagNumber != element.context:
                    raise DecodingError, "'%s' expected closing tag %d" % (element.name, context)

                # done
                if _debug: Choice._debug("    - found choice (structure)")
                break
        else:
            raise AttributeError, "missing choice of %s" % (self.__class__.__name__,)

        # now save the value and None everywhere else
        for element in self.choiceElements:
            setattr(self, element.name, foundElement.get(element.name, None))

    def debug_contents(self, indent=1, file=sys.stdout, _ids=None):
        for element in self.choiceElements:
            value = getattr(self, element.name, None)
            if value is None:
                continue

            elif issubclass(element.klass, Atomic):
                file.write("%s%s = %r\n" % ("    " * indent, element.name, value))
                break
                
            elif isinstance(value, element.klass):
                file.write("%s%s\n" % ("    " * indent, element.name))
                value.debug_contents(indent+1, file, _ids)
                break
                
            else:
                file.write("%s%s must be a %s" % ("    " * indent, element.name, element.klass.__name__))
        else:
            file.write("%smissing choice of %s" % ("    " * indent, self.__class__.__name__))

#
#   Any
#

class Any(Logging):

    def __init__(self, *args):
        self.tagList = TagList()

        # cast in the args
        for arg in args:
            self.cast_in(arg)

    def encode(self, taglist):
        if _debug: Any._debug("encode %r", taglist)

        taglist.extend(self.tagList)

    def decode(self, taglist):
        if _debug: Any._debug("decode %r", taglist)

        lvl = 0
        while len(taglist) != 0:
            tag = taglist.Peek()
            if tag.tagClass == Tag.openingTagClass:
                lvl += 1
            elif tag.tagClass == Tag.closingTagClass:
                lvl -= 1
                if lvl < 0: break

            self.tagList.append(taglist.Pop())

        # make sure everything balances
        if lvl > 0:
            raise DecodingError, "mismatched open/close tags"

    def cast_in(self, element):
        """encode the element into the internal tag list."""
        if _debug: Any._debug("cast_in %r", element)

        t = TagList()
        if isinstance(element, Atomic):
            tag = Tag()
            element.encode(tag)
            t.append(tag)
        else:
            element.encode(t)

        self.tagList.extend(t.tagList)

    def cast_out(self, klass):
        """Interpret the content as a particular class."""
        if _debug: Any._debug("cast_out %r", klass)

        # check for a sequence element
        if _sequence_of_classes.has_key(klass):
            # build a sequence helper
            helper = klass()

            # make a copy of the tag list
            t = TagList(self.tagList[:])

            # let it decode itself
            helper.decode(t)

            # make sure everything was consumed
            if len(t) != 0:
                raise DecodingError, "incomplete cast"

            # return what was built
            return helper.value

        elif issubclass(klass, Atomic):
            # make sure there's only one piece
            if len(self.tagList) == 0:
                raise DecodingError, "missing cast component"
            if len(self.tagList) > 1:
                raise DecodingError, "too many cast components"

            if _debug: Any._debug("    - building helper: %r", klass)

            # a helper cooperates between the atomic value and the tag
            helper = klass(self.tagList[0])

            # return the value
            return helper.value

        else:
            if _debug: Any._debug("    - building value: %r", klass)

            # build an element
            value = klass()

            # make a copy of the tag list
            t = TagList(self.tagList[:])

            # let it decode itself
            value.decode(t)

            # make sure everything was consumed
            if len(t) != 0:
                raise DecodingError, "incomplete cast"

            # return what was built
            return value

    def debug_contents(self, indent=1, file=sys.stdout, _ids=None):
        self.tagList.debug_contents(indent, file, _ids)
