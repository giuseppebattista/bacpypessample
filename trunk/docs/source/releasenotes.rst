.. BACpypes release notes

Release Notes
=============

This page contains release notes.

Version 0.9.1
-------------

Most of this release is just documentation, but it includes some new functionality
for translating PDUs into dictionaries.  The new ``dict_contents`` functions will 
most likely have some bugs, so consider that API unstable.

Revisions `r238 <http://sourceforge.net/p/bacpypes/code/238>`_
through `r245 <http://sourceforge.net/p/bacpypes/code/245>`_.

* For some new users of BACpypes, particularly those that were also new to BACnet,
  it can be a struggle getting something to work.  This is the start of a new
  documentation section to speed that process along.
  `r238 <http://sourceforge.net/p/bacpypes/code/238>`_
  `r239 <http://sourceforge.net/p/bacpypes/code/239>`_
  `r240 <http://sourceforge.net/p/bacpypes/code/240>`_

* For multithreaded applications it is sometimes handly to override the default 
  spin value, which is the maximum amount of time that the application should 
  be stuck in the asyncore.loop() function.  The developer could import the 
  core module and change the CORE value before calling run(), but that seems 
  excessively hackish.
  `r241 <http://sourceforge.net/p/bacpypes/code/241>`_

* Apparently there should not be a dependancy on ``setuptools`` for developers that 
  want to install the library without it.  In revision `r227 <http://sourceforge.net/p/bacpypes/code/227>`_
  I changed the setup.py file, but that broke the release script.  I'm not 
  completely sure this is correct, but it seems to work.
  `r242 <http://sourceforge.net/p/bacpypes/code/242>`_

* This revision includes a new dict_contents() function that encodes PDU content
  into a dict-like object (a real ``dict`` by default, but the developer can provide 
  any other class that supports ``__setitem__``).  This is the first step in a long
  road to translate PDU data into JSON, then into BSON to be streamed into a 
  MongoDB database for analysis applications.
  `r243 <http://sourceforge.net/p/bacpypes/code/243>`_

* Bump the version number before releasing it.
  `r244 <http://sourceforge.net/p/bacpypes/code/244>`_

* Update these release notes.
  `r245 <http://sourceforge.net/p/bacpypes/code/245>`_

Version 0.9
-----------

There are a number of significant changes in BACpypes in this release, some of which
may break existing code so it is getting a minor release number.  While this project
is getting inexorably closer to a 1.0 release, we're not there yet.

The biggest change is the addition of a set of derived classes of ``Property`` that
match the names of the way properties are described in the standard; ``OptionalProperty``,
``ReadableProperty``, and ``WritableProperty``.  This takes over from the awkward and
difficult-to-maintain combinations of ``optional`` and ``mutable`` constructor parameters.
I went through the standard again and matched the class name with the object definition
and it is much cleaner.

This change was brought about by working on the `BACowl <http://bacowl.sourceforge.net/>`_
project where I wanted the generated ontology to more closely match the content of the 
standard.  This is the first instance where I've used the ontology design to change 
application code.

Revisions `r227 <http://sourceforge.net/p/bacpypes/code/227>`_
through `r234 <http://sourceforge.net/p/bacpypes/code/234>`_.

* At some point ``setuptools`` was replaced with ``distutils`` and this needed to change
  while I was getting the code working on Windows.
  `r227 <http://sourceforge.net/p/bacpypes/code/227>`_

* Added the new property classes and renamed the existing ``Property`` class instances.
  There are object types that are not complete (not every object type has every property
  defined) and these will be cleaned up and added in a minor release in the near future.
  `r228 <http://sourceforge.net/p/bacpypes/code/228>`_

* The UDP module had some print statements and a traceback call that sent content to stdout,
  errors should go to stderr.
  `r229 <http://sourceforge.net/p/bacpypes/code/229>`_

* With the new property classes there needed to be a simpler and cleaner way managing the
  __init__ keyword parameters for a ``LocalDeviceObject``.  During testing I had created
  objects with no name or object identifier and it seemed like some error checking was
  warrented, so that was added to ``add_object`` and ``delete_object``.
  `r230 <http://sourceforge.net/p/bacpypes/code/230>`_

* This commit is the first pass at changing the way object classes are registered.  There
  is now a new ``vendor_id`` parameter so that derived classes of a standard object can be
  registered.  For example, if vendor Snork has a custom SnorkAnalogInputObject class (derived
  from ``AnalogInputObject`` of course) then both classes can be registered.

  The ``get_object_class`` has a cooresponding ``vendor_id`` parameter, so if a client
  application is looking for the appropriate class, pass the ``vendorIdentifier`` property
  value from the deivce object of the server and if there isn't a specific one defined, the
  standard class will be returned.

  The new and improved registration function would be a lot nicer as a decorator, but optional
  named parameters make and interesting twist.  So depending on the combination of parameters
  it returns a decorator, which is an interesting twist on recursion.

  At some point there will be a tutorial covering just this functionality, and before this
  project hits version 1.0, there will be a similar mechanism for vendor defined enumerations,
  especially ``PropertyIdentifier``, and this will also follow the BACowl ontology conventions.

  This commit also includes a few minor changes like changing the name ``klass`` to the 
  not-so-cute ``cls``, ``property`` to ``propid`` because the former is a reserved word, and 
  the dictionary of registered objects from ``object_types`` to ``registered_object_types``.
  `r231 <http://sourceforge.net/p/bacpypes/code/231>`_

* Simple wrapping of the command line argument interpretation for a sample application.
  `r232 <http://sourceforge.net/p/bacpypes/code/232>`_

* The ``CommandableMixin`` isn't appropriate for ``BinaryValueObject`` type, so I replaced it
  with a ``DateValueObject``.
  `r233 <http://sourceforge.net/p/bacpypes/code/233>`_

* I managed to install Sphinx on my Windows laptop and this just added a build script to make
  it easier to put in these release notes.
  `r235 <http://sourceforge.net/p/bacpypes/code/235>`_

* This adds the relaease notes page and a link to it for documentation, committed so I could
  continue working on it from a variety of different places.  I usually wouldn't make a commit just
  for this unless I was working in a branch, but because I'm working in the trunk rather than 
  using a service like DropBox I decided to let myself get away with it.
  `r234 <http://sourceforge.net/p/bacpypes/code/234>`_
  `r236 <http://sourceforge.net/p/bacpypes/code/236>`_

* Committed the final version of these notes and bumped the minor version number.
  `r237 <http://sourceforge.net/p/bacpypes/code/237>`_

Version 0.8
-----------

Placeholder for 0.8 release notes.

Revisions `r224 <http://sourceforge.net/p/bacpypes/code/224>`_
through `r226 <http://sourceforge.net/p/bacpypes/code/226>`_.

* Placeholder for comments about revision 224.
  `r224 <http://sourceforge.net/p/bacpypes/code/224>`_

* Placeholder for comments about revision 225.
  `r225 <http://sourceforge.net/p/bacpypes/code/225>`_

* Bump the minor version number.
  `r226 <http://sourceforge.net/p/bacpypes/code/226>`_

Version 0.7.5
-------------

Placeholder for 0.8 release notes.

Revisions `r217 <http://sourceforge.net/p/bacpypes/code/217>`_
through `r223 <http://sourceforge.net/p/bacpypes/code/223>`_.

* Placeholder for comments about revision 217.
  `r217 <http://sourceforge.net/p/bacpypes/code/217>`_

* Placeholder for comments about revision 218.
  `r218 <http://sourceforge.net/p/bacpypes/code/218>`_

* Placeholder for comments about revision 219.
  `r219 <http://sourceforge.net/p/bacpypes/code/219>`_

* Placeholder for comments about revision 220.
  `r220 <http://sourceforge.net/p/bacpypes/code/220>`_

* Placeholder for comments about revision 221.
  `r221 <http://sourceforge.net/p/bacpypes/code/221>`_

* Placeholder for comments about revision 222.
  `r222 <http://sourceforge.net/p/bacpypes/code/222>`_

* Bump the patch version number.
  `r223 <http://sourceforge.net/p/bacpypes/code/223>`_

Version 0.7.4
-------------

Lost to the sands of time.

