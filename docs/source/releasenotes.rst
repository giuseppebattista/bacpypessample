.. BACpypes release notes

Release Notes
=============

This page contains release notes.

Version 0.9
-----------

There are a number of significant changes in BACpypes in this release, some of which
may break existing code so it is getting a minor release number.  While this project
is getting inexorably closer to a 1.0 release, we're not there yet.

The biggest change is the addition of a set of derived classes of ``Property`` that match the names of the way properties are described in the standard; ``OptionalProperty``, ``ReadableProperty``, and ``WritableProperty``.  This takes over from the awkward and difficult-to-maintain combinations of ``optional`` and ``mutable`` constructor parameters.  I went through the standard again and matched the class name with the object definition and it is much cleaner.

Revisions `r227 <http://sourceforge.net/p/bacpypes/code/227>`_
through `r234 <http://sourceforge.net/p/bacpypes/code/234>`_.

* At some point ``setuptools`` was replaced with ``distutils`` and this needed to change while I was getting the code working on Windows.
  `r227 <http://sourceforge.net/p/bacpypes/code/227>`_

* This has the new proerty classes.
  `r228 <http://sourceforge.net/p/bacpypes/code/228>`_

* The UDP module had some print statements and a traceback call that sent content to stdout, errors should go to stderr.
  `r229 <http://sourceforge.net/p/bacpypes/code/229>`_

* With the new property classes there needed to be a simpler and cleaner way managing the __init__ keyword parameters for a ``LocalDeviceObject``.  During testing I had created objects with no name or object identifier and it seemed like some error checking was warrented, so that was added to ``add_object`` and ``delete_object``.
  `r230 <http://sourceforge.net/p/bacpypes/code/230>`_

* This commit is the first pass at changing the way object classes are registered.  There is now a new ``vendor_id`` parameter so that derived classes of a standard object can be registered.  For example, if vendor Snork has a custom SnorkAnalogInputObject class (derived from ``AnalogInputObject`` of course) then both classes can be registered.

  The ``get_object_class`` has a cooresponding ``vendor_id`` parameter, so if a client application is looking for the appropriate class, pass the ``vendorIdentifier`` property value from the deivce object of the server and if there isn't a specific one defined, the standard class will be returned.

  The new and improved registration function would be a lot nicer as a decorator, but optional named parameters make and interesting twist.  So depending on the combination of parameters it returns a decorator, which is an interesting twist on recursion.

  This commit also includes a few minor changes like changing the name ``klass`` to the not-so-cute ``cls``, ``property`` to ``propid`` because the former is a reserved word, and the dictionary of registered objects from ``object_types`` to ``registered_object_types``.
  `r231 <http://sourceforge.net/p/bacpypes/code/231>`_

* Simple wrapping of the command line argument interpretation for a sample application.
  `r232 <http://sourceforge.net/p/bacpypes/code/232>`_

* The ``CommandableMixin`` isn't appropriate for ``BinaryValueObject`` type, so I replaced it with a ``DateValueObject``.
  `r233 <http://sourceforge.net/p/bacpypes/code/233>`_

* This adds the relaease notes page and a link to it for documentation, committed so I could continue working on it.
  `r234 <http://sourceforge.net/p/bacpypes/code/234>`_

* I managed to install Sphinx on my Windows laptop and this just added a build script to make it easier to put in these release notes.
  `r225 <http://sourceforge.net/p/bacpypes/code/225>`_

* Commit these notes so far and finish tomorrow.
  `r226 <http://sourceforge.net/p/bacpypes/code/226>`_

Version 0.8
-----------

This is a long line of text.

Revisions `r224 <http://sourceforge.net/p/bacpypes/code/224>`_
through `r226 <http://sourceforge.net/p/bacpypes/code/226>`_.

* Something interesting about 224.
  `r224 <http://sourceforge.net/p/bacpypes/code/224>`_

* Something interesting about 225.
  `r225 <http://sourceforge.net/p/bacpypes/code/225>`_

* Bump the minor version number.
  `r226 <http://sourceforge.net/p/bacpypes/code/226>`_


Version 0.7.5
-------------

This is a long line of text.

Revisions `r217 <http://sourceforge.net/p/bacpypes/code/217>`_
through `r223 <http://sourceforge.net/p/bacpypes/code/223>`_.

* Something interesting about 217.
  `r217 <http://sourceforge.net/p/bacpypes/code/217>`_

* Something interesting about 218.
  `r218 <http://sourceforge.net/p/bacpypes/code/218>`_

* Something interesting about 219.
  `r219 <http://sourceforge.net/p/bacpypes/code/219>`_

* Something interesting about 220.
  `r220 <http://sourceforge.net/p/bacpypes/code/220>`_

* Something interesting about 221.
  `r221 <http://sourceforge.net/p/bacpypes/code/221>`_

* Something interesting about 222.
  `r222 <http://sourceforge.net/p/bacpypes/code/222>`_

* Bump the patch version number.
  `r223 <http://sourceforge.net/p/bacpypes/code/223>`_

Version 0.7.4
-------------

Lost to the sands of time.

