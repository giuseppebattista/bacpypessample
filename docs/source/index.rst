.. BACpypes documentation master file, created by
   sphinx-quickstart on Wed May  4 21:36:23 2011.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to BACpypes
===================

BACpypes library for building BACnet applications using Python.  Installation 
is easy, just::

    $ sudo easy_install bacpypes

You will be installing the latest released version.  You can also check out
the latest version from SourceForge::

    $ svn co https://bacpypes.svn.sourceforge.net/svnroot/bacpypes bacpypes

And then use the setup utility to install it::

    $ cd bacpypes/trunk/
    $ python setup.py install

If you would like to participate in its development, please join the
`developers mailing list <https://lists.sourceforge.net/lists/listinfo/bacpypes-developers>`_
and use the `Trac <https://sourceforge.net/apps/trac/bacpypes>`_ to create 
tickets and monitor the project development.

Welcome aboard!

Tutorial
--------

This tutorial is a step-by-step walk through of the library describing the
essential components of a BACpypes application and how the pieces fit together.

.. toctree::
    :maxdepth: 1

    tutorial/tutorial001.rst
    tutorial/tutorial002.rst

Samples
-------

The library has a variety of sample applications, some of them are a framework
for building larger applications, some of them are standalone analysis tools 
that don't require a connection to a network.

.. toctree::
    :maxdepth: 1

    samples/sample001.rst

Modules
-------

This documentation is intended for BACpypes developers.

Core
^^^^

.. toctree::
    :maxdepth: 2

    modules/core.rst
    modules/comm.rst
    modules/debugging.rst
    modules/consolelogging.rst
    modules/errors.rst
    modules/singleton.rst
    modules/task.rst
    modules/event.rst

UDP Communications
^^^^^^^^^^^^^^^^^^

.. toctree::
    :maxdepth: 2

    modules/udp.rst
    modules/bvll.rst
    modules/bvllservice.rst

TCP Communications
^^^^^^^^^^^^^^^^^^

.. toctree::
    :maxdepth: 2

    modules/tcp.rst
    modules/bsll.rst
    modules/bsllservice.rst

Network Layer
^^^^^^^^^^^^^

.. toctree::
    :maxdepth: 2

    modules/npdu.rst
    modules/netservice.rst
    modules/vlan.rst

Application Layer
^^^^^^^^^^^^^^^^^

.. toctree::
    :maxdepth: 2

    modules/primitivedata.rst
    modules/constructeddata.rst
    modules/basetypes.rst

    modules/apdu.rst
    modules/object.rst
    modules/app.rst
    modules/appservice.rst

Analysis
^^^^^^^^

.. toctree::
    :maxdepth: 2

    modules/analysis.rst

Other
^^^^^

.. toctree::
    :maxdepth: 2

    modules/commandlogging.rst
    glossary.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

