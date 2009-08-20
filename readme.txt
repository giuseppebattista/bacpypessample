Expand the archive into a directory. 
Edit the BACpypes.ini file to have the settings your test
device should have on your network, and give it a shot.

BACpypes_001.py  - dump headers of received packets
BACpypes_002.py  - collect counts of Who-Is and I-Am messages
BACpypes_003.py  - count Who-Has and I-Have messages
BACpypes_004.py  - add an analog-input object with a random
                       present value
BACpypes_005.py  - console application that can generate Who-Is,
                       I-Am, and Read-Property requests and
                       dump the responses

The whole package is based on a set of small components that you can put
together to form whatever part of a stack you would like, or just use
the encoding and decoding functionality.  This design started back while
I was working with VTS and struggling with the scripting language.
After a long time and many re-designs, I'm quite happy with the way it
is turning out (with a few warts, hacks, and obfuscations).

There is one important theme for the code: the Client/Server pattern,
and the ServiceAccessPoint/ApplicationServiceElement connections.  These
classes are defined in CommunicationsCore.py.

The API is closely related to the text in the standard.  When a Client
instance calls Request() with some arguments, the Server instance it is
bound gets its Indication() called with the same arguments.  When the
server is done doing what it needs to do, it calls Response() and the
client has its Confirmation() called.

These things are put together into a "stack" of objects where servers
are at the bottom and clients are at the top.  The objects in the middle
inherit from both Client and Server and do things to parameters on the
way "down" (from client to server) and "up" (from server to client) the
stack.

A ServiceAccessPoint (SAP) is very similar, but works "horizontally" to
the rest of the stack.  ApplicationServiceElement (ASE) objects are
bound to SAP objects in a symbiotic version of the client/server pattern.

Take the network service layer of BACnet.  Most of the packets travel up
and down the stack through the layer, but there is also the possibility
of having a network application layer.  For example, a network ASE would
call Request() for Who-Is-Router-To-Network.  This message is
interesting because it is a transactionless service, the
I-Am-Router-To-Network messages may come in at any time.  Therefore
these responses are presented to the application via its Indication()
function, not the Confirmation() function.

The BACnet application layer is simpler since there are things that are
confirmed services.  When an ASE calls Request() with some
ConfirmedServicePDU Confirmation() will get called with the result,
which could be a simple or complex ack, error, or abort.

The next thing to be aware of is 'Encode' and 'Decode'.  Without generic
functions like C++ where I could say "a >> b", I needed a standard for
which object is doing the work, and which one is the buffer.

I decided that in 'a.Encode(b)' then 'a' is the thing that has knowledge
of encoding itself into 'b', and for 'a.Decode(b)' then 'a' has the
reflexive knowledge of looking at the contents of 'b' and figuring out
how to set its properties/parameters appropriately.

WARNING: for both Encode() and Decode(), 'b' is modified.  This makes
sense for Encode() since 'b' should be considered a buffer of some kind,
but it would be nicer if Decode() didn't modify 'b'.  It made it easy
and a little shorter to code, but it could trip you up.

That's what comes off the top of my head.  Before the next release I
would like all of the BaseTypes reviewed and brought up to snuff (and
sadly they can't be in the same order as the standard because of forward
references), and likewise all of the APDU's to have all their
appropriate Sequence/SequenceOf stuff defined.  Oh, and all of the
object types in Object.py with appropriate datatypes.

Unit testing would be cool too!

There are some warts, like the fact that you can't create more than one
application layer object, so you can't set up a VLAN and fling packets
between applications, but that will have to wait until I do some more
testing with the networking layer (which sucks because that feature
would help test the network layer...sigh).

Joel Bender

Frequently Asked Questions (FAQ)
--------------------------------
Q-1: Is the ObjectName the same as Device Name?

A-1: Yes, more formally it is the object name of the device object.  BACnet
devices have one and only one instance of a device object, so that can
be considered the device name.

Q-2: What is the Address format?

A-2: It is address/mask:port, so your address should be 192.268.1.100/24
because your network mask is probably 255.255.255.0 and the port
defaults to 47808.

It uses the "/24" part to create an appropriate broadcast address (in
this case it will be 129.168.1.255) and open an additional socket
listening for similar broadcasts from other devices.

Q-3: Is the ObjectIdentifier the same as the Device Instance Number? or
is it a MAC Address or something?

A-3: Yes, the objectIdentifier is the device instance number.  To be
consistent it should have been (device, 12345) but in the case of the
BACpypes.ini file it only has properties of the device object, and then
some other stuff got added.
