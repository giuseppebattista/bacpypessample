.. BACpypes npdu module

.. module:: npdu

Network Layer Protocol Data Units
=================================

This is a long line of text.

PDU Base Types
--------------

.. class:: NPCI(PCI)

    This is a long line of text.

    .. data:: npduVersion

        This is a long line of text.

    .. data:: npduControl

        This is a long line of text.

    .. data:: npduDADR

        This is a long line of text.

    .. data:: npduSADR

        This is a long line of text.

    .. data:: npduHopCount

        This is a long line of text.

    .. data:: npduNetMessage

        This is a long line of text.

    .. data:: npduVendorID

        This is a long line of text.

    .. method:: update(npci)

        This is a long line of text.

    .. method:: encode(pdu)

        This is a long line of text.

    .. method:: decode(pdu)

        This is a long line of text.

.. class:: BSLPDU(BVSCI, PDUData)

    This is a long line of text.

    .. method:: encode(pdu)

        This is a long line of text.

    .. method:: decode(pdu)

        This is a long line of text.

Service Requests
----------------

.. class:: WhoIsRouterToNetwork(NPCI)

    This is a long line of text.

    .. method:: encode(npdu)
    .. method:: decode(npdu)

        This is a long line of text.

.. class:: IAmRouterToNetwork(NPCI)

    This is a long line of text.

    .. method:: encode(npdu)
    .. method:: decode(npdu)

        This is a long line of text.

.. class:: ICouldBeRouterToNetwork(NPCI)

    This is a long line of text.

    .. method:: encode(npdu)
    .. method:: decode(npdu)

        This is a long line of text.

.. class:: RejectMessageToNetwork(NPCI)

    This is a long line of text.

    .. method:: encode(npdu)
    .. method:: decode(npdu)

        This is a long line of text.

.. class:: RouterBusyToNetwork(NPCI)

    This is a long line of text.

    .. method:: encode(npdu)
    .. method:: decode(npdu)

        This is a long line of text.

.. class:: RouterAvailableToNetwork(NPCI)

    This is a long line of text.

    .. method:: encode(npdu)
    .. method:: decode(npdu)

        This is a long line of text.

.. class:: RoutingTableEntry()

    This is a long line of text.

    .. data:: rtDNET

        This is a long line of text.

    .. data:: rtPortID

        This is a long line of text.

    .. data:: rtPortInfo

        This is a long line of text.

.. class:: InitializeRoutingTable(NPCI)

    This is a long line of text.

    .. method:: encode(npdu)
    .. method:: decode(npdu)

        This is a long line of text.

.. class:: InitializeRoutingTableAck(NPCI)

    This is a long line of text.

    .. method:: encode(npdu)
    .. method:: decode(npdu)

        This is a long line of text.

.. class:: EstablishConnectionToNetwork(NPCI)

    This is a long line of text.

    .. method:: encode(npdu)
    .. method:: decode(npdu)

        This is a long line of text.

.. class:: DisconnectConnectionToNetwork(NPCI)

    This is a long line of text.

    .. method:: encode(npdu)
    .. method:: decode(npdu)

        This is a long line of text.
