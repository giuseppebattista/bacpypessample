#!/usr/bin/python

"""
Time Utilities
"""

import re
import types
import time as _time
import logging

from datetime import datetime, timedelta, tzinfo
import pytz

from debugging import Logging, function_debugging

# some debugging
_log = logging.getLogger(__name__)

# keep everything UTC if possible
UTC = pytz.utc

# we are Eastern
LocalTimeZone = pytz.timezone('US/Eastern')

#
#   _FixedOffset
#

class _FixedOffset(tzinfo, Logging):
    """Fixed offset in minutes east from UTC."""

    def __init__(self, offset, name):
        self.__offset = timedelta(minutes = offset)
        self.__name = name

    def utcoffset(self, dt):
        return self.__offset

    def tzname(self, dt):
        return self.__name

    def dst(self, dt):
        return timedelta(0)

    def __repr__(self):
        return '<FixedOffset %s>' % (self.__offset,)

#
#   AbsoluteTime
#

nowRE = re.compile("^now$", re.IGNORECASE)
todayRE = re.compile("^tod(a?(y?))$", re.IGNORECASE)
tomorrowRE = re.compile("^tom(o?(r?(r?(o?(w?)))))$", re.IGNORECASE)
yesterdayRE = re.compile("^yes(t?(e?(r?(d?(a?(y?))))))$", re.IGNORECASE)

dbre = re.compile( """^
(?P<year>\d+) - (?P<month>\d+) - (?P<day>\d+)     # all three pieces required
(\s+)?
( (?P<hour>\d+)
  ( :(?P<minute>\d+)
    ( :(?P<second>\d+)
        ([.](?P<microsecond>\d+))?
    )?
  )?
)?
$""", re.VERBOSE )

# '6/21/2006 16:03:36.157234'

user1re = re.compile( """^
( (?P<month>\d+) / (?P<day>\d+) (/ (?P<year>\d+))?    # month and day required, year optional
)?
(\s+)?
( (?P<hour>\d+)
  ( :(?P<minute>\d+)
    ( :(?P<second>\d+)
        ([.](?P<microsecond>\d+))?
    )?
  )?
)?
$""", re.VERBOSE )

# '21-Jun-2006 16:03:36.157234'

user2re = re.compile( """^
( (?P<day>\d+)                          # day and month required, year optional
    - (?P<month>(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec))
    (- (?P<year>\d+))?
)?
(\s+)?
( (?P<hour>\d+)
  ( :(?P<minute>\d+)
    ( :(?P<second>\d+)
        ([.](?P<microsecond>\d+))?
    )?
  )?
)?
$""", re.VERBOSE | re.IGNORECASE )

# 'Jun 21 2006 16:03:36.157234'

user3re = re.compile( """^
( (?P<month>(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec))
    ((\s+)? (?P<day>\d+))?              # month required,  day and year optional
    ((\s+)? (?P<year>\d+))?
)?
(\s+)?
( (?P<hour>\d+)
  ( :(?P<minute>\d+)
    ( :(?P<second>\d+)
        ([.](?P<microsecond>\d+))?
    )?
  )?
)?
$""", re.VERBOSE | re.IGNORECASE )

# 'Wed, 21 Jun 2006 16:03:36 GMT'

webre = re.compile( """^
(?P<dow>(sun|mon|tue|wed|thu|fri|sat))
[,]
\s+
(?P<day>\d+)
(?:\s+|[-])
(?P<month>(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec))
(?:\s+|[-])
(?P<year>\d+)
\s+
(?P<hour>\d+)
:(?P<minute>\d+)
:(?P<second>\d+)
\s+
GMT
$""", re.VERBOSE | re.IGNORECASE )

# YYYY-MM-DDTHH:MM:SS+HH:MM

isore = re.compile( """^
(?P<year>\d+) - (?P<month>\d+) - (?P<day>\d+)     # all three pieces required
T
(?P<hour>\d+)
:
(?P<minute>\d+)
:
(?P<second>\d+)
([.](?P<microsecond>\d+))?
( (?P<z>Z) |
  (?P<offhour>[ +-]\d+):(?P<offminute>\d+)        # GMT offset (signed)
)?
$""", re.VERBOSE )

dayNames = ['sun','mon','tue','wed','thu','fri','sat']
monthNames = ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']

class AbsoluteTime(datetime, Logging):

    def __new__(cls, *args, **kwargs):
        """Create a new datetime."""
        AbsoluteTime._debug("__new__ %r %r", args, kwargs)

        if (len(args) == 0) or (args[0] == ''):
            # no parameters is current time
            t = _time.time()
            ms = int((t - int(t)) * 1000000)
            year, month, day, hour, minute, second = _time.gmtime(t)[:6]
            d = {'hour':hour, 'minute':minute, 'second':second, 'microsecond':ms, 'tzinfo':UTC}
            
        elif (len(args) == 3):
            year, month, day = args
            d = {'hour':0, 'minute':0, 'second':0, 'microsecond':0, 'tzinfo':UTC}
            
        elif (len(args) == 6):
            year, month, day, hour, minute, second = args
            d = {'hour':0, 'minute':0, 'second':0, 'microsecond':0, 'tzinfo':UTC}
            
        elif type(args[0]) == types.FloatType:
            # a floating point parameter is from time.time()
            t = args[0]
            ms = int((t - int(t)) * 1000000)
            year, month, day, hour, minute, second = _time.gmtime(t)[:6]
            d = {'hour':hour, 'minute':minute, 'second':second, 'microsecond':ms, 'tzinfo':UTC}
            
        elif type(args[0]) in (types.IntType, types.LongType):
            # an integer is the same as float
            year, month, day, hour, minute, second = _time.gmtime(args[0])[:6]
            d = {'hour':hour, 'minute':minute, 'second':second, 'microsecond':0, 'tzinfo':UTC}
            
        elif isinstance(args[0], datetime):
            year, month, day, hour, minute, second = args[0].timetuple()[:6]
            microsecond = args[0].microsecond
            if args[0].tzinfo:
                tzinfo = args[0].tzinfo
            else:
                tzinfo = UTC
            d = {'hour':hour, 'minute':minute, 'second':second, 'microsecond':microsecond, 'tzinfo':tzinfo}

        elif type(args[0]) == types.StringType:
            d = {}
                
            #default to current values if not supplied
            year, month, day = _time.localtime()[:3]

            if nowRE.match(args[0]):
                t = _time.time()
                ms = int((t - int(t)) * 1000000)
                year, month, day, hour, minute, second = _time.gmtime(t)[:6]
                d = {'hour':hour, 'minute':minute, 'second':second, 'microsecond':ms, 'tzinfo':UTC}
                
            elif todayRE.match(args[0]):
                pass
                
            elif tomorrowRE.match(args[0]):
                tomorrow = datetime(year,month,day) + timedelta(days=1)
                year, month, day = tomorrow.year, tomorrow.month, tomorrow.day
                
            elif yesterdayRE.match(args[0]):
                yesterday = datetime(year,month,day) - timedelta(days=1)
                year, month, day = yesterday.year, yesterday.month, yesterday.day
                
            else:
                for re in (dbre, webre, isore):
                    m = re.match(args[0])
                    if m:
                        d['tzinfo'] = UTC
                        break
                else:
                    for re in (user1re, user2re, user3re):
                        m = re.match(args[0])
                        if m:
                            break
                    else:
                        raise ValueError, "invalid absolute time format"
                    
                # extract the stuff that was named
                gd = m.groupdict()
                AbsoluteTime._debug("    - gd: %r", gd)

                if gd['year']:
                    year = int(gd['year'])
                    if (year < 100):
                        if (year > 50):
                            year += 1900
                        else:
                            year += 2000
                if gd['month']:
                    try:
                        month = int(gd['month'])
                    except:
                        month = monthNames.index(gd['month'].lower()) + 1
                if gd['day']:
                    day = int(gd['day'])
                    if (not gd['year']) and (day > 31):
                        year = day
                        if (year < 100):
                            if (year > 50):
                                year += 1900
                            else:
                                year += 2000
                        day = 1
                else:
                    day = 1

                if gd['hour']:
                    d['hour'] = int(gd['hour'])
                if gd['minute']:
                    d['minute'] = int(gd['minute'])
                if gd['second']:
                    d['second'] = int(gd['second'])
                if gd.get('microsecond', None):
                    d['microsecond'] = int((gd['microsecond'] + '000000')[:6])

                if gd.get('z', None):
                    pass
                elif gd.get('offhour', None):
                    offhour = int(gd['offhour'])
                    offminute = int(gd['offminute'])
                    utcoffset = offhour * 60 + offminute
                    AbsoluteTime._debug("    - utcoffset: %r", utcoffset)

                    if utcoffset != 0:
                        d['tzinfo'] = _FixedOffset(utcoffset, "(fixed)")
        else:
            raise TypeError, "invalid argument type"

        # allow keyword arguments to override defaults
        d.update(kwargs)
        
        # no timezone means naive date and time
        if 'tzinfo' not in d:
            try:
                # make a naive datetime object
                naivedt = datetime(year, month, day, **d)
                AbsoluteTime._debug("    - naivedt: %r", naivedt)
                    
                # attempt to localize it
                localdt = LocalTimeZone.localize(naivedt)
                AbsoluteTime._debug("    - localdt: %r", localdt)
                    
            except IndexError:
                # IndexError appears to be thrown if the naivedt can't be localized
                raise ValueError, "invalid time"

            # the tzinfo might not be the same as LocalTimeZone
            d['tzinfo'] = localdt.tzinfo

        AbsoluteTime._debug("    - __new__: %r %r", (year,month,day), d)

        # now forward the creation along
        return apply( datetime.__new__, (cls,year,month,day), d )

    def __str__(self):
        """Return a string version of the time as if it was local time."""
        # start with the normal stuff
        rslt = self.astimezone(LocalTimeZone).strftime("%d-%b-%Y %H:%M:%S")

        # add microseconds
        if self.microsecond:
            rslt = rslt + (".%06d" % self.microsecond).rstrip('0')

        # fini
        return rslt

    def __add__(self, secs):
        """Return a new time offset by seconds."""
        if isinstance(secs, DeltaTime):
            secs = float(secs)
        if isinstance(secs, int) or isinstance(secs, long):
            secs = float(secs)
        if not isinstance(secs, float):
            raise TypeError, "operand must be an int, float, or DeltaTime"

        return AbsoluteTime(self.utctime() + secs)

    def __sub__(self, secs):
        """Return a new time offset by seconds."""
        if isinstance(secs, AbsoluteTime):
            return DeltaTime(self.utctime() - secs.utctime())
        elif isinstance(secs, DeltaTime):
            secs = float(secs)
        if isinstance(secs, int) or isinstance(secs, long):
            secs = float(secs)
        if not isinstance(secs, float):
            raise TypeError, "operand must be an int, float, or DeltaTime"

        return AbsoluteTime(self.utctime() - secs)

    def strftime(self, *args):
        """Format the time as if it was local."""
        AbsoluteTime._debug("strftime %r", args)
        if self.tzinfo == LocalTimeZone:
            AbsoluteTime._debug("    - apply directly")
            return apply( datetime.strftime, (self,)+args )
        else:
            AbsoluteTime._debug("    - convert to LocalTimeZone")
            return apply( self.astimezone(LocalTimeZone).strftime, args )

#    def isoformat(self):
#        """Format the time."""
#        if (self.tzinfo != LocalTimeZone):
#            return self.astimezone(LocalTimeZone).isoformat()
#        else:
#            return datetime.isoformat(self)
            
    def gmtime(self):
        """ Return the tuple (like time.gmtime()) as if it was UTC. """
        AbsoluteTime._debug("gmtime")
        rslt = datetime.utctimetuple(self)
        AbsoluteTime._debug("    - rslt: %r", rslt)

        return rslt

    def utctime(self):
        """ Return the time like time.time() and include microseconds. Note 
        that time.mktime() RETURNS IT IN THE LOCAL TIME ZONE, therefore,
        time.mktime(time.gmtime(x)) != x.  Sheesh! """
        now = _time.mktime(self.astimezone(LocalTimeZone).timetuple())
        now += self.microsecond / 1000000.0
        return now

    def __int__(self):
        return int(self.utctime())
        
    def __float__(self):
        return self.utctime()
        
    def datetime(self):
        """ Return the time as a datetime, includes microseconds. """
        return apply( datetime, self.utctimetuple()[:6] + (self.microsecond,) )

    def dbstr(self):
        """ Return a formatted string for a database, make sure it's UTC. """
        return "%04d-%02d-%02d %02d:%02d:%02d" % self.utctimetuple()[:6]

    def webstr(self):
        """ Return a formatted string for an HTTP header, make sure it's UTC. """
        return _time.strftime("%a, %d-%b-%Y %H:%M:%S GMT",self.gmtime())

    def sameDayAs(self, other):
        """ Return true iff the two dates are on the same day. Used to simplify
        the presentation of timestamps if the context is relatively clear. """
        thisday = self.astimezone(LocalTimeZone).timetuple()[0:3]
        thatday = other.astimezone(LocalTimeZone).timetuple()[0:3]
        return thisday == thatday

#
#   DeltaTime
#

deltare = re.compile( """^
( (?P<days>\d+) (?:\s+|-) (?:days?,\s+)? )?     # days are optional and must be separated by a dash or whitespace
( ( (?P<hours>\d+) : )? (?P<minutes>\d+) : )?   # if hours are given, minutes must also be
(?P<seconds>\d+)                                # seconds are required
([.] (?P<microseconds>\d+) )?                   # microseconds are optional
$""", re.VERBOSE )

class DeltaTime(timedelta):

    def __new__(cls,*args,**kwargs):
        """Create a new datetime."""
        dict = {}

        if len(args) == 0:
            # no parameters is zero
            pass
        elif type(args[0]) == types.IntType:
            # an integer parameter is in seconds
            dict['seconds'] = args[0]
            
        elif type(args[0]) == types.FloatType:
            # a floating point parameter is in seconds
            dict['seconds'] = args[0]
            
        elif isinstance(args[0],timedelta):
            days = args[0].days
            seconds = args[0].seconds
            microseconds = args[0].microseconds
            dict = {'days':days, 'seconds':seconds, 'microseconds':microseconds}
            
        elif type(args[0]) == types.StringType:
            # a string is from a database
            m = deltare.match(args[0])
            if not m:
                raise ValueError, "invalid deltatime format"
            gd = m.groupdict()
            if gd['microseconds']:
                gd['microseconds'] = (gd['microseconds'] + '000000')[:6]

            for i in gd:
                if gd[i]: dict[i] = int(gd[i])
        else:
            raise TypeError, "invalid argument type"

        AbsoluteTime._debug("    - dict: %r", dict)

        # now forward the creation along
        return apply( timedelta.__new__, (cls,), dict )

    def __int__(self):
        return (self.days * 86400) + self.seconds
        
    def __float__(self):
        return (self.days * 86400.0) + self.seconds + (self.microseconds / 1000000.0)

#
#   SmartTimeFormat
#

@function_debugging
def SmartTimeFormat(when, wrt):
    """Format the time 'when' with respect to the time 'wrt'."""
    SmartTimeFormat._debug("SmartTimeFormat %r %r", when, wrt)

    # check the time zone
    if when.tzinfo == UTC:
        when = when.astimezone(LocalTimeZone)
        SmartTimeFormat._debug("    - when remapped: %r", when)
    if wrt.tzinfo == UTC:
        wrt = wrt.astimezone(LocalTimeZone)
        SmartTimeFormat._debug("    - wrt remapped: %r", wrt)

    # look for matching days
    dfmt = None
    if (when.month != wrt.month) or (when.day != wrt.day) or (when.year != wrt.year):
        dfmt = "%d-%b-%Y"
#    if (when.year != wrt.year):
#        dfmt += "-%Y"    

    # look for non-zero time
    tfmt = None
    if (when.hour != 0) or (when.minute != 0) or (when.second != 0):
        tfmt = "%H:%M"
    if (when.second != 0):
        tfmt += ":%S"

    # build the format string
    if dfmt:
        if tfmt:
            fmt = dfmt + ' ' + tfmt
        else:
            fmt = dfmt
    else:
        if tfmt:
            fmt = tfmt
        else:
            # default for 00:00:00 on same day
#           fmt = "%d-%b"
            fmt = "%d-%b-%Y"
    SmartTimeFormat._debug("    - fmt: %r", fmt)

    # format the time
    rslt = when.strftime(fmt)
    SmartTimeFormat._debug("    - rslt: %r", rslt)

    return rslt

#
#   For these function definitions, see:
#
#       <http://www.phys.uu.nl/~vgent/calendar/isocalendar.htm>
#
#   The ISO calendar year consists either of 52 weeks (i.e. 364 days, the
#   "short" years) or 53 weeks (i.e. 371 days, the "long" years).
#

def _g(y):
    return (y - 100) / 400 - (y - 102) / 400

def _h(y):
    return (y - 200) / 400 - (y - 199) / 400

def _f(y):
    return 5 * y + 12 - 4 * ((y / 100) - (y / 400)) + _g(y) + _h(y)

def isLongYear(y):
    """True iff the year has 53 ISO calendar weeks."""
    return (_f(y) % 28) < 5

def isShortYear(y):
    """True iff the year has 52 ISO calendar weeks."""
    return (_f(y) % 28) > 4

#
#   OrdinalBase
#

class OrdinalBase(Logging):

    def toOrdinal(self, when):
        OrdinalBase._debug("toOrdinal %r", when)
        raise NotImplementedError, "%s.toOrdinal() not implemented" % (self.__class__.__name__,)

    def fromOrdinal(self, when):
        OrdinalBase._debug("fromOrdinal %r", when)
        raise NotImplementedError, "%s.fromOrdinal() not implemented" % (self.__class__.__name__,)

    def toRange(self, when, scale=1):
        OrdinalBase._debug("toRange %r scale=%r", when, scale)
        raise NotImplementedError, "%s.toOrdinal() not implemented" % (self.__class__.__name__,)

#
#   OrdinalHour
#

class OrdinalHour(OrdinalBase, Logging):

    def toOrdinal(self, when):
        OrdinalHour._debug("toOrdinal %r", when)

        if not when.tzinfo:
            when = LocalTimeZone.localize(when)
        elif when.tzinfo is not LocalTimeZone:
            when = when.astimezone(LocalTimeZone)

        secs = _time.mktime(when.timetuple())

        return (int(secs) / 3600)

    def fromOrdinal(self, when):
        OrdinalHour._debug("fromOrdinal %r", when)

        when = LocalTimeZone.localize(datetime.fromtimestamp(when * 3600))
        return AbsoluteTime(when)

    def toRange(self, when, scale=1):
        OrdinalHour._debug("toRange %r scale=%r", when, scale)

        # the datetime objects constructed by fromtimestamp() are
        # naive, they have no tzinfo, and therefore need to be 
        # localized
        start = LocalTimeZone.localize(datetime.fromtimestamp(when * 3600))
        end = LocalTimeZone.localize(datetime.fromtimestamp((when + scale) * 3600))

        # now morph these into AbsoluteTime objects for more features
        start = AbsoluteTime(start)
        end = AbsoluteTime(end)

        return (start, end)

# there is only one
OrdinalHour = OrdinalHour()

#
#   OrdinalDay
#

class OrdinalDay(OrdinalBase, Logging):

    def toOrdinal(self, when):
        OrdinalDay._debug("toOrdinal %r", when)

        if not when.tzinfo:
            when = LocalTimeZone.localize(when)
        elif when.tzinfo is not LocalTimeZone:
            when = when.astimezone(LocalTimeZone)

        return when.toordinal()

    def fromOrdinal(self, when):
        OrdinalDay._debug("fromOrdinal %r", when)

        when = LocalTimeZone.localize(datetime.fromordinal(when))
        return AbsoluteTime(when)

    def toRange(self, when, scale=1):
        OrdinalDay._debug("toRange %r scale=%r", when, scale)

        # the datetime objects constructed by fromordinal() are
        # naive, they have no tzinfo, and therefore need to be 
        # localized
        start = LocalTimeZone.localize(datetime.fromordinal(when))
        end = LocalTimeZone.localize(datetime.fromordinal(when + scale))

        # now morph these into AbsoluteTime objects for more features
        start = AbsoluteTime(start)
        end = AbsoluteTime(end)

        return (start, end)

# there is only one
OrdinalDay = OrdinalDay()

#
#   OrdinalWeek
#
#   The first week (ordinal 0) is the first week of 1-Jan-1970, but starts
#   earlier since that is a Thursday and ISO calendar weeks start on a Monday.
#

_ordinalBaseDate = datetime(1969, 12, 29)
_ordinalBase = _ordinalBaseDate.toordinal()

class OrdinalWeek(OrdinalBase, Logging):

    def toOrdinal(self, when):
        OrdinalWeek._debug("toOrdinal %r", when)

        return (OrdinalDay.toOrdinal(when) - _ordinalBase) / 7

    def fromOrdinal(self, when):
        OrdinalWeek._debug("fromOrdinal %r", when)

        when = when * 7 + _ordinalBase
        when = LocalTimeZone.localize(datetime.fromordinal(when))
        return AbsoluteTime(when)

    def toRange(self, when, scale=1):
        OrdinalWeek._debug("toRange %r scale=%r", when, scale)

        # calculate the ISO ordinal number for the day
        wstart = when * 7 + _ordinalBase

        # see OrdinalDayRange for naive datetimes
        start = LocalTimeZone.localize(datetime.fromordinal(wstart))
        end = LocalTimeZone.localize(datetime.fromordinal(wstart + (7 * scale)))

        # now morph these into AbsoluteTime objects for more features
        start = AbsoluteTime(start)
        end = AbsoluteTime(end)

        return (start, end)

# there is only one
OrdinalWeek = OrdinalWeek()

#
#   OrdinalMonth
#

class OrdinalMonth(OrdinalBase, Logging):

    def toOrdinal(self, when):
        OrdinalMonth._debug("toOrdinal %r", when)

        if not when.tzinfo:
            when = LocalTimeZone.localize(when)
        elif when.tzinfo is not LocalTimeZone:
            when = when.astimezone(LocalTimeZone)

        return (when.year * 12) + (when.month - 1)

    def fromOrdinal(self, when):
        OrdinalMonth._debug("fromOrdinal %r", when)

        year, month = when / 12, (when % 12) + 1
        when = LocalTimeZone.localize(datetime(year, month, 1))
        return AbsoluteTime(when)

    def toRange(self, when, scale=1):
        OrdinalMonth._debug("toRange %r scale=%r", when, scale)

        # special calculations for larger scales
        thisWhen, nextWhen = when, when + scale

        # split the number into components
        thisYear, thisMonth = thisWhen / 12, (thisWhen % 12) + 1
        nextYear, nextMonth = nextWhen / 12, (nextWhen % 12) + 1

        # the datetime objects constructed by fromordinal() are
        # naive, they have no tzinfo, and therefore need to be 
        # localized
        start = LocalTimeZone.localize(datetime(thisYear, thisMonth, 1))
        end = LocalTimeZone.localize(datetime(nextYear, nextMonth, 1))

        # now morph these into AbsoluteTime objects for more features
        start = AbsoluteTime(start)
        end = AbsoluteTime(end)

        return (start, end)

# there is only one
OrdinalMonth = OrdinalMonth()

#
#   OrdinalYear
#

class OrdinalYear(OrdinalBase, Logging):

    def toOrdinal(self, when):
        OrdinalYear._debug("toOrdinal %r", when)

        if not when.tzinfo:
            when = LocalTimeZone.localize(when)
        elif when.tzinfo is not LocalTimeZone:
            when = when.astimezone(LocalTimeZone)

        return when.year

    def fromOrdinal(self, when):
        OrdinalYear._debug("fromOrdinal %r", when)

        when = LocalTimeZone.localize(datetime(when, 1, 1))
        return AbsoluteTime(when)

    def toRange(self, when, scale=1):
        OrdinalYear._debug("toRange %r scale=%r", when, scale)

        # the datetime objects naive, they have no tzinfo, and
        # therefore need to be localized
        start = LocalTimeZone.localize(datetime(when, 1, 1))
        end = LocalTimeZone.localize(datetime(when + scale, 1, 1))

        # now morph these into AbsoluteTime objects for more features
        start = AbsoluteTime(start)
        end = AbsoluteTime(end)

        return (start, end)

# there is only one
OrdinalYear = OrdinalYear()

