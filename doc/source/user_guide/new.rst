.. MacSyLib - python library that provide functions for
    detection of macromolecular systems in protein datasets
    using systems modelling and similarity search.
    Authors: Sophie Abby, Bertrand Néron
    Copyright © 2014-2025 Institut Pasteur (Paris) and CNRS.
    See the COPYRIGHT file for details
    MacsyLib is distributed under the terms of the GNU General Public License (GPLv3).
    See the COPYING file for details.


.. _new:

**********************
What's new in MacSyLib
**********************



V 1.0.4
=======

Test MacSyFinder with python 3.14

Features
--------

New version of the model definition grammar
"""""""""""""""""""""""""""""""""""""""""""
The version of the grammar is now `2.1`. The **semantic** stay **unchanged**. But the **syntax** is little **more stringent**.
We develop a new model definition validation system.
This system check thoroughly the xml models definitions.
Only valid xml comments are allowed :code:`<!-- comment -->`
The boolean value (for attributes: loner, multi_system, multi_model, ...) must be `true` or `false` in lower case
(`True` or `False` are not allowed any longer)
This feature is used only for :code:`msl_data check` command. At run time *macsylib* can use grammar 2.0 or 2.1.

This feature require to install `lxml` library.
Which is automatically done if you install macsylib with target `[model]` or `[dev]`

:code:`pip install macsylib[model]`

Bug fix
-------

Moderate
""""""""

Fix bug during the cluster building step, with circularization
see https://github.com/gem-pasteur/macsyfinder/issues/81 and https://github.com/macsy-models/CONJScan/issues/1
Impacted versions: < 1.0.4

Minor
"""""

small internal bugs with no incidences on results


V 1.0.2
=======

Fix bug im `msl_data` when library used by third partite as `MacSyFinder`.


V 1.0.1
=======

| Now MacSyFinder and MacSyLib are two separated packages.
| MacSyFinder is build on top of MacSyLib.
| This new architecture allow to create new tool on the top of MacSyLib.

provide 2 scripts

- ``msl_data`` formerly `macsydata`
- ``msl_profile`` formerly `macsyprofile`

features
--------

* add new subcommand to msl_data ``msl_data show`` to show the structure of an installed package model :ref:`msl_data`


For older changelog see `https://macsyfinder.readthedocs.io/en/latest/ <macsyfinder documentation>`_.
