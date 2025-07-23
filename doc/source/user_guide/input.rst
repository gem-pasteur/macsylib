.. MacSyLib - python library that provide functions for
    detection of macromolecular systems in protein datasets
    using systems modelling and similarity search.
    Authors: Sophie Abby, Bertrand Néron
    Copyright © 2014-2025 Institut Pasteur (Paris) and CNRS.
    See the COPYRIGHT file for details
    MacsyLib is distributed under the terms of the GNU General Public License (GPLv3).
    See the COPYING file for details.


.. _input:

*****************************
Input and Options of MacSyLib
*****************************


.. _input-dataset-label:

Input dataset
=============

The input dataset must be a set of protein sequences in **Fasta format** (see http://en.wikipedia.org/wiki/FASTA_format).
(The fasta file can be compressed in *gzip* format see note below)


The :ref:`base section<config-base-label>` in the configuration file (see :ref:`config-definition-label`)
can be used to specify **the path** and the **type of dataset** to deal with,
as well as the `--sequence_db` and `--db_type` parameters respectively,
described in the :ref:`command-line-label` (see :ref:`Input options <cmd-input-label>`).

  Four types of protein datasets are supported:

        * *unordered* : a set of sequences corresponding to a complete genome
          (*e.g.* an unassembled complete genome)
        * *ordered_replicon* : a set of sequences corresponding to an ordered complete replicon
          (*e.g.* an assembled complete genome)
        * *gembase* : a set of multiple ordered replicons, which format follows the convention described
          in :ref:`gembase_convention`.

For "ordered" ("ordered_replicon" or "gembase") datasets only,
MacSyLib can take into account the **shape of the genome**: "linear",
or "circular" for detection. The default is set to "circular".

  This can be set with the `--replicon_topology` parameter from :ref:`command-line-label`
  (see :ref:`Input options <cmd-input-label>`),
  or in the configuration in the :ref:`base section<config-base-label>`.

  With the "gembase" format, it is possible to specify a topology per replicon with a topology file
  (see :ref:`gembase_convention` and :ref:`topology-files`).

.. note::

    MSL can also read *.gz* compressed files; it will uncompress them on the fly.
    The compressed files must end with the *.gz* extension.
    For the `hmmsearch` step You need to have `gunzip` installed on your system for this to work.


.. _config-definition-label:

Configuration file
==================

Options to run MacSyLib can be specified in a configuration file.

The :ref:`Config object <configuration>` handles all configuration options for MacSylib.
There kind of locations where to put configuration file:

 #. System wide configuration (this configuration is used for all macsylib run)

    * */etc/macsylib/macsylib.conf*
    * or in *${VIRTUAL_ENV}/etc/macsylib.conf* if you installed macsylib in a virtualenv
    * the file pointed by environment variable *MACSY_HOME*

 #. User wide configuration (this configuration is used for all run for a user)

    * *~/.macsylib/macsylib.conf*

 #. Project configuration

    * *macsylib.conf* in the current directory
    * with command line option *--cfg-file*


.. note::
    The precedence rules from the least to the most important priority are:

    System wide configuration < user wide configuration < project configuration < command line option

This means that command-line options will always bypass those from the configuration files. In the same flavor,
options altering the definition of systems found in the command-line or the configuration file will always
overwhelm values from systems' :ref:`XML definition files <model-definition-grammar-label>`.

The configuration files must follow the Python "ini" file syntax.
The :ref:`Config object <configuration>` provides some default values and performs some validations of the values.


In MacSyLib, six sections are defined and stored by default in the configuration file:

 .. _config-base-label:

  * **base** : all information related to the protein dataset under study

    * *sequence_db* : the path to the dataset in Fasta format (*no default value*)
    * *db_type* : the type of dataset to handle, four types are supported:

        * *unordered* : a set of sequences corresponding to a complete replicon
          (*e.g.* an unassembled complete genome)
        * *ordered_replicon* : a set of sequences corresponding to a complete replicon ordered
          (*e.g.* an assembled complete genome)
        * *gembase* : a set of multiple ordered replicons.

      (*no default value*)

    * *replicon_topology* : the topology of the replicon under study.
      Two topologies are supported: 'linear' and 'circular' (*default* = 'circular').
      This option will be ignored if the dataset type is not ordered (*i.e.* "unordered_replicon" or "unordered").

  * **models**
    * list of models to search in replicon

  * **models_opt**

    * *inter_gene_max_space* = list of models' fully qualified names and integer separated by spaces (see example below).
      These values will supersede the values found in the model definition file.
    * *min_mandatory_genes_required* = list of models' fully qualified name and integer separated by spaces.
      These values will supersede the values found in the model definition file.
    * *min_genes_required* = list of models' fully qualified name and integer separated by spaces.
      These values will supersede the values found in the model definition file.
    * *max_nb_genes* = list of models' fully qualified names and integer separated by spaces.
      These values will supersede the values found in the model definition file.

  * **hmmer**

    * *hmmer_exe* (default= *hmmsearch* )
    * *e_value_res* = (default= *1* )
    * *i_evalue_sel* = (default= *0.5* )
    * *coverage_profile* = (default= *0.5* )

  * **score_opt**

    * *mandatory_weight* (default= *1.0*)
    * *accessory_weight* (default= *0.5*)
    * *exchangeable_weight* (default= *0.8*)
    * *redundancy_penalty* (default= *1.5*)
    * *out_of_cluster* (default= *0.7*)


  * **directories**

    * *res_search_dir* = (default= *./datatest/res_search* )
    * *res_search_suffix* = (default= *.search_hmm.out* )
    * *system_models_dir* = (default= *./models* )
    * *res_extract_suffix* = (default= *.res_hmm_extract* )
    * *index_dir* = (default= beside the sequence_db)

  * **general**

    * *log_level*: (default= *debug* ) This corresponds to an integer code:
        ========    ==========
        Level 	    Numeric value
        ========    ==========
        CRITICAL 	50
        ERROR 	    40
        WARNING 	30
        INFO 	    20
        DEBUG 	    10
        NOTSET 	    0
        ========    ==========
    * *log_file* = (default = macsylib.log in directory of the run)

Example of a configuration file

.. code-block:: ini

    [base]
    prefix = /path/to/macsylib/home/
    file = %(prefix)s/data/base/prru_psae.001.c01.fasta
    db_type = gembase
    replicon_topology = circular

    [models]
    models_1 = TFF-SF_final all

    [models_opt]
    inter_gene_max_space = TXSS/T2SS 22 TXSS/Flagellum 44
    min_mandatory_genes_required = TXSS/T2SS 6 TXSS/Flagellum 4
    min_genes_required = TXSS/T2SS 8 TXSS/Flagellum 4
    max_nb_genes = TXSS/T2SS 12 TXSS/Flagellum 8

    [hmmer]
    hmmer = hmmsearch
    e_value_res = 1
    i_evalue_sel = 0.5
    coverage_profile = 0.5

    [score_opt]
    mandatory_weight = 1.0
    accessory_weight = 0.5
    exchangeable_weight = 0.8
    redundancy_penalty = 1.5
    loner_multi_system_weight = 0.7

    [directories]
    prefix = /path/to/macsylib/home/
    data_dir = %(prefix)s/data/
    res_search_dir = %(prefix)s/dataset/res_search/
    res_search_suffix = .raw_hmm
    system_models_dir = %(data_dir)/data/models, ~/.macsylib/data
    profile_suffix = .fasta-aln.hmm
    res_extract_suffix = .res_hmm
    index_dir = path/where/I/store/my_indexes

   [general]
   log_level = debug
   worker = 4

.. note::

    After a run, the corresponding configuration file ("macsylib.conf") is generated as a (re-usable)
    output file that stores every options used in the run.
    It is stored in the results' directory (see :ref:`the output section <outputs>`).

.. warning::

    The configuration variable `models_dir` cannot be set in general configuration file.
    `models_dir`` can be set only in configuration under user control.
    ```$(HOME)/.macsylib/macsylib.conf < macsylib.conf < "command-line" options```
    `models_dir` is a single path to a directory whre masyfinder can find models.

    But the `system_models_dir` can be set in general configuration file

    * /etc/macsylib/macsylib.conf
    * or ${VIRTUAL_ENV}/etc/macsylib/macsylib.conf
    * or anywhere point by $MACSY_CONF environment variable

    `system_models_dir` manage a list of locations where macsylib can find models.
    The order of locations is important, it reflects the precedence rule (The models found in last location
    superseed models found in previous location).
    By default look for following directories: */share/macsylib/models*, or */usr/share/macsylib/models*
    and *$HOME/.macsylib/models* and `system_models_dir` uses these directories if they exists.


In-house input files
====================
.. toctree::
   :maxdepth: 1

   gembase_convention
