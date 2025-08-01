.. MacSyLib - python library that provide functions for
   detection of macromolecular systems in protein datasets
   using systems modelling and similarity search.
   Authors: Sophie Abby, Bertrand Néron
   Copyright © 2014-2025 Institut Pasteur (Paris) and CNRS.
   See the COPYRIGHT file for details
   MacSyLib is distributed under the terms of the GNU General Public License (GPLv3).
   See the COPYING file for details.

.. _publish_package:

*************************
Publishing/sharing models
*************************


 .. _writing_model_package:


Writing your own macsy-model package
====================================

The whole package structure and the corresponding files are described in the section :ref:`package_structure`.
It requires five different types of files to be complete:

* a `metadata.yml` file (mandatory)
* a `README.md` file (mandatory)
* a `LICENSE` file (optional but **HIGHLY** recommended)
* a `model_conf.xml` file (optional)
* macsy-models definition(s) within a `definitions` folder (mandatory)
* HMM profiles within a `profiles` folder (mandatory)

You can create a template for your package by using `msl_data init`.
It will create for you:

* the git repository with the data package with the right structure.
* a template of `metadata.yaml` .
* a template of `README.md` file.
* a generic `model_conf.xml` file.
* a LICENSE file if `--license` option is set.
* a COPYRIGHT file if `--holders` option is set.
* a directory `definitions` with an example of model definition (model_example.xml to remove before publishing).
* a directory `profiles` where to put the hmm profiles corresponding to the models genes.


Sharing your models
===================

If you want to share your models you can create a :ref:`macsy-model package <model_package>` in your github repository.
Several steps are needed to publish your model:

1. Check the **validity** of your package with the ``msl_data check`` command.
   You have to run it from within the folder containing your package files.
   It will report:

   * everything is clear: `msl_data` displays the next step to take to publish the package

   * warning: it means that the package could be improved.

   It is better to fix it if you can, but you can also proceed to *Step 2*

   * error: the package is not ready to be published as is. You have to fix the errors before you go to *Step 2*.

2. Create a **tag**, and submit a **pull request** to the https://github.com/macsy-models organization.
   This step is **very important**: without a tag, there is no package.
   `msl_data check` only tagged packages.
   It is **Mandatory** to follow a versioning scheme described here:

        * https://www.python.org/dev/peps/pep-0440/#public-version-identifiers
        * https://the-hitchhikers-guide-to-packaging.readthedocs.io/en/latest/specification.html#standard-versioning-schemes

   .. important::

        If your package is in version *2.0.1* the tag must be `2.0.1`.
        The version or tag must **NOT** start with letter as `v2.0.1` or `my_package-2.0.1`.

   .. warning::

        To avoid making an inconsistent model visible by msl_data install/search (by pushing a tag),
        a pre-push hook has been setup in the git repository by `msl_data init` command.
        If you do not used `msl_data init` to create the model, It is a good idea to set up the hook by yourself.

        Check that the hook is well named pre-push and it is executable (`chmod 755 .git/hooks/pre-push`)
        This script run `msl_data check` if you push a tag and it prevent the push if some error are found.

        .. literalinclude:: ../_static/code/pre-push
           :language: shell

        :download:`pre-push <../_static/code/pre-push>` .


3. When your pull request (PR) is accepted, the model package becomes automatically available to the community through the `msl_data` tool.

If you don't want to submit a PR you can provide the tag release tarball (tar.gz) as is to your collaborators.
This archive will also be usable with the `msl_data` tool.

.. note::

    The creation of a git repositorywith the right hooks, skeleton of license, copyrights, metadata, profleis and definitions
    can be done by `msl_data init` command.

.. note::

    ``msl_data check``
    checks the syntax of the package, but it does not publish anything.
    It just warns you if something is wrong with the package.
    Every model provider should check its own package before publishing it.
    The package publication is done by the `git push` and the `pull request`.

Examples of ``msl_data check`` outputs:


Your package is syntactically correct:

.. code-block:: text

    msl_data check tests/data/models/test_model_package/
    Checking 'test_model_package' package structure
    Checking 'test_model_package' metadata_path
    Checking 'test_model_package' Model definitions
    Models Parsing
    Definitions are consistent
    Checking 'test_model_package' model configuration
    There is no model configuration for package test_model_package.
    If everyone were like you, I'd be out of business
    To push the models in organization:
            cd tests/data/models/test_model_package
    Transform the models into a git repository
            git init .
            git add .
            git commit -m 'initial commit'
    add a remote repository to host the models
    for instance if you want to add the models to 'macsy-models'
            git remote add origin https://github.com/macsy-models/
            git tag 1.0b2
            git push --tags


You received some warnings:

.. code-block:: text

    msl_data check tests/data/models/Model_w_conf/
    Checking 'Model_w_conf' package structure
    Checking 'Model_w_conf' metadata_path
    Checking 'Model_w_conf' Model definitions
    Models Parsing
    Definitions are consistent
    Checking 'Model_w_conf' model configuration
    The package 'Model_w_conf' have not any LICENSE file. May be you have not right to use it.
    The package 'Model_w_conf' have not any README file.
    msl_data says: You're only giving me a partial QA payment?
    I'll take it this time, but I'm not happy.
    I'll be really happy, if you fix warnings above, before to publish these models.

You received some errors:

.. code-block:: text

    msl_data check tests/data/models/TFF-SF/
    Checking 'TFF-SF' package structure
    The package 'TFF-SF' have no 'metadata.yml'.
    Please fix issues above, before publishing these models.
    ValueError
