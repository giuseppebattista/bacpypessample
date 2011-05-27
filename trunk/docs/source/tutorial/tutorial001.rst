.. BACpypes tutorial lesson 1

Clients and Servers
===================

Since the server needs to do something when it gets a request, it 
needs to provide a function to get it::

    >>> class MyServer(Server):
    ...     def indication(self, arg):
    ...         print "working on", arg
    ...         self.response(arg.upper())
    ... 

Now create an instance of this new class and bind the client and server together::

    >>> s = MyServer()
    >>> bind(c, s)

This only solves the downstream part of the problem, as you can see::

    >>> c.request("hi")
    working on hi
    NotImplementedError: confirmation must be overridden

So now we create a custom client class that does something with the response::

    >>> class MyClient(Client):
    ...     def confirmation(self, pdu):
    ...         print "thanks for the", pdu
    ... 

Create an instance of it, bind the client and server together and test it::

    >>> c = MyClient()
    >>> bind(c, s)
    >>> c.request('hi')
    working on hi
    thanks for the HI

Success!

But at some point you can't get too carried away with yourself.

.. note::
    Having some the real text of the note display under the directive, or whatever this thing is called
    looks a lot nicer.  I wondering what it would take to make a restructed text format for OWL
    documents.

Ah, some day maybe.
