.. BACpypes command logging module

.. module:: commandlogging

CommandLogging
==============

This module provides a function that is typically used to attach a log handler
to a **_debug** logger that has been created by the methods in
:mod:`debugging`.  It defines and uses a variety of support classes, BACpypes
applications rarely need to derive from them.

Functions
---------

.. function:: ConsoleLogHandler(loggerRef='', level=logging.DEBUG)

    :param string loggerRef: function to call
    :param level: logging level

    This is a long line of text.

Classes
-------

.. class:: LoggingFormatter(logging.Formatter)

    This is a long line of text.

    .. method:: __init__()

        logging.Formatter.__init__(self, logging.BASIC_FORMAT, None)

    .. method:: format(record)

        :param logging.LogRecord record: record to format

        This function converts the record into a string.  It uses
        the regular formatting function that it overrides, then 
        if any of the parameters inherit from :class:`debugging.DebugContents`
        (or duck typed by providing **debug_contents** function) the 
        message is extended with the deconstruction of those parameters.

Logging Service
---------------

The follow set of classes are used to provide access to the defined loggers as
a client or a service.  For example, instances of these classes can be stacked
on top of a UDP or TCP director to provide debugging to remote devices or to 
BACpypes applications running as a daemon where there is no interactive command
capability.

.. class:: CommandLoggingHandler(logging.Handler)

    .. method:: __init__(self, commander, destination, loggerName)

        :param commander: record to format
        :param destination: record to format
        :param loggerName: record to format

        This is a long line of text.

    .. method:: emit(self, record)

        :param commander: record to format

        This is a long line of text.

.. class:: CommandLogging(Logging)

    .. data:: handlers

    .. method:: process_command(self, cmd, addr)

        :param cmd: command message to be processed
        :param addr: address of source of request/response

        This is a long line of text.

    .. method:: emit(self, msg, addr)

        :param msg: message to send
        :param addr: address to send request/response

        This is a long line of text.

.. class:: CommandLoggingServer(CommandLogging, Server, Logging)

    .. method:: indication(pdu)

        :param pdu: command message to be processed

        This is a long line of text.

    .. method:: emit(self, msg, addr)

        :param msg: message to send
        :param addr: address to send response

        This is a long line of text.

.. class:: CommandLoggingClient(CommandLogging, Client, Logging)

    .. method:: confirmation(pdu)

        :param pdu: command message to be processed

        This is a long line of text.

    .. method:: emit(self, msg, addr)

        :param msg: message to send
        :param addr: address to send request

        This is a long line of text.
