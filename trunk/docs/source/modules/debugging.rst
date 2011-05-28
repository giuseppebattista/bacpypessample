.. BACpypes debugging module

.. module:: debugging

Debugging
=========

All applications use some kind of debugging.

Globals
-------

.. data:: _root

    This is a long line of text.

Functions
---------

.. function:: ModuleLogger(globs)

    :param globs: dictionary of module globals

    This function, posing as an instance creator, returns a ...

Function Decorators
-------------------

.. function:: function_debugging

    This function decorates a function with instances of buggers that are
    named by the function name combined with the module name.  It is used like
    this::

        @function_debugging
        def some_function(arg):
            if _debug: some_function._debug("some_function %r", arg)
            # rest of code

    This results in a bugger called **module.some_function** that can be
    accessed by that name when attaching log handlers.

Classes
-------

.. class:: DebugContents

    By inheriting from this class, all calls to build an object will return
    the same object.

    .. method:: debug_contents(indent=1, file=sys.stdout, _ids=None)

        :param indent: function to call
        :param file: regular arguments to pass to fn
        :param _ids: keyword arguments to pass to fn
    
        This function is called to postpone a function call until after the 
        asyncore.loop processing has completed.  See :func:`run`.

.. class:: Logging

    By inheriting from this class, all calls to build an object will return
    the same object.

