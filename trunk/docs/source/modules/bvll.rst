.. BACpypes bvll module

.. module:: bvll

BACnet Virtual Link Layer
=========================

BACnet virtual link layer...

PDU Base Types
--------------

.. class:: BVLCI(PCI, DebugContents, Logging)

    .. data:: bvlciType
    .. data:: bvlciFunction
    .. data:: bvlciLength

    This is a long line of text.

.. class:: BVLPDU(BVLCI, PDUData)

    This is a long line of text.

PDU Types
---------

.. class:: Result(BVLCI)

Broadcast Distribution Table
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. class:: ReadBroadcastDistributionTable(BVLCI)

.. class:: ReadBroadcastDistributionTableAck(BVLCI)

.. class:: WriteBroadcastDistributionTable(BVLCI)

Foreign Devices
^^^^^^^^^^^^^^^

.. class:: FDTEntry(DebugContents)

.. class:: RegisterForeignDevice(BVLCI)

.. class:: ReadForeignDeviceTable(BVLCI)

.. class:: ReadForeignDeviceTableAck(BVLCI)

.. class:: DeleteForeignDeviceTableEntry(BVLCI)


Message Broadcasting
^^^^^^^^^^^^^^^^^^^^

.. class:: OriginalUnicastNPDU(BVLPDU)

.. class:: OriginalBroadcastNPDU(BVLPDU)

.. class:: DistributeBroadcastToNetwork(BVLPDU)

.. class:: ForwardedNPDU(BVLPDU)
