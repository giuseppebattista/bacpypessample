
import sys
import cmd
import traceback
import gc
import types

from BACpypes.CommunicationsCore import Thread
if ("--debugThread" in sys.argv):
    print "imported", Thread

from BACpypes.PDU import Address, GlobalBroadcast
from BACpypes.PrimativeData import Real
from BACpypes.Application import BIPSimpleApplication
from BACpypes.Object import LocalDeviceObject, AnalogInputObject, Property, RegisterObjectType

from BACpypes.APDU import UnconfirmedRequestPDU, WhoIsRequest, IAmRequest, ReadPropertyRequest

# some debugging
_debug = 0

# make a device object from a configuration file
from ConfigParser import ConfigParser
config = ConfigParser()
config.read('BACpypes.ini')

thisDevice = \
    LocalDeviceObject( objectName=config.get('BACpypes','objectName')
        , objectIdentifier=config.getint('BACpypes','objectIdentifier')
        , maxApduLengthAccepted=config.getint('BACpypes','maxApduLengthAccepted')
        , segmentationSupported=config.get('BACpypes','segmentationSupported')
        , vendorIdentifier=config.getint('BACpypes','vendorIdentifier')
        )

#
#   MyApplication
#

class MyApplication(BIPSimpleApplication):

    def __init__(self):
        BIPSimpleApplication.__init__(self, thisDevice, config.get('BACpypes','address'))
        
    def Request(self, apdu):
        print "MyApplication.Request:", apdu
        apdu.DebugContents()
        print
        
        BIPSimpleApplication.Request(self, apdu)

    def Indication(self, apdu):
        # cut down on debug messages on busy networks
        if not isinstance(apdu, UnconfirmedRequestPDU):
            print "MyApplication.Indication:", apdu
            apdu.DebugContents()
            print
            
        BIPSimpleApplication.Indication(self, apdu)

    def Response(self, apdu):
        print "MyApplication.Response:", apdu
        apdu.DebugContents()
        print
        
        BIPSimpleApplication.Response(self, apdu)

    def Confirmation(self, apdu):
        print "MyApplication.Confirmation:", apdu
        apdu.DebugContents()
        print

# make a simple application
myApp = MyApplication()

#
#   Console
#

class Console(cmd.Cmd):

    def __init__(self):
        cmd.Cmd.__init__(self)
        self.prompt = "> "

        # gc counters
        self.type2count = {}
        self.type2all = {}
        
    #-----
    
    def do_whois(self, args):
        """whois [ <addr>] [ <lolimit> <hilimit> ]"""
        args = args.split()
        if _debug:
            print "do_whois", args
            
        try:
            # build a request
            request = WhoIsRequest()
            if (len(args) == 1) or (len(args) == 3):
                request.pduDestination = Address(args[0])
                del args[0]
            else:
                request.pduDestination = GlobalBroadcast()

            if len(args) == 2:
                loLimit = int(args[0])
                hiLimit = int(args[1])

                request.deviceInstanceRangeLowLimit = int(args[0])
                request.deviceInstanceRangeHighLimit = int(args[1])

            # give it to the application
            myApp.Request(request)
            
        except Exception, e:
            print e.__class__, ":", e
            traceback.print_exc(file=sys.stdout)
            print

    def help_whois(self):
        print self.do_whois.__doc__

    def do_iam(self, args):
        """iam"""
        args = args.split()
        if _debug:
            print "do_iam", args

        try:
            # build a request
            request = IAmRequest()
            request.pduDestination = GlobalBroadcast()
            
            # set the parameters from the device object
            request.iAmDeviceIdentifier = thisDevice.objectIdentifier
            request.maxAPDULengthAccepted = thisDevice.maxApduLengthAccepted
            request.segmentationSupported = thisDevice.segmentationSupported
            request.vendorID = thisDevice.vendorIdentifier
            
            # give it to the application
            myApp.Request(request)
            
        except Exception, e:
            print e.__class__, ":", e
            traceback.print_exc(file=sys.stdout)
            print

    def help_iam(self):
        print self.do_iam.__doc__

    #-----
    
    def do_read(self, args):
        """read <addr> <type> <inst> <prop> [ <indx> ]"""
        args = args.split()
        if _debug:
            print "do_read", args

        try:
            addr, objType, objInst, propId = args[:4]
            objInst = int(objInst)

            # build a request
            request = ReadPropertyRequest(objectIdentifier=(objType, objInst), propertyIdentifier=propId)
            request.pduDestination = Address(addr)
            if len(args) == 5:
                request.propertyArrayIndex = int(args[4])
                
            # give it to the application
            myApp.Request(request)
            
        except Exception, e:
            print e.__class__, ":", e
            traceback.print_exc(file=sys.stdout)
            print

    def help_read(self):
        print self.do_read.__doc__

    #-----
    
    def do_gc(self, args):
        """gc"""
        
        # snapshot of counts
        type2count = {}
        type2all = {}
        for o in gc.get_objects():
            if type(o) == types.InstanceType:
                type2count[o.__class__] = type2count.get(o.__class__,0) + 1
                type2all[o.__class__] = type2all.get(o.__class__,0) + sys.getrefcount(o)
            
        # count the things that have changed
        ct = [ ( t.__module__
            , t.__name__
            , type2count[t]
            , type2count[t] - self.type2count.get(t,0)
            , type2all[t] - self.type2all.get(t,0)
            ) for t in type2count.iterkeys()
            ]
            
        # ready for the next time
        self.type2count = type2count
        self.type2all = type2all
        
        fmt = "%-30s %-30s %6s %6s %6s"
        print fmt % ("Module", "Type", "Count", "dCount", "dRef")
        
        # sorted by count
        ct.sort(lambda x, y: cmp(y[2], x[2]))
        for i in range(10):
            m, n, c, delta1, delta2 = ct[i]
            print fmt % (m, n, c, delta1, delta2)
        print
            
        print fmt % ("Module", "Type", "Count", "dCount", "dRef")
        
        # sorted by module and class
        ct.sort()
        for m, n, c, delta1, delta2 in ct:
            if delta1 or delta2:
                print fmt % (m, n, c, delta1, delta2)
        print
            
    def help_gc(self):
        print self.do_gc.__doc__

    #-----
    
    def do_hist(self, args):
        """Print a list of commands that have been entered."""
        print self._hist

    def help_hist(self):
        print self.do_hist.__doc__

    def do_exit(self, args):
        """Exits from the console."""
        return -1

    def help_exit(self):
        print self.do_exit.__doc__

    #-----
    
    def do_EOF(self, args):
        """Exit on system end of file character"""
        return self.do_exit(args)

    def do_shell(self, args):
        """Pass command to a system shell when line begins with '!'"""
        os.system(args)

    def do_help(self, args):
        """Get help on commands
        'help' or '?' with no arguments prints a list of commands for which help is available
        'help <command>' or '? <command>' gives help on <command>
        """
        ## The only reason to define this method is for the help text in the doc string
        cmd.Cmd.do_help(self, args)

    ## Override methods in Cmd object ##
    def preloop(self):
        """Initialization before prompting user for commands.
        Despite the claims in the Cmd documentaion, Cmd.preloop() is not a stub.
        """
        cmd.Cmd.preloop(self)   ## sets up command completion
        self._hist    = []      ## No history yet
        self._locals  = {}      ## Initialize execution namespace for user
        self._globals = {}

    def postloop(self):
        """Take care of any unfinished business.
        Despite the claims in the Cmd documentaion, Cmd.postloop() is not a stub.
        """
        cmd.Cmd.postloop(self)   ## Clean up command completion
        print "Exiting..."

    def precmd(self, line):
        """ This method is called after the line has been input but before
            it has been interpreted. If you want to modifdy the input line
            before execution (for example, variable substitution) do it here.
        """
        self._hist += [ line.strip() ]
        return line

    def postcmd(self, stop, line):
        """If you want to stop the console, return something that evaluates to true.
        If you want to do some post command processing, do it here.
        """
        return stop

    def emptyline(self):
        """Do nothing on empty input line"""
        pass

    def default(self, line):
        """Called on an input line when the command prefix is not recognized.
        In that case we execute the line as Python code.
        """
        try:
            exec(line) in self._locals, self._globals
        except Exception, e:
            print e.__class__, ":", e
            print

# start the threads
Thread.StartThreads()

# create a console and let it run
Console().cmdloop()

# halt
Thread.HaltThreads()
