.. MacSyLib - python library that provide functions for
    detection of macromolecular systems in protein datasets
    using systems modelling and similarity search.
    Authors: Sophie Abby, Bertrand Néron
    Copyright © 2014-2025 Institut Pasteur (Paris) and CNRS.
    See the COPYRIGHT file for details
    MacsyLib is distributed under the terms of the GNU General Public License (GPLv3).
    See the COPYING file for details.

.. _package_module:

*******
package
*******

Allow to handles model package either on localhost or from a remote location.
the model packages can be stored in github organization to be downloaded and installed locally.
The classes below are used by `macsydata`, which is the entry point to manipulate models package.

.. _package_api:

package API reference
=====================


AbstractModelIndex
==================
.. autoclass:: macsylib.package.AbstractModelIndex
   :members:
   :private-members:
   :special-members:


LocalModelIndex
===============
.. autoclass:: macsylib.package.LocalModelIndex
   :members:
   :private-members:
   :special-members:


RemoteModelIndex
================
.. autoclass:: macsylib.package.RemoteModelIndex
   :members:
   :private-members:
   :special-members:


Package
=======
.. autoclass:: macsylib.package.Package
   :members:
   :private-members:
   :special-members:
