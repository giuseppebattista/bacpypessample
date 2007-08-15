
import time

from Exceptions import *
from PDU import *

# some debugging
_debug = 0

def _StringToHex(x,sep=''):
    return sep.join(["%02X" % (ord(c),) for c in x])

def _HexToString(x,sep=''):
    if sep:
        parts = x.split(sep)
    else:
        parts = [x[i:i+2] for i in range(0,len(x),2)]
    
    return ''.join([chr(int(part,16)) for part in parts])

#
#   Tag
#

class Tag:
    applicationTagClass     = 0
    contextTagClass         = 1
    openingTagClass         = 2
    closingTagClass         = 3

    nullAppTag              = 0
    booleanAppTag           = 1
    unsignedAppTag          = 2
    integerAppTag           = 3
    realAppTag              = 4
    doubleAppTag            = 5
    octetStringAppTag       = 6
    characterStringAppTag   = 7
    bitStringAppTag         = 8
    enumeratedAppTag        = 9
    dateAppTag              = 10
    timeAppTag              = 11
    objectIdentifierAppTag  = 12
    reservedAppTag13        = 13
    reservedAppTag14        = 14
    reservedAppTag15        = 15

    _applicationTagName = \
        [ 'null', 'boolean', 'unsigned', 'integer'
        , 'real', 'double', 'octetString', 'characterString'
        , 'bitString', 'enumerated', 'date', 'time'
        , 'objectIdentifier', 'reserved13', 'reserved14', 'reserved15'
        ]
    _applicationTagClass = [] # defined later

    def __init__(self, *args):
        self.tagClass = None
        self.tagNumber = None
        self.tagLVT = None
        self.tagData = None

        if args:
            if (len(args) == 1) and isinstance(args[0], PDUData):
                self.Decode(args[0])
            elif (len(args) >= 2):
                self.Set(*args)
            else:
                raise ValueError, "invalid Tag ctor arguments"

    def Set(self, tclass, tnum, tlvt=0, tdata=''):
        """Set the values of the tag."""
        self.tagClass = tclass
        self.tagNumber = tnum
        self.tagLVT = tlvt
        self.tagData = tdata

    def SetAppData(self, tnum, tdata):
        """Set the values of the tag."""
        self.tagClass = Tag.applicationTagClass
        self.tagNumber = tnum
        self.tagLVT = len(tdata)
        self.tagData = tdata

    def Encode(self, pdu):
        # check for special encoding of open and close tags
        if (self.tagClass == Tag.openingTagClass):
            pdu.Put(((self.tagNumber & 0x0F) << 4) + 0x0E)
            return
        if (self.tagClass == Tag.closingTagClass):
            pdu.Put(((self.tagNumber & 0x0F) << 4) + 0x0F)
            return

        # check for context encoding
        if (self.tagClass == Tag.contextTagClass):
            data = 0x08
        else:
            data = 0x00

        # encode the tag number part
        if (self.tagNumber < 15):
            data += (self.tagNumber << 4)
        else:
            data += 0xF0

        # encode the length/value/type part
        if (self.tagLVT < 5):
            data += self.tagLVT
        else:
            data += 0x05

        # save this and the extended tag value
        pdu.Put( data )
        if (self.tagNumber >= 15):
            pdu.Put(self.tagNumber)

        # really short lengths are already done
        if (self.tagLVT >= 5):
            if (self.tagLVT <= 253):
                pdu.Put( self.tagLVT )
            elif (self.tagLVT <= 65535):
                enc.Put( 254 )
                pdu.PutShort( self.tagLVT )
            else:
                pdu.Put( 255 )
                pdu.PutLong( self.tagLVT )

        # now put the data
        pdu.PutData(self.tagData)

    def Decode(self, pdu):
        tag = pdu.Get()

        # extract the type
        self.tagClass = (tag >> 3) & 0x01

        # extract the tag number
        self.tagNumber = (tag >> 4)
        if (self.tagNumber == 0x0F):
            self.tagNumber = dec.Get()

        # extract the length
        self.tagLVT = tag & 0x07
        if (self.tagLVT == 5):
            self.tagLVT = pdu.Get()
            if (self.tagLVT == 254):
                self.tagLVT = pdu.GetShort()
            elif (self.tagLVT == 255):
                self.tagLVT = pdu.GetLong()
        elif (self.tagLVT == 6):
            self.tagClass = Tag.openingTagClass
            self.tagLVT = 0
        elif (self.tagLVT == 7):
            self.tagClass = Tag.closingTagClass
            self.tagLVT = 0

        # application tagged boolean has no more data
        if (self.tagClass == Tag.applicationTagClass) and (self.tagNumber == Tag.booleanAppTag):
            # tagLVT contains value
            self.tagData = ''
        else:
            # tagLVT contains length
            self.tagData = pdu.GetData(self.tagLVT)

    def AppToCtx(self, context):
        """Return a context encoded tag."""
        if self.tagClass != Tag.applicationTagClass:
            raise ValueError, "application tag required"

        # application tagged boolean now has data
        if (self.tagNumber == Tag.booleanAppTag):
            return ContextTag(context, chr(self.tagLVT))
        else:
            return ContextTag(context, self.tagData)

    def CtxToApp(self, dataType):
        """Return an application encoded tag."""
        if self.tagClass != Tag.contextTagClass:
            raise ValueError, "context tag required"

        # context booleans have value in data
        if (dataType == Tag.booleanAppTag):
            return Tag(Tag.applicationTagClass, Tag.booleanAppTag, ord(self.tagData[0]), '')
        else:
            return ApplicationTag(dataType, self.tagData)

    def AppToObject(self):
        """Return the application object encoded by the tag."""
        if self.tagClass != Tag.applicationTagClass:
            raise ValueError, "application tag required"

        # get the class to build
        klass = self._applicationTagClass[self.tagNumber]
        if not klass:
            return None

        # build an object, tell it to decode this tag, and return it
        return klass(self)

    def __repr__(self):
        xid = id(self)
        if (xid < 0): xid += (1L << 32)

        sname = self.__module__ + '.' + self.__class__.__name__
        try:
            if self.tagClass == Tag.openingTagClass:
                desc = "(open(%d))" % (self.tagNumber,)
            elif self.tagClass == Tag.closingTagClass:
                desc = "(close(%d))" % (self.tagNumber,)
            elif self.tagClass == Tag.contextTagClass:
                desc = "(context(%d))" % (self.tagNumber,)
            elif self.tagClass == Tag.applicationTagClass:
                desc = "(%s)" % (self._applicationTagName[self.tagNumber],)
            else:
                raise ValueError, "invalid tag class"
        except:
            desc = "(?)"

        return '<' + sname + desc + ' instance at 0x%08x' % (xid,) + '>'

    def __eq__(self, tag):
        return (self.tagClass == tag.tagClass) \
            and (self.tagNumber == tag.tagNumber) \
            and (self.tagLVT == tag.tagLVT) \
            and (self.tagData == tag.tagData)

    def __ne__(self,arg):
        return not self.__eq__(arg)

    def DebugContents(self, indent=1):
        # object reference first
        print "%s%r" % ("    " * indent, self)
        indent += 1
        
        # tag class
        print "%stagClass =" % ("    " * indent,), self.tagClass,
        if self.tagClass == Tag.applicationTagClass: print 'application'
        elif self.tagClass == Tag.contextTagClass: print 'context'
        elif self.tagClass == Tag.openingTagClass: print 'opening'
        elif self.tagClass == Tag.closingTagClass: print 'closing'
        else: print "?"
        
        # tag number
        print "%stagNumber =" % ("    " * indent,), self.tagNumber,
        if self.tagClass == Tag.applicationTagClass:
            try:
                print self._applicationTagName[self.tagNumber]
            except:
                print "?"
        else: print
        
        # length, value, type
        print "%stagLVT =" % ("    " * indent,), self.tagLVT,
        if self.tagLVT != len(self.tagData): print "(length does not match data)"
        else: print "(length match)"
        
        # data
        print "%stagData = '%s'" % ("    " * indent, _StringToHex(self.tagData,'.'))
    
#
#   ApplicationTag
#

class ApplicationTag(Tag):

    def __init__(self, *args):
        if len(args) == 1 and isinstance(args[0], PDUData):
            Tag.__init__(self, args[0])
            if self.tagClass != Tag.applicationTagClass:
                raise DecodingError, "application tag not decoded"
        elif len(args) == 2:
            tnum, tdata = args
            Tag.__init__(self, Tag.applicationTagClass, tnum, len(tdata), tdata)
        else:
            raise ValueError, "ApplicationTag ctor requires a type and data or PDUData"

#
#   ContextTag
#

class ContextTag(Tag):

    def __init__(self, *args):
        if len(args) == 1 and isinstance(args[0], PDUData):
            Tag.__init__(self, args[0])
            if self.tagClass != Tag.contextTagClass:
                raise DecodingError, "context tag not decoded"
        elif len(args) == 2:
            tnum, tdata = args
            Tag.__init__(self, Tag.contextTagClass, tnum, len(tdata), tdata)
        else:
            raise ValueError, "ContextyTag ctor requires a type and data or PDUData"

#
#   OpeningTag
#

class OpeningTag(Tag):

    def __init__(self, context):
        if isinstance(context, PDUData):
            Tag.__init__(self, context)
            if self.tagClass != Tag.openingTagClass:
                raise DecodingError, "opening tag not decoded"
        elif isinstance(context, types.IntType):
            Tag.__init__(self, Tag.openingTagClass, context)
        else:
            raise TypeError, "OpeningTag ctor requires an integer or PDUData"

#
#   ClosingTag
#

class ClosingTag(Tag):

    def __init__(self, context):
        if isinstance(context, PDUData):
            Tag.__init__(self, context)
            if self.tagClass != Tag.closingTagClass:
                raise DecodingError, "closing tag not decoded"
        elif isinstance(context, types.IntType):
            Tag.__init__(self, Tag.closingTagClass, context)
        else:
            raise TypeError, "OpeningTag ctor requires an integer or PDUData"

#
#   TagList
#

class TagList:

    def __init__(self, arg=None):
        self.tagList = []

        if isinstance(arg, types.ListType):
            self.tagList = arg
        elif isinstance(arg, TagList):
            self.tagList = arg.tagList[:]
        elif isinstance(arg, PDUData):
            self.Decode(arg)

    def append(self, tag):
        self.tagList.append(tag)

    def extend(self, taglist):
        self.tagList.extend(taglist)

    def __getitem__(self, item):
        return self.tagList[item]

    def __len__(self):
        return len(self.tagList)

    def Peek(self):
        """Return the tag at the front of the list."""
        if self.tagList:
            tag = self.tagList[0]
        else:
            tag = None

        if _debug:
            print "(peek)", tag

        return tag

    def Push(self, tag):
        """Return a tag back to the front of the list."""
        if _debug:
            print "(push)", tag

        self.tagList = [tag] + self.tagList

    def Pop(self):
        """Remove the tag from the front of the list and return it."""
        if self.tagList:
            tag = self.tagList[0]
            del self.tagList[0]
        else:
            tag = None

        if _debug:
            print "(pop)", tag

        return tag

    def GetContext(self, context):
        """Return a tag or a list of tags context encoded."""
        # forward pass
        i = 0
        while i < len(self.tagList):
            tag = self.tagList[i]

            # skip application stuff
            if tag.tagClass == Tag.applicationTagClass:
                pass

            # check for context encoded atomic value
            elif tag.tagClass == Tag.contextTagClass:
                if tag.tagNumber == context:
                    return tag

            # check for context encoded group
            elif tag.tagClass == Tag.openingTagClass:
                keeper = tag.tagNumber == context
                rslt = []
                i += 1
                lvl = 0
                while i < len(self.tagList):
                    tag = self.tagList[i]
                    if tag.tagClass == Tag.openingTagClass:
                        lvl += 1
                    elif tag.tagClass == Tag.closingTagClass:
                        lvl -= 1
                        if lvl < 0: break

                    rslt.append(tag)
                    i += 1

                # make sure everything balances
                if lvl >= 0:
                    raise DecodingError, "mismatched open/close tags"

                # get everything we need?
                if keeper:
                    return TagList(rslt)
            else:
                raise DecodingError, "unexpected tag"

            # try the next tag
            i += 1

        # nothing found
        return None

    def Encode(self, pdu):
        """Encode the tag list into a PDU."""
        for tag in self.tagList:
            tag.Encode(pdu)

    def Decode(self, pdu):
        """Decode the tags from a PDU."""
        while pdu.pduData:
            self.tagList.append( Tag(pdu) )

    def DebugContents(self, indent=1):
        for tag in self.tagList:
            tag.DebugContents(indent+1)
            
#
#   Atomic
#

class Atomic:

    _appTag = None

    def __cmp__(self, other):
        # hoop jump it
        if not isinstance(other, self.__class__):
            other = self.__class__(other)

        # now compare the values
        if (self.value < other.value):
            return -1
        elif (self.value > other.value):
            return 1
        else:
            return 0

#
#   Null
#

class Null(Atomic):

    _appTag = Tag.nullAppTag

    def __init__(self, arg=None):
        self.value = ()

        if arg is None:
            pass
        elif isinstance(arg,Tag):
            self.Decode(arg)
        elif isinstance(arg,types.TupleType):
            if len(arg) != 0:
                raise ValueError, "empty tuple required"
        else:
            raise TypeError, "invalid constructor datatype"

    def Encode(self, tag):
        tag.SetAppData(Tag.nullAppTag, '')

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.nullAppTag):
            raise ValueError, "null application tag required"

        self.value = ()

    def __str__(self):
        return "Null"

#
#   Boolean
#

class Boolean(Atomic):

    _appTag = Tag.booleanAppTag

    def __init__(self, arg=None):
        self.value = False

        if arg is None:
            pass
        elif isinstance(arg,Tag):
            self.Decode(arg)
        elif isinstance(arg,types.BooleanType):
            self.value = arg
        else:
            raise TypeError, "invalid constructor datatype"

    def Encode(self, tag):
        tag.Set(Tag.applicationTagClass, Tag.booleanAppTag, int(self.value), '')

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.booleanAppTag):
            raise ValueError, "boolean application tag required"

        # get the data
        self.value = bool(tag.tagLVT)

    def __str__(self):
        return "Boolean(%s)" % (str(self.value), )

#
#   Unsigned
#

class Unsigned(Atomic):

    _appTag = Tag.unsignedAppTag

    def __init__(self,arg = None):
        self.value = 0L

        if arg is None:
            pass
        elif isinstance(arg,Tag):
            self.Decode(arg)
        elif isinstance(arg,types.IntType):
            if (arg < 0):
                raise ValueError, "unsigned integer required"
            self.value = long(arg)
        elif isinstance(arg,types.LongType):
            if (arg < 0):
                raise ValueError, "unsigned integer required"
            self.value = arg
        else:
            raise TypeError, "invalid constructor datatype"

    def Encode(self, tag):
        # rip apart the number
        data = [ord(c) for c in struct.pack('>L',self.value)]

        # reduce the value to the smallest number of octets
        while (len(data) > 1) and (data[0] == 0):
            del data[0]

        # encode the tag
        tag.SetAppData(Tag.unsignedAppTag, ''.join(chr(c) for c in data))

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.unsignedAppTag):
            raise ValueError, "unsigned application tag required"

        # get the data
        rslt = 0L
        for c in tag.tagData:
            rslt = (rslt << 8) + ord(c)

        # save the result
        self.value = rslt

    def __str__(self):
        return "Unsigned(%s)" % (self.value, )

#
#   Integer
#

class Integer(Atomic):

    _appTag = Tag.integerAppTag

    def __init__(self,arg = None):
        self.value = 0

        if arg is None:
            pass
        elif isinstance(arg,Tag):
            self.Decode(arg)
        elif isinstance(arg,types.IntType):
            self.value = arg
        elif isinstance(arg,types.LongType):
            self.value = arg
        else:
            raise TypeError, "invalid constructor datatype"

    def Encode(self, tag):
        # rip apart the number
        data = [ord(c) for c in struct.pack('>I',self.value)]

        # reduce the value to the smallest number of bytes, be
        # careful about sign extension
        if self.value < 0:
            while (len(data) > 1):
                if (data[0] != 255):
                    break
                if (data[1] < 128):
                    break
                del data[0]
        else:
            while (len(data) > 1):
                if (data[0] != 0):
                    break
                if (data[1] >= 128):
                    break
                del data[0]

        # encode the tag
        tag.SetAppData(Tag.integerAppTag, ''.join(chr(c) for c in data))

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.integerAppTag):
            raise ValueError, "integer application tag required"

        # get the data
        rslt = ord(tag.tagData[0])
        if (rslt & 0x80) != 0:
            rslt = (-1 << 8) | rslt

        for c in tag.tagData[1:]:
            rslt = (rslt << 8) | ord(c)

        # save the result
        self.value = rslt

    def __str__(self):
        return "Integer(%s)" % (self.value, )

#
#   Real
#

class Real(Atomic):

    _appTag = Tag.realAppTag

    def __init__(self, arg=None):
        self.value = 0.0

        if arg is None:
            pass
        elif isinstance(arg,Tag):
            self.Decode(arg)
        elif isinstance(arg,types.FloatType):
            self.value = arg
        else:
            raise TypeError, "invalid constructor datatype"

    def Encode(self, tag):
        # encode the tag
        tag.SetAppData(Tag.realAppTag, struct.pack('>f',self.value))

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.realAppTag):
            raise ValueError, "real application tag required"

        # extract the data
        self.value = struct.unpack('>f',tag.tagData)[0]

    def __str__(self):
        return "Real(%g)" % (self.value,)

#
#   Double
#

class Double(Atomic):

    _appTag = Tag.doubleAppTag

    def __init__(self,arg = None):
        self.value = 0.0

        if arg is None:
            pass
        elif isinstance(arg,Tag):
            self.Decode(arg)
        elif isinstance(arg,types.FloatType):
            self.value = arg
        else:
            raise TypeError, "invalid constructor datatype"

    def Encode(self, tag):
        # encode the tag
        tag.SetAppData(Tag.doubleAppTag, struct.pack('>d',self.value))

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.doubleAppTag):
            raise ValueError, "double application tag required"

        # extract the data
        self.value = struct.unpack('>d',tag.tagData)[0]

    def __str__(self):
        return "Double(%g)" % (self.value,)

#
#   OctetString
#

class OctetString(Atomic):

    _appTag = Tag.octetStringAppTag

    def __init__(self, arg=None):
        self.value = ''

        if arg is None:
            pass
        elif isinstance(arg,Tag):
            self.Decode(arg)
        elif isinstance(arg,types.StringType):
            self.value = arg
        else:
            raise TypeError, "invalid constructor datatype"

    def Encode(self, tag):
        # encode the tag
        tag.SetAppData(Tag.octetStringAppTag, self.value)

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.octetStringAppTag):
            raise ValueError, "octet string application tag required"

        self.value = tag.tagData

    def __str__(self):
        return "OctetString(X'" + StringToHex(self.value) + "')"

#
#   CharacterString
#

class CharacterString(Atomic):

    _appTag = Tag.characterStringAppTag

    def __init__(self, arg=None):
        self.value = ''
        self.strEncoding = 0

        if arg is None:
            pass
        elif isinstance(arg,Tag):
            self.Decode(arg)
        elif isinstance(arg,types.StringType):
            self.value = arg
        else:
            raise TypeError, "invalid constructor datatype"

    def Encode(self, tag):
        # encode the tag
        tag.SetAppData(Tag.characterStringAppTag, chr(self.strEncoding)+self.value)

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.characterStringAppTag):
            raise ValueError, "character string application tag required"

        # extract the data
        self.strEncoding = tag.tagData[0]
        self.value = tag.tagData[1:]

    def __str__(self):
        return "CharacterString(%d," % (self.strEncoding,) + repr(self.value) + ")"

#
#   BitString
#

class BitString(Atomic):

    _appTag = Tag.bitStringAppTag
    bitNames = {}
    bitLen = 0

    def __init__(self, arg = None):
        self.value = [0] * self.bitLen

        if arg is None:
            pass
        elif isinstance(arg,Tag):
            self.Decode(arg)
        elif isinstance(arg,types.ListType):
            allInts = allStrings = True
            for elem in arg:
                allInts = allInts and ((elem == 0) or (elem == 1))
                allStrings = allStrings and self.bitNames.has_key(elem)

            if allInts:
                self.value = arg
            elif allStrings:
                for bit in arg:
                    bit = self.bitNames[bit]
                    if (bit < 0) or (bit > len(self.value)):
                        raise IndexError, "constructor element out of range"
                    self.value[bit] = 1
            else:
                raise TypeError, "invalid constructor list element(s)"
        else:
            raise TypeError, "invalid constructor datatype"

    def Encode(self, tag):
        # compute the unused bits to fill out the string
        _, used = divmod(len(self.value), 8)
        unused = used and (8 - used) or 0

        # start with the number of unused bits
        data = chr(unused)

        # build and append each packed octet
        bits = self.value + [0] * unused
        for i in range(0,len(bits),8):
            x = 0
            for j in range(0,8):
                x |= bits[i + j] << (7 - j)
            data += chr(x)

        # encode the tag
        tag.SetAppData(Tag.bitStringAppTag, data)

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.bitStringAppTag):
            raise ValueError, "bit string application tag required"

        # extract the number of unused bits
        unused = ord(tag.tagData[0])

        # extract the data
        data = []
        for c in tag.tagData[1:]:
            x = ord(c)
            for i in range(8):
                if (x & (1 << (7 - i))) != 0:
                    data.append( 1 )
                else:
                    data.append( 0 )

        # trim off the unused bits
        if unused:
            self.value = data[:-unused]
        else:
            self.value = data
            
    def __str__(self):
        # flip the bit names
        bitNames = {}
        for key, value in self.bitNames.iteritems():
            bitNames[value] = key

        # build a list of values and/or names
        valueList = []
        for value, index in zip(self.value,range(len(self.value))):
            if bitNames.has_key(index):
                if value:
                    valueList.append(bitNames[index])
                else:
                    valueList.append('!' + bitNames[index])
            else:
                valueList.append(str(value))

        # bundle it together
        return "BitString(" + ','.join(valueList) + ")"

    def __getitem__(self,bit):
        if isinstance(bit,types.IntType):
            pass
        elif isinstance(bit,types.StringType):
            if not self.bitNames.has_key(bit):
                raise IndexError, "unknown bit name '%s'" % (bit,)

            bit = self.bitNames[bit]
        else:
            raise TypeError, "bit index must be an integer or bit name"

        if (bit < 0) or (bit > len(self.value)):
            raise IndexError, "list index out of range"

        return self.value[bit]

    def __setitem__(self,bit,value):
        if isinstance(bit,types.IntType):
            pass
        elif isinstance(bit,types.StringType):
            if not self.bitNames.has_key(bit):
                raise IndexError, "unknown bit name '%s'" % (bit,)

            bit = self.bitNames[bit]
        else:
            raise TypeError, "bit index must be an integer or bit name"

        if (bit < 0) or (bit > len(self.value)):
            raise IndexError, "list index out of range"

        # funny cast to a bit
        self.value[bit] = value and 1 or 0

#
#   Enumerated
#

class Enumerated(Atomic):

    _appTag = Tag.enumeratedAppTag

    enumerations = {}
    _xlateTable = {}

    def __init__(self, arg=None):
        self.value = 0L

        # see if the class has a translate table
        if not self.__class__.__dict__.has_key('_xlateTable'):
            ExpandEnumerations(self.__class__)

        # initialize the object
        if arg is None:
            pass
        elif isinstance(arg, Tag):
            self.Decode(arg)
        elif isinstance(arg, types.IntType):
            if (arg < 0):
                raise ValueError, "unsigned integer required"

            # convert it to a string if you can
            try: self.value = self._xlateTable[arg]
            except KeyError: self.value = long(arg)
        elif isinstance(arg, types.LongType):
            if (arg < 0):
                raise ValueError, "unsigned integer required"

            # convert it to a string if you can
            try: self.value = self._xlateTable[arg]
            except KeyError: self.value = long(arg)
        elif isinstance(arg,types.StringType):
            if self._xlateTable.has_key(arg):
                self.value = arg
            else:
                raise ValueError, "undefined enumeration '%s'" % (arg,)
        else:
            raise TypeError, "invalid constructor datatype"

    def __getitem__(self, item):
        return self._xlateTable.get(item)

    def GetLong(self):
        if isinstance(self.value, types.LongType):
            return self.value
        elif isinstance(self.value, types.StringType):
            return long(self._xlateTable[self.value])
        else:
            raise TypeError, "%s is an invalid enumeration value datatype" % (type(self.value),)

    def keylist(self):
        """Return a list of names in order by value."""
        items = self.enumerations.items()
        items.sort(lambda a, b: cmp(a[1], b[1]))

        # last item has highest value
        rslt = [None] * (items[-1][1] + 1)

        # map the values
        for key, value in items:
            rslt[value] = key

        # return the result
        return rslt

    def __cmp__(self, other):
        """Special function to make sure comparisons are done in enumeration
        order, not alphabetic order."""
        # hoop jump it
        if not isinstance(other, self.__class__):
            other = self.__class__(other)

        # get the numeric version
        a = self.GetLong()
        b = other.GetLong()

        # now compare the values
        if (a < b):
            return -1
        elif (a > b):
            return 1
        else:
            return 0

    def Encode(self, tag):
        if isinstance(self.value, types.IntType):
            value = long(self.value)
        if isinstance(self.value, types.LongType):
            value = self.value
        elif isinstance(self.value, types.StringType):
            value = self._xlateTable[self.value]
        else:
            raise TypeError, "%s is an invalid enumeration value datatype" % (type(self.value),)

        # rip apart the number
        data = [ord(c) for c in struct.pack('>L',value)]

        # reduce the value to the smallest number of octets
        while (len(data) > 1) and (data[0] == 0):
            del data[0]

        # encode the tag
        tag.SetAppData(Tag.enumeratedAppTag, ''.join(chr(c) for c in data))

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.enumeratedAppTag):
            raise ValueError, "enumerated application tag required"

        # get the data
        rslt = 0L
        for c in tag.tagData:
            rslt = (rslt << 8) + ord(c)

        # convert it to a string if you can
        try: rslt = self._xlateTable[rslt]
        except KeyError: pass

        # save the result
        self.value = rslt

    def __str__(self):
        return "Enumerated(%s)" % (self.value,)

#
#   ExpandEnumerations
#

# translate lowers to uppers, keep digits, toss everything else
_ExpandTranslateTable = ''.join([c.isalnum() and c.upper() or '-' for c in [chr(cc) for cc in range(256)]])
_ExpandDeleteChars = ''.join([chr(cc) for cc in range(256) if not chr(cc).isalnum()])

def ExpandEnumerations(klass):
    # build a value dictionary
    xlateTable = {}
    for name, value in klass.enumerations.iteritems():
        # save the results
        xlateTable[name] = value
        xlateTable[value] = name

        # translate the name for a class const
        name = name.translate(_ExpandTranslateTable, _ExpandDeleteChars)

        # save the name in the class
        setattr(klass, name, value)

    # save the dictionary in the class
    setattr(klass, '_xlateTable', xlateTable)

#
#   Date
#

class Date(Atomic):

    _appTag = Tag.dateAppTag

    DONT_CARE = 255

    def __init__(self, arg=None, year=255, month=255, day=255, dayOfWeek=255):
        self.value = (year, month, day, dayOfWeek)

        if arg is None:
            pass
        elif isinstance(arg,Tag):
            self.Decode(arg)
        elif isinstance(arg, types.TupleType):
            self.value = arg
        else:
            raise TypeError, "invalid constructor datatype"

    def Now(self):
        tup = time.gmtime()

        self.value = (tup[0]-1900, tup[1], tup[2], tup[6] + 1)

        return self

    def CalcDayOfWeek(self):
        """Calculate the correct day of the week."""
        # rip apart the value
        year, month, day, dayOfWeek = self.value

        # make sure all the components are defined
        if (year != 255) and (month != 255) and (day != 255):
            today = time.mktime( (year + 1900, month, day, 0, 0, 0, 0, 0, -1) )
            dayOfWeek = time.gmtime(today)[6] + 1

        # put it back together
        self.value = (year, month, day, dayOfWeek)

    def Encode(self, tag):
        # encode the tag
        tag.SetAppData(Tag.dateAppTag, ''.join(chr(c) for c in self.value))

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.dateAppTag):
            raise ValueError, "date application tag required"

        # rip apart the data
        self.value = tuple(ord(c) for c in tag.tagData)

    def __str__(self):
        # rip it apart
        year, month, day, dayOfWeek = self.value

        rslt = "Date("
        if month == 255:
            rslt += "*/"
        else:
            rslt += "%d/" % (month,)
        if day == 255:
            rslt += "*/"
        else:
            rslt += "%d/" % (day,)
        if year == 255:
            rslt += "* "
        else:
            rslt += "%d " % (year + 1900,)
        if dayOfWeek == 255:
            rslt += "*)"
        else:
            rslt += ['','Mon','Tue','Wed','Thu','Fri','Sat','Sun'][dayOfWeek] + ")"

        return rslt

#
#   Time
#

class Time(Atomic):

    _appTag = Tag.timeAppTag

    DONT_CARE = 255

    def __init__(self, arg=None, hour=255, minute=255, second=255, hundredth=255):
        # put it together
        self.value = (hour, minute, second, hundredth)

        if arg is None:
            pass
        elif isinstance(arg,Tag):
            self.Decode(arg)
        elif isinstance(arg, types.TupleType):
            self.value = arg
        else:
            raise TypeError, "invalid constructor datatype"

    def Now(self):
        now = time.time()
        tup = time.gmtime(now)

        self.value = (tup[3], tup[4], tup[5], int((now - int(now)) * 100))

        return self

    def Encode(self, tag):
        # encode the tag
        tag.SetAppData(Tag.timeAppTag, ''.join(chr(c) for c in self.value))

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.timeAppTag):
            raise ValueError, "time application tag required"

        # rip apart the data
        self.value = tuple(ord(c) for c in tag.tagData)

    def __str__(self):
        # rip it apart
        hour, minute, second, hundredth = self.value

        rslt = "Time("
        if hour == 255:
            rslt += "*:"
        else:
            rslt += "%02d:" % (hour,)
        if minute == 255:
            rslt += "*:"
        else:
            rslt += "%02d:" % (minute,)
        if second == 255:
            rslt += "*."
        else:
            rslt += "%02d." % (second,)
        if hundredth == 255:
            rslt += "*)"
        else:
            rslt += "%02d)" % (hundredth,)

        return rslt

#
#   ObjectType
#

class ObjectType(Enumerated):
    enumerations = \
        { 'analog-input':0
        , 'analog-output':1
        , 'analog-value':2
        , 'binary-input':3
        , 'binary-output':4
        , 'binary-value':5
        , 'calendar':6
        , 'command':7
        , 'device':8
        , 'event-enrollment':9
        , 'file':10
        , 'group':11
        , 'loop':12
        , 'multi-state-input':13
        , 'multi-state-output':14
        , 'notification-class':15
        , 'program':16
        , 'schedule':17
        , 'averaging':18
        , 'multi-state-value':19
        , 'trend-log':20
        , 'life-safety-point':21
        , 'life-safety-zone':22
        , 'accumulator':23
        , 'pulse-converter':24
        }

ExpandEnumerations(ObjectType)

#
#   ObjectIdentifier
#

class ObjectIdentifier(Atomic):

    _appTag = Tag.objectIdentifierAppTag
    objectTypeClass = ObjectType

    def __init__(self, *args):
        self.value = ('analog-input', 0)

        if len(args) == 0:
            pass
        elif len(args) == 1:
            arg = args[0]
            if isinstance(arg, Tag):
                self.Decode(arg)
            elif isinstance(arg, types.IntType):
                self.SetLong(long(arg))
            elif isinstance(arg, types.LongType):
                self.SetLong(arg)
            elif isinstance(arg, types.TupleType):
                self.SetTuple(*arg)
            else:
                raise TypeError, "invalid constructor datatype"
        elif len(args) == 2:
            self.SetTuple(*args)
        else:
            raise ValueError, "invalid constructor parameters"

    def SetTuple(self, objType, objInstance):
        # allow a type name as well as an integer
        if isinstance(objType, types.IntType):
            try:
                # try and make it pretty
                objType = self.objectTypeClass()[objType]
            except KeyError:
                pass
        elif isinstance(objType, types.StringType):
            try:
                # make sure the type is known
                self.objectTypeClass()[objType]
            except KeyError:
                raise ValueError, "unrecognized object type '%s'" % (objType,)
        else:
            raise TypeError, "invalid datatype for objType"

        # pack the components together
        self.value = (objType, objInstance)

    def GetTuple(self):
        """Return the unsigned integer tuple of the identifier."""
        objType, objInstance = self.value

        if isinstance(objType, types.IntType):
            pass
        elif isinstance(objType, types.LongType):
            objType = int(objType)
        elif isinstance(objType, types.StringType):
            # turn it back into an integer
            objType = self.objectTypeClass()[objType]
        else:
            raise TypeError, "invalid datatype for objType"

        # pack the components together
        return (objType, objInstance)

    def SetLong(self, value):
        # suck out the type
        objType = (value >> 22) & 0x03FF
        
        # try and make it pretty
        objType = self.objectTypeClass()[objType] or objType

        # suck out the instance
        objInstance = value & 0x003FFFFF

        # save the result
        self.value = (objType, objInstance)

    def GetLong(self):
        """Return the unsigned integer representation of the identifier."""
        objType, objInstance = self.GetTuple()

        # pack the components together
        return long((objType << 22) + objInstance)

    def Encode(self, tag):
        # encode the tag
        tag.SetAppData(Tag.objectIdentifierAppTag, struct.pack('>L',self.GetLong()))

    def Decode(self, tag):
        if (tag.tagClass != Tag.applicationTagClass) or (tag.tagNumber != Tag.objectIdentifierAppTag):
            raise ValueError, "object identifier application tag required"

        # extract the data
        self.SetLong( struct.unpack('>L',tag.tagData)[0] )

    def __str__(self):
        # rip it apart
        objType, objInstance = self.value

        if isinstance(objType, types.StringType):
            typestr = objType
        elif objType < 0:
            typestr = "Bad %d" % (objType,)
        elif self.objectTypeClass._xlateTable.has_key(objType):
            typestr = self.objectTypeClass._xlateTable[objType]
        elif (objType < 128):
            typestr = "Reserved %d" % (objType,)
        else:
            typestr = "Vendor %d" % (objType,)
        return "ObjectIdentifier(%s,%d)" % (typestr, objInstance)

    def __hash__(self):
        return hash(self.value)

    def __cmp__(self, other):
        """Special function to make sure comparisons are done in enumeration
        order, not alphabetic order."""
        # hoop jump it
        if not isinstance(other, self.__class__):
            other = self.__class__(other)

        # get the numeric version
        a = self.GetLong()
        b = other.GetLong()

        # now compare the values
        if (a < b):
            return -1
        elif (a > b):
            return 1
        else:
            return 0

#
#   Application Tag Classes
#
#   This list is set in the Tag class so that the AppToObject
#   function can return one of the appliction datatypes.  It
#   can't be provided in the Tag class definition because the
#   classes aren't defined yet.
#

Tag._applicationTagClass = \
    [ Null, Boolean, Unsigned, Integer
    , Real, Double, OctetString, CharacterString
    , BitString, Enumerated, Date, Time
    , ObjectIdentifier, None, None, None
    ]
