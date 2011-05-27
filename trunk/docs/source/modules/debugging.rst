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

    This is a long line of text.

.. function:: function_debugging(f)

    :param f: function to update

    This is a long line of text.

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

