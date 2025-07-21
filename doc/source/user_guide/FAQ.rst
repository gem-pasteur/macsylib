.. MacSyLib - python library that provide functions for
   detection of macromolecular systems in protein datasets
   using systems modelling and similarity search.
   Authors: Sophie Abby, Bertrand Néron
   Copyright © 2014-2025 Institut Pasteur (Paris) and CNRS.
   See the COPYRIGHT file for details
   MacSyLib is distributed under the terms of the GNU General Public License (GPLv3).
   See the COPYING file for details.


.. _FAQ:


**************************
Frequently Asked Questions
**************************

How to report an issue?
-----------------------

If you encounter a problem while running MacSyFinder, please submit an issue on the dedicated page of the `GitHub project <https://github.com/gem-pasteur/macsyfinder/issues>`_

To ensure we have all elements to help, please provide:

- a concise description of the issue
- the expected behavior VS observed one
- the exact command-line used
- the version of MacSyFinder used
- the exact error message, and if applicable, the `<macsylib>.log` and `<macsylib>.conf` files
- if applicable, an archive (or link to it) with the output files obtained
- if possible, the smallest dataset there is to reproduce the issue
- if applicable, this would also include the macsy-models (XML models plus HMM profiles) used (or precise version of the models if there are publicly available). Same as above, if possible, please provide the smallest set possible of models and HMM profiles.

All these will definitely help us to help you! ;-)

.. note::

    If you use ``macsylib`` in higher level script you can change <macsylib> by the name of your tool by setting it in :class:`macsylib.config.MacsyDefault` prog_name parameter.

.. _citations:

How to cite MacSyFinder and published macy-models?
--------------------------------------------------

- `Abby et al. 2014 <https://doi.org/10.1371/journal.pone.0110726>`_, *PLoS ONE* for the **general principles of MacSyFinder** (version 1), and the corresponding set of Cas systems (CasFinder, 1st version).

- `Abby and Rocha 2012 <https://doi.org/10.1371/journal.pgen.1002983>`_, *PLoS Genetics*, for the study of the evolutionary relationship between the T3SS and the bacterial flagellum, and how were designed the corresponding HMM protein profiles.

- `Abby et al. 2016 <https://www.nature.com/articles/srep23080>`_, *Scientific Reports*, for the description of bacterial protein secretion systems' models (TXSScan: T1SS, T2SS, T5SS, T6SS, T9SS, Tad, T4P).

- `Denise et al. 2019 <https://doi.org/10.1371/journal.pbio.3000390>`_, *PLoS Biology*, for the description of type IV-filament super-family models (TFF-SF: T2SS, T4aP, T4bP, Com, Tad, archaeal T4P).

- `Rendueles et al. 2017 <https://doi.org/10.1371/journal.ppat.1006525>`_, *PLoS Pathogens*, for the CapsuleFinder set of models.

- `Couvin, Bernheim et al. 2018 <https://doi.org/10.1093/nar/gky425>`_, *Nucleic Acids Research*, for the updated version of the set of Cas systems' models, CasFinder.

.. add CONJscan? Which ref?


.. _cmd-line-examples:

What do MacSyFinder command lines look like?
--------------------------------------------


Here are a few examples of command line formation:

.. code-block:: python

   import os
   import logging
   from argparse import Namespace

   import macsylib
   import macsylib.config
   import macsylib.registries
   import macsylib.utils
   import macsylib.search_systems

   defaults = macsylib.config.MacsyDefaults()
   settings = Namespace(
           db_type='ordered_replicon',
           sequence_db='test.fasta',
           models=['TFF-SF' , 'all'], # this model must be installed with msl_data scripts
           worker=4,
           out_dir='my_results'
   )
   config = macsylib.config.Config(defaults, settings)

   os.makedirs(config.working_dir()) # working_dir = out_dir; you have to create this directory

   macsylib.init_logger(log_file=os.path.join(config.working_dir(), config.log_file()))
   macsylib.logger_set_level(level=logging.INFO)
   logger = logging.getLogger('macsylib')
   model_registry = macsylib.registries.ModelRegistry()

   for model_dir in config.models_dir():
       models_loc_available = macsylib.registries.scan_models_dir(model_dir)
       for model_loc in models_loc_available:
           model_registry.add(model_loc)
   models_def_to_detect, models_fam_name, models_version = macsylib.utils.get_def_to_detect(config.models(), model_registry)

   all_systems, rejected_candidates = macsylib.search_systems.search_systems(config, model_registry, models_def_to_detect, logger)

The code above correspond more or less to macsyfinder command line

:code:`macsyfinder --db-type ordered_replicon --sequence-db genome.fasta --models TFF-SF all`

| For more details check the developer guide :ref:`developer_guide` and api documentation :ref:`api`
| For more example check `macsyfinder source code <https://github.com/gem-pasteur/macsyfinder/tree/master>`_

.. _faq-search-mode:

What search mode to be used?
----------------------------

Depending on the type of dataset you have, you will have to adapt MacSyFinder's search mode.

- If you have a fasta file from a complete genome where **proteins are ordered** according to the corresponding genes' order along the replicon,
  your dataset is entitled to the most powerful search mode (see below): `ordered_replicon` and use the following option `--db-type ordered_replicon`.

- If you have a fasta file of proteins with **no sense of the order** of the corresponding genes along the chromosome(s) or replicon(s),
  you will have to use the `unordered` search mode with the following option: `--db-type unordered`

- If you have **multiple ordered replicons** to analyse at once, you can follow the `Gembase` convention to name the proteins in the fasta file,
  so that the original replicons can be assessed from their name: :ref:`see here for a description <gembase_convention>`.

.. note::

 - When the **gene order is known** (`ordered_replicon` search mode) the power of the analysis is **maximal**,
   since both the genomic content and context are taken into account for the search.

 - When the **gene order is unknown** (`unordered` search mode) the power of the analysis is more **limited** since
   the presence of systems can only be suggested on the basis of the quorum of components - and not based on genomic context information.


More on command-line options :ref:`here <command-line-label>` and on MacSyFinder's functioning :ref:`here <functioning>`.


How to deal with fragmented genomes (MAGs, SAGs, draft genomes)?
----------------------------------------------------------------

There are more and more genomes available which are not completely assembled, or are fragmented and incomplete.
In this case, several options can be considered.

1. If your genome is at least partially assembled and contigs are not too short, you might "feel lucky" and first
consider to run MacSyFinder with the `ordered_replicon` mode. It could be particularly efficient if you are investigating
systems encoded by compact loci (Cas systems, some secretion systems...), as they might be encoded by a single contig.

2. On top of the `ordered_replicon` mode, you might add the option "multi-loci" to the systems to annotate (if not already the case),
in order to maximize the chance to annotate an entire system, even if encoded across several contigs.

3. The `unordered` mode can be used in complement of the two above options, e.g. to retrieve some of the missing components.
It will enable to assess the genetic potential and possible presence of a system, independently of the quality of assembly of the genome.
It might also be the only reasonable option if the genome is too fragmented and/or too incomplete.

.. note::

 - The results obtained with the `ordered_replicon` mode on a fragmented genome have to be considered carefully, especially with respect
   to the contigs' borders, as some proteins from different contigs might be artificially considered as closely encoded.

 - To retrieve "fragments" of a system not found to reach the quorum in the `ordered_replicon` mode, it is possible to retrieve
   clusters of genes from the *rejected_candidates.tsv* file.


How to interpret the results from an `unordered` search?
--------------------------------------------------------

As mentioned above, in the `unordered` search mode, the inference of a system's presence is only based on the list of components found in the protein dataset.
Thus, the kind of search specificity provided when using the genomic context
(components next to each other are more likely to be part of a same system's occurrence) is not within reach.

In the `unordered` search mode, the number of proteins selected as system's components
(based on the filtering of HMM profiles' similarity search) is reported.
We decided to report all kinds of system's components, including the `forbidden` ones in order to raise awareness of
the user -> even if all constraints are met for the system's inference
(here, the quorum: minimal number of components), it cannot be excluded that a `forbidden`
component would lie next to the *bona fide* components (`mandatory` and `accessory` ones) in the genome...

In the end, the `unordered` search mode provides an idea as to whether the **genetic potential** for
a given system is found in the set of proteins analysed, with no attempt to assign proteins to particular systems' occurrences,
nor guarantee as to whether `forbidden` components should be considered for the potential occurrences.


How to search for multiple systems at once?
-------------------------------------------

- It is possible to search for only some systems from a macsy-model package. In this case, the command-line should be formed as follows:

.. code-block:: text

   macsyfinder --models TXSS Flagellum T2SS --sequence-db mygenomes.fasta --db-type gembase

This would run the search of the systems "Flagellum" and "T2SS" in the dataset "mygenomes.fasta".


- To run the search of all the models contained in a macsy-model package, use the following:

.. code-block:: text

   macsyfinder --models TXSS all --sequence-db mygenomes.fasta --db-type gembase
   macsyfinder --models CRISPRCas all --sequence-db mygenomes.fasta --db-type gembase
   macsyfinder --models CRISPRCas/typing all --sequence-db mygenomes.fasta --db-type gembase

You can see that the `all` keyword can not only be applied to an entire macsy-model package and its entire hierarchy,
but can also be ran on all the systems from a macsy-model sub-directory.


When can the option `--previous-run` be used?
---------------------------------------------

The option `--previous-run` enables to avoid running the HMM profile search and the hits extraction when the set
of systems to search and the replicons to analyse are exactly the same between runs.
This enables to alter the features of the systems to be searched for,
i.e. basically any feature found in the XML file of the corresponding models:

- the maximal distance allowed between components to be considered as part of a same locus `--inter-gene-max-space`
- the minimal number of components to be found to infer a full system `--min-mandatory-genes-required` and `--min-genes-required`
- the general genomic architecture of the system `--multi-loci`

This also means that there are a number of options that are incompatible with  `--previous-run`, including:

.. code-block:: text

   --config, --sequence-db, --profile-suffix, --res-extract-suffix, --e-value-res, --db-type, --hmmer



Which output file to be used to get ONE solution?
-------------------------------------------------

Since version 2 of MacSyFinder, a combinatorial exploration of the possible sets of systems is performed.
A scoring scheme has been set up to differentiate between solutions,
in order to provide the user with the most complete set of systems as possible given the searched models.
This score is maximal for the "best solution". This also means that some solutions might get the same maximal score.
In this case, one can wonder how to find all the equivalent solutions, and an other,
how to simply pick one solution among the best, whichever it is.
We thus propose several kind of :ref:`output files <ordered_outputs>`.

- All equivalent best solutions are found in the `all_best_solutions.tsv` file.
- One best solution is given in the `best_solution.tsv` file.

.. note::

   For those more familiar with the output files from MacSyFinder v1, the file `best_solution.tsv` is the closest from
   the previous output file `macsyfinder.report`.


Where to find MacSyFinder models?
---------------------------------

Since version 2, there is a tool to enable the download and installation of published models from a repository: the `macsydata` tool.

See :ref:`here for details <macsydata>` on how to use it.



What are the rules for options precedence?
------------------------------------------

MacSyFinder offers many ways to parametrize the systems' search: through the command-line,
through various configuration files (for the models, for the run, etc...).
It offers a large control over the search engine. But it also means you can get lost in configuration. ;-)

Here is a recap of the rules for options precedence. In a general manner, the command line always wins.

The precedence rules between the different levels of configuration are:

.. code-block:: text

 system < home < model < project < --cfg-file | --previous-run < command line options

* **system**: the `<macsylib>.conf` file either in ${VIRTUAL_ENV}/etc/<macsylib>/
  in case of a *virtualenv* this configuration affects only the MacSyFinder version installed in this virtualenv
* **home**:  the `~/.<macsylib>/<macsylib>.conf` file
* **model**: the `model_conf.xml` file at the root of the model package
* **project**: the `<macsylib>.conf` file found in the directory where the `macsylib` command was run
* **cfgfile**: any configuration file specified by the user on the command line
* **previous-run**: the `<macsylib>.conf` file found in the results directory of the previous run

