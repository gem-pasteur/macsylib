.. MacSyLib - python library that provide functions for
    detection of macromolecular systems in protein datasets
    using systems modelling and similarity search.
    Authors: Sophie Abby, Bertrand Néron
    Copyright © 2014-2025 Institut Pasteur (Paris) and CNRS.
    See the COPYRIGHT file for details
    MacSyLib is distributed under the terms of the GNU General Public License (GPLv3).
    See the COPYING file for details.


.. _outputs:

*************
Output format
*************

MacSyLib allow to produce different types of output files.

There are three types of output files:
  1. The main output files for the systems' search. They differ with the search mode (:ref:`ordered<ordered_outputs>` or :ref:`unordered<unordered_outputs>`).
  2. The :ref:`HMMER output files<hmmer-outputs-label>` (search of each systems' components), located in the `hmmer_results` folder.
  3. The internal :ref:`configuration and log files<logs_and_conf>`.


.. note::
    Each tabular output file contains a header line describing each column in the output.



.. _ordered_outputs:

Output files for the "ordered replicon(s)" search modes
-------------------------------------------------------

These output files can be generated when MacSyLib search proceeds on a set of proteins that are deemed to follow the order of their genes on replicons.
This corresponds to the two search modes *gembase* and *ordered_replicon*.


-------------------------
Systems detection results
-------------------------

Different types of output files can be generated, human-readable files ".txt", and tabulated files ".tsv". For the latter,
headers are provided with the content of the lines in the file.


  * :ref:`best_solution.tsv<best_solution_tsv>` - This file contains the **best solution found by MacSyLib** in terms of systems detected,
    under the form of a per-component, tabulated report file. A **solution** consists in a set of compatible systems (no components' overlap allowed).
    If multiple solutions showed a maximal score, a :ref:`ranking <sort_eqt_best_solution>` is established.

    To see potential other best solutions (in case several obtained the same highest score), see file :ref:`all_best_solutions.tsv<best_solution_tsv>`.

    To see all possible, candidate systems without further processing, see files `all_systems.txt` and `all_systems.tsv`.

    The `best_solution.tsv` file is the most similar to former V1 file `macsylib.report`.

  * :ref:`best_solution_loners.tsv <best_solution_loners_tsv>` and :ref:`best_solution_multisystems.tsv <best_solution_multisystems_tsv>` report
    hits which have been identified as loners or multi-systems which means that the corresponding gene is tagged as a 'loner' or 'multi-system' in the model definition
    and the hit is lot located in a cluster.

  * :ref:`best_solution_summary.tsv<best_solution_summary_tsv>` is a summary of the `best_solution.tsv` file, containing the number of systems detected in each replicon analysed.

  * :ref:`all_systems.txt<all_systems_txt>` - This file describes the search process of all possible candidate systems given the definitions in systems' models -
    without processing of the potential overlaps between candidate systems. This set of possible candidate systems are also given
    under the form of a tabulated file in `all_systems.tsv`.

  * :ref:`rejected_candidates.tsv<rejected_candidates_tsv>` and :ref:`rejected_candidates.txt<rejected_candidates_txt>` - This file lists candidate clusters (or a combination of clusters) components that were rejected by
    MacSyLib during the search process, and were thus not assigned to a candidate system. This set of clusters are also given under the form of tabulated file
    :ref:`rejected_candidates.tsv<rejected_candidates_tsv>`.

  * :ref:`all_best_solutions.tsv<best_solution_tsv>` - This file contains all possible best solutions under the form of a per-component, tabulated report file.
    To retrieve a single best solution as proposed by MacSyLib, see file `best_solution.tsv`.

  * :ref:`all_systems.tsv<all_systems_tsv>` - This file contains all possible candidate systems given the definitions -
    without processing of the potential overlaps between candidate systems, under the form of a per-component, tabulated report file. It corresponds
    to the tabulated version of the `all_systems.txt` file.


.. _all_systems_txt:

all_systems.txt
---------------


The file starts with some comments:

    - the version of MacSyLib used
    - the name of model package and version used
    - the command line used to produce this file

Then for each replicon, the systems detected are listed along with their description:

    - **system_id** - the unique identifier of a system
    - **model** - the model assigned to this system
    - **replicon** - the name of the replicon harbouring the system
    - **clusters** - the clusters composition of this system

        - each clusters is a list of tuple
        - each tuple is composed of:

            - the name of the matching gene(s) in the replicon
            - the name of the corresponding gene profile(s)
            - the position of the corresponding sequence(s) along the replicon

    - **occurrence** - the average number of occurrences of each components of the system (as a potential proxy to estimate whether there's the genetic potential for multiple systems in one)
    - **wholeness** - the percentage of the model's components that were found in this system
    - **loci nb** - the number of different loci constituting this system
    - **score** - the score of the system. See :ref:`here <combinatorial-exploration>` for more details
    - **systems components** - the number of occurrences of each model components
      in parenthesis the name of the matching profile
      in square brackets the name of other putative systems that would involve this gene

Here is an example of the `all_systems.txt` file:


.. code-block:: text

    # macsylib 20200217.dev
    # models: TFF-SF_final-0.1
    # macsylib --sequence-db DATA_TEST/sequences.prt --db-type=gembase --models-dir data/models/ --models TFF-SF_final all -w 4
    # Systems found:

    system id = VICH001.B.00001.C001_MSH_1
    model = TFF-SF_final/MSH
    replicon = VICH001.B.00001.C001
    clusters = [('VICH001.B.00001.C001_00406', 'MSH_mshI', 366), ('VICH001.B.00001.C001_00407', 'MSH_mshJ', 367), ('VICH001.B.00001.C001_00408', 'MSH_mshK', 368), ('VICH001.B.00001.C001_00409', '
    MSH_mshL', 369), ('VICH001.B.00001.C001_00410', 'MSH_mshM', 370), ('VICH001.B.00001.C001_00411', 'MSH_mshN', 371), ('VICH001.B.00001.C001_00412', 'MSH_mshE', 372), ('VICH001.B.00001.C001_0041
    3', 'MSH_mshG', 373), ('VICH001.B.00001.C001_00414', 'MSH_mshF', 374), ('VICH001.B.00001.C001_00415', 'MSH_mshB', 375), ('VICH001.B.00001.C001_00416', 'MSH_mshA', 376), ('VICH001.B.00001.C001
    _00417', 'MSH_mshC', 377), ('VICH001.B.00001.C001_00418', 'MSH_mshD', 378), ('VICH001.B.00001.C001_00419', 'MSH_mshO', 379), ('VICH001.B.00001.C001_00420', 'MSH_mshP', 380), ('VICH001.B.00001
    .C001_00421', 'MSH_mshQ', 381)]
    occ = 1
    wholeness = 0.941
    loci nb = 1
    score = 10.500

    mandatory genes:
            - MSH_mshA: 1 (MSH_mshA)
            - MSH_mshE: 1 (MSH_mshE)
            - MSH_mshG: 1 (MSH_mshG)
            - MSH_mshL: 1 (MSH_mshL)
            - MSH_mshM: 1 (MSH_mshM)

    accessory genes:
            - MSH_mshB: 1 (MSH_mshB)
            - MSH_mshC: 1 (MSH_mshC)
            - MSH_mshD: 1 (MSH_mshD)
            - MSH_mshF: 1 (MSH_mshF)
            - MSH_mshI: 1 (MSH_mshI)
            - MSH_mshI2: 0 ()
            - MSH_mshJ: 1 (MSH_mshJ)
            - MSH_mshK: 1 (MSH_mshK)
            - MSH_mshN: 1 (MSH_mshN)
            - MSH_mshO: 1 (MSH_mshO)
            - MSH_mshQ: 1 (MSH_mshQ)
            - MSH_mshP: 1 (MSH_mshP)

    neutral genes:

    ============================================================
    system id = VICH001.B.00001.C001_T4P_14
    model = TFF-SF_final/T4P
    replicon = VICH001.B.00001.C001
    clusters = [('VICH001.B.00001.C001_00476', 'T4P_pilT', 427), ('VICH001.B.00001.C001_00477', 'T4P_pilU', 428)], [('VICH001.B.00001.C001_00847', 'T4P_pilO', 778), ('VICH001.B.00001.C001_00850',
     'T4P_pilE', 781), ('VICH001.B.00001.C001_00851', 'T4P_fimT', 782), ('VICH001.B.00001.C001_00852', 'T4P_pilW', 783), ('VICH001.B.00001.C001_00853', 'T4P_pilX', 784), ('VICH001.B.00001.C001_00
    854', 'T4P_pilV', 785)], [('VICH001.B.00001.C001_02305', 'T4P_pilA', 2202), ('VICH001.B.00001.C001_02306', 'T4P_pilB', 2203), ('VICH001.B.00001.C001_02307', 'T4P_pilC', 2204), ('VICH001.B.000
    01.C001_02308', 'T4P_pilD', 2205)], [('VICH001.B.00001.C001_02502', 'MSH_mshM', 2391), ('VICH001.B.00001.C001_02505', 'T4P_pilQ', 2394), ('VICH001.B.00001.C001_02506', 'T4P_pilP', 2395), ('VI
    CH001.B.00001.C001_02507', 'T4P_pilO', 2396), ('VICH001.B.00001.C001_02508', 'T4P_pilN', 2397), ('VICH001.B.00001.C001_02509', 'T4P_pilM', 2398)]
    occ = 1
    wholeness = 0.944
    loci nb = 4
    score = 12.000

    mandatory genes:
            - T4P_pilE: 1 (T4P_pilE)
            - T4P_pilB: 1 (T4P_pilB)
            - T4P_pilC: 1 (T4P_pilC)
            - T4P_pilO: 2 (T4P_pilO, T4P_pilO)
            - T4P_pilQ: 1 (T4P_pilQ)
            - T4P_pilN: 1 (T4P_pilN)
            - T4P_pilT: 1 (T4P_pilT)
            - T4P_pilD: 1 (T4P_pilD [VICH001.B.00001.C001_T2SS_4])

    accessory genes:
            - T4P_pilA: 1 (T4P_pilA)
            - T4P_pilV: 1 (T4P_pilV)
            - T4P_pilY: 0 ()
            - T4P_pilW: 1 (T4P_pilW)
            - T4P_pilX: 1 (T4P_pilX)
            - T4P_fimT: 1 (T4P_fimT)
            - T4P_pilM: 1 (T4P_pilM)
            - T4P_pilP: 1 (T4P_pilP)
            - T4P_pilU: 1 (T4P_pilU)
            - MSH_mshM: 1 (MSH_mshM)

    neutral genes:


.. _all_systems_tsv:

all_systems.tsv
---------------


This corresponds to the tabulated version of the systems listed in `all_systems.txt`.
Each line corresponds to a "hit" that has been assigned to a detected system. It includes:

    * **replicon** - the name of the replicon it belongs to
    * **hit_id** - the unique identifier of the hit
    * **gene_name** - the name of the component identified by the hit
    * **hit_pos** - the position of the sequence in the replicon
    * **model_fqn** - the model fully-qualified name
    * **sys_id** - the unique identifier attributed to the detected system
    * **sys_loci** - the number of loci
    * **locus_num** - the number of the locus where is located this gene. Loners gene have a negative locus_num
    * **sys_wholeness** - the wholeness of the system
    * **sys_score** - the system score
    * **sys_occ** - the estimated number of system occurrences that could be potentially "filled" with this system's occurrence,
      based on the average number of each component found. A proxy for the genetic potential ton encode several systems from the set of components found in this one occurrence.
    * **hit_gene_ref** - the gene in the model whose this hit plays the role of
    * **hit_status** - the status of the component in the assigned system's definition
    * **hit_seq_len** - the length of the protein sequence matched by this hit
    * **hit_i_eval** - Hmmer statistics, the independent-evalue
    * **hit_score** - Hmmer score
    * **hit_profile_cov** - the percentage of the profile covered by the alignment with the sequence
    * **hit_seq_cov** - the percentage of the sequence covered by the alignment with the profile
    * **hit_begin_match** - the position in the sequence where the profile match begins
    * **hit_end_match** - the position in the sequence where the profile match ends
    * **counterpart** - the hit id of some other hit which are equivalent. Only loners and multi-systems hits have counterparts
    * **used_in** - whether the hit could be used in another system's occurrence

This file can be easily parsed using the Python `pandas <https://pandas.pydata.org/>`_ library. ::

    import pandas as pd

    systems = pd.read_csv("path/to/systems.tsv", sep='\t', comment='#')

.. note::
    Each system reported is separated from the others with a blank line to ease human reading.
    These lines are ignored during the parsing with pandas.

.. literalinclude:: ../_static/all_systems.tsv
   :language: text
   :lines: 1-15

.. note::
    If a loner component is not clustered with other genes, it will not be considered as part of a locus.
    Thus, its locus number will be a negative value (numbered from -1) and will not be counted in the variable `sys_loci` (number of loci for a system).
    See above lines for more details.

    .. code-block:: text

        GCF_000005845	GCF_000005845_026740	T4P_pilT	2674	TFF-SF/T4P	GCF_000005845_T4P_25	3	-1	0.556	7.800
        GCF_000005845	GCF_000005845_026930	T2SS_gspO	2693	TFF-SF/T4P	GCF_000005845_T4P_25	3	-2	0.556	7.800



.. _best_solution_tsv:

best_solution.tsv and all_best_solutions.tsv
--------------------------------------------


Since MacSyLib 2.0, a combinatorial exploration of solutions using sets of systems found is performed. We call best solution, the combination of systems offering the highest score.

The `best_solution.tsv` and `all_best_solutions.tsv` files have the same structure as the file `all_systems.tsv`, except that there is an extra column **sol_id** which is a
solution identifier added to the file `all_best_solutions.tsv`. The systems that have the same "sol_id" belong to a same solution.

As the files have the same structure as `all_systems.tsv`, they can also be parsed with pandas as shown above.

For the description of the fields of `best_solution.tsv`, see :ref:`above <all_systems_tsv>` those of the `all_systems.tsv` file.

For the `all_best_solutions.tsv`, each line corresponds to a "hit" that has been assigned to a detected system. It includes:

    * **sol_id** - the name of the solution it is part of **(only in** `all_best_solutions.tsv` **files)**
    * **replicon** - the name of the replicon it belongs to
    * **hit_id** - the unique identifier of the hit
    * **gene_name** - the name of the component identified by the hit
    * **hit_pos** - the position of the sequence in the replicon
    * **model_fqn** - the model fully-qualified name
    * **sys_id** - the unique identifier attributed to the detected system
    * **sys_loci** - the number of loci
    * **locus_num** - the number of the locus where is located this gene. Loners gene have negative locus_num
    * **sys_wholeness** - the wholeness of the system
    * **sys_score** - the system score
    * **sys_occ** - the estimated number of system occurrences that could be potentially "filled" with this system's occurrence, based on the average number of each component found. A proxy for the genetic potential ton encode several systems from the set of components found in this one occurrence.
    * **hit_gene_ref** - the gene in the model whose this hit plays the role of
    * **hit_status** - the status of the component in the assigned system's definition
    * **hit_seq_len** - the length of the protein sequence matched by this hit
    * **hit_i_eval** - Hmmer statistics, the independent-evalue
    * **hit_score** - Hmmer score
    * **hit_profile_cov** - the percentage of the profile covered by the alignment with the sequence
    * **hit_seq_cov** - the percentage of the sequence covered by the alignment with the profile
    * **hit_begin_match** - the position in the sequence where the profile match begins
    * **hit_end_match** - the position in the sequence where the profile match ends
    * **counterpart** - the hit id of some other hit which are equivalent. Only loners and multi-systems hits have counterparts
    * **used_in** - whether the hit could be used in another system's occurrence

.. note::
    Each system reported is separated from the others with a blank line to ease human reading.
    These lines are ignored during the parsing with pandas.

Example of `best_solution.tsv files`

.. literalinclude:: ../_static/best_solution.tsv
   :language: text
   :lines: 1-15

Example of `all_best_solutions.tsv files`

.. literalinclude:: ../_static/all_best_solutions.tsv
   :language: text
   :lines: 1-20, 28-35

.. note::
    If a loner component is not clustered with other genes, it will not be considered as part of a locus.
    Thus, its locus number will be a negative value (numbered from -1) and will not be counted in the variable `sys_loci` (number of loci for a system).
    See above lines for more details.

.. note::
    If several systems from same model use a loner (same gene) *msf* check that there is at least one occurrence of
    this hit for each system. If there are fewer hits than systems occurrence a warning is displayed in
    `best_solution.tsv` or `all_best_solution.tsv` as comment.
    So the file can be parsed with pandas without problem.

    .. code-block:: text

        1	GCF_000005845	GCF_000005845_030080	T2SS_gspO	3008	TFF-SF/T2SS	GCF_000005845_T2SS_1	1	1	0.857	9.000	1	T2SS_gspO	mandatory	225	4e-65	220.400	0.978	0.840	26	214

        # WARNING Loner: there is only 1 occurrence(s) of loner 'T4P_pilT' and 2 potential systems [GCF_000005845_T4P_9, GCF_000005845_T4P_13]

        2	GCF_000005845	GCF_000005845_000970	T4P_pilC	97	TFF-SF/T4P	GCF_000005845_T4P_11	2	1	0.389	4.760	1	T4P_pilC	mandatory	400	2.2e-105	353.100	0.991	0.830	62	393


.. _sort_eqt_best_solution:

.. note::
   In case multiple solutions have the exact same score, a sorting is performed among the best solutions, and the solution ranked 1st
   is reported in the `best_solution.tsv` and `best_solution.txt` files.
   The ranking is performed as follow:

   1. by the number of systems' components (hits) constituting the solution (most components first)
   2. by the number of systems (most systems in first)
   3. by the average of systems' wholeness
   4. by hits position. This criterion is mostly introduced to produce reproducible results between two runs.



.. _best_solution_summary_tsv:

best_solution_summary.tsv
-------------------------

This file is a concise view of which systems have been found in your replicons and how many per replicon.
It is based on **best_solution.tsv**.
The first two lines are comments that indicate the version of MacSyLib and the command line used to generate the results.
Then a table represented by tabulated text to separate columns, with the searched models in columns and the replicons scanned for the models in row.

.. literalinclude:: ../_static/best_solution_summary.tsv
       :language: text

as a `tsv` file it can be parsed easily using pandas::

    import pandas as pd
    solution = pd.read_csv('path to best_solution_summary.tsv', sep='\t', comment='#', index_col=0)


.. note::

        If you want to do the same operation but based on the *all_best_solutions.tsv* file,
        you can do it with the few lines of pandas below::

            import pandas as pd

            all_best_sol = '<macsylib_results_dir>/all_best_solutions.tsv'

            # read data from best_solution file
            data = pd.read_csv(all_best_sol, sep='\t', comment='#')

            # remove useless columns
            selection = data[['sol_id', 'replicon', 'sys_id', 'model_fqn']]

            # keep only one row per replicon, sys_id
            dropped = selection.drop_duplicates(subset=['sol_id', 'replicon', 'sys_id'])

            # count for each replicon which models have been detected and their occurrences
            summary = pd.crosstab(index=[dropped.sol_id, dropped.replicon], columns=dropped['model_fqn'])



    if you are not fluent in `pandas`, we provide you a tiny script `msf_summary.py` based on few lines above
    to do the job

    :download:`msf_summary.py <../_static/msf_summary.py>` .

    Then you can run the script ::

        python msf_summary.py <path_to_all_best_solutions.tsv>

    below an example of summary of `all_best_solutions.tsv`

    .. literalinclude:: ../_static/all_best_solutions_summary.tsv
       :language: text



.. _best_solution_loners_tsv:

best_solution_loners.tsv
------------------------

This file give an overview of all hits identified as Loner in the best_solution

    .. literalinclude:: ../_static/best_solution_loners.tsv
       :language: text



.. _best_solution_multisystems_tsv:

best_solution_multisystems.tsv
------------------------------

This file give an overview of all hits identified as multi-systems in the best_solution

    .. literalinclude:: ../_static/best_solution_multisystems.tsv
       :language: text


.. _rejected_candidates_txt:

rejected_candidates.txt
-----------------------

This file records all clusters or cluster combinations (if the "multi_loci" search mode is on)
which have been discarded and the reason why they were not selected as systems.

The header is composed of the MacSyLib version and the command line used
followed by the description of the cluster(s). The list of the hits composing the cluster is presented
at the end of the cluster or clusters' combination, followed by the reason why it has been discarded.

.. note::

    This file is in human readable format. If you need to parse the information about rejected candidates,
    use the tsv formatted file rejected_candidates.tsv

.. code-block:: text

    # <header of my choice see FAQ>
    # Rejected candidates:

    Cluster:
        - model: T4P
        - hits: (GCF_000005845_025680, T4P_pilW, 2568), (GCF_000005845_025690, T4P_fimT, 2569)
    Cluster:
        - model: T4P
        - hits: (GCF_000005845_026930, T2SS_gspO, 2693)
    Cluster:
        - model: T4P
        - hits: (GCF_000005845_030080, T2SS_gspO, 3008)
    This candidate has been rejected because:
    The quorum of mandatory genes required (4) is not reached: 1
    The quorum of genes required (5) is not reached: 3
    ============================================================
    Cluster:
        - model: Archaeal-T4P
        - hits: (GCF_000005845_019260, Archaeal-T4P_arCOG00589, 1926), (GCF_000005845_019310, Archaeal-T4P_arCOG02900, 1931)
    This candidate has been rejected because:
    The quorum of mandatory genes required (3) is not reached: 0
    The quorum of genes required (3) is not reached: 2
    ============================================================


.. _rejected_candidates_tsv:

rejected_candidates.tsv
-----------------------

This file contains same information as `rejected_candidates.txt` but in tsv format, so it's more convenient to parse it.
for instance with python and `pandas <https://pandas.pydata.org/>`_ library.::

    import pandas as pd
    pd.read_csv("path/to/rejected_candidates.tsv", sep-'\t', comment='#')

As other file the first lines are comments and provides informations to indicate how this file has been produced.

    - the macsylib version
    - the model package and version used
    - the command line used

then the following information separated by 'tabulation' character '\t'

    * **candidate_id** - An unique identifier of the candidate (for this run)
    * **replicon** - The name of the replicon
    * **model_fqn** - The model fully-qualified name
    * **cluster_id** - An unique identifier for the cluster constituting the candidate
    * **hit_id** - The identifier of the hit (as indicate in hmmer output)
    * **hit_pos** - The position of the sequence in the replicon
    * **gene_name** - The name of the component identified by the hit
    * **function** - The name of the gene for which it it fulfill the function.
    * **reasons** - The reasons why this cluster has been discarded. ther can be several reasons, in this case each reason are separated by '/'.

.. note::

    A rejected candidate can be constituted of

        * clusters (can have several clusters if the model is multi loci),
        * loners


Example of `rejected_candidates.tsv`

.. literalinclude:: ../_static/rejected_candidates.tsv
   :language: text
   :lines:  1-33



.. note::

    If a timeout is set to limit the time spent in best solution resolution. This timeout is applied per replicon.
    If the best solution resolution reach the timeout for a replicon, a WARNING is raised in `macysfinder.log`
    The warning is also report in the following files:

    * :ref:`best_solution.tsv<best_solution_tsv>`
    * :ref:`best_solution_summary.tsv<best_solution_summary_tsv>`
    * :ref:`all_best_solutions.tsv<best_solution_tsv>`
    * :ref:`all_systems.tsv<all_systems_tsv>` and :ref:`all_systems.txt<all_systems_txt>`
    * :ref:`rejected_candidates.tsv<rejected_candidates_tsv>` and :ref:`rejected_candidates.txt<rejected_candidates_txt>`

    for instance

    .. code-block:: text

        # <header of my choice see FAQ>
        #
        # WARNING: The replicon 'GCF_000006765' has been SKIPPED. Cannot be solved before timeout.
        #
        replicon  hit_id ...


.. _unordered_outputs:


Output files for the "unordered replicon" search mode
-----------------------------------------------------


-------------------------
Systems detection results
-------------------------

As for ordered replicons, several output files are provided.

    * :ref:`all_systems.txt<all_systems_txt_unordered>` - This file contains the description of candidate systems found.
    * :ref:`all_systems.tsv<all_systems_tsv_unordered>` - The same information as in `all_systems.txt` but in the tabulated tsv format.
    * :ref:`uncomplete_systems.txt<uncomplete_unordered>` - This file contains occurrences for systems that did not complete models' definitions and that were therefore not kept as candidate systems.


.. note::

  In this `unordered` search mode, there is no notion of order or distance of the components along the replicon. The clustering step
  is skipped by MacSyLib, and it is therefore "only" checked for each type of system being searched whether there is the genetic potential to fulfil its model definition.


.. _all_systems_txt_unordered:

all_systems.txt
---------------

This file contains potential systems for unordered replicon in human readable format.

In this file, for each component of each searched system's model, we report the number of hits found. For the description of the fields, see :ref:`above <all_systems_txt>`.

.. warning::
    In this mode the `forbidden` genes are reported here to the user. As we do not know if they co-localize (cluster) with the other genes they could
    be present in the replicon, yet far away - or very close on the contrary - to the potential system.

.. code-block:: text

    # <header of my choice see FAQ>
    # Systems found:

    This replicon contains genetic materials needed for system TFF-SF/T4P_single_locus


    system id = Unordered_T4P_single_locus_1
    model = TFF-SF/T4P_single_locus
    replicon = Unordered
    hits = [('GCF_000006845_000250', 'T4P_pilY', 25), ('GCF_000006845_000700', 'T4P_pilY', 70), ('GCF_000006845_001030', 'T4P_pilQ', 103), ('GCF_000006845_001040', 'T4P_pilP', 104), ('GCF_000006845_001050', 'T4P_pilO', 105), ('GCF_000006845_001060', 'T4P_pilN', 106), ('GCF_000006845_001070', 'T4P_pilM', 107), ('GCF_000006845_003200', 'T4P_pilU', 320), ('GCF_000006845_004190', 'T4P_fimT', 419), ('GCF_000006845_004200', 'T4P_pilV', 420), ('GCF_000006845_004210', 'T4P_pilW', 421), ('GCF_000006845_004220', 'T4P_pilX', 422), ('GCF_000006845_004230', 'T4P_pilA', 423), ('GCF_000006845_010160', 'T4P_pilA', 1016), ('GCF_000006845_012440', 'T4P_pilA', 1244), ('GCF_000006845_014270', 'T4P_pilC', 1427), ('GCF_000006845_014280', 'T4P_pilD', 1428), ('GCF_000006845_014310', 'T4P_pilB', 1431), ('GCF_000006845_016430', 'T4P_pilT', 1643), ('GCF_000006845_016440', 'T4P_pilU', 1644)]
    wholeness = 0.889

    mandatory genes:
        - T4P_pilE: 0 ()
        - T4P_pilB: 1 (T4P_pilB)
        - T4P_pilC: 1 (T4P_pilC)
        - T4P_pilO: 1 (T4P_pilO)
        - T4P_pilQ: 1 (T4P_pilQ)
        - T4P_pilN: 1 (T4P_pilN)
        - T4P_pilT: 1 (T4P_pilT)
        - T4P_pilD: 1 (T4P_pilD)

    accessory genes:
        - T4P_pilA: 3 (T4P_pilA, T4P_pilA, T4P_pilA)
        - T4P_pilV: 1 (T4P_pilV)
        - T4P_pilY: 2 (T4P_pilY, T4P_pilY)
        - T4P_pilW: 1 (T4P_pilW)
        - T4P_pilX: 1 (T4P_pilX)
        - T4P_fimT: 1 (T4P_fimT)
        - T4P_pilM: 1 (T4P_pilM)
        - T4P_pilP: 1 (T4P_pilP)
        - T4P_pilU: 2 (T4P_pilU, T4P_pilU)
        - MSH_mshM: 0 ()

    neutral genes:

    forbidden genes:

    Use ordered replicon to have better prediction.



.. _all_systems_tsv_unordered:

all_systems.tsv
---------------

This file contains the same information as in `all_systems.txt` but in `tsv` format. For the description of the fields, see :ref:`above <all_systems_tsv>`.


.. note::

    This file can be easily parsed with pandas::

        import pandas as pd
        pot_systems = pd.read_csv('all_systems.tsv', sep='\t', comment='#')


.. code-block:: text

    # <header of my choice see FAQ>
    # Likely Systems found:

    replicon	hit_id	gene_name	hit_pos	model_fqn	sys_id	sys_wholeness	hit_gene_ref	hit_status	hit_seq_len	hit_i_eval	hit_score	hit_profile_cov	hit_seq_cov	hit_begin_match	hit_end_match	used_in
    Unordered	GCF_000006845_014310	T4P_pilB	1431	TFF-SF/T4P_single_locus	Unordered_T4P_single_locus_1	0.889	T4P_pilB	mandatory	558	3.8e-178	589.000	0.964	0.731	146	553
    Unordered	GCF_000006845_014270	T4P_pilC	1427	TFF-SF/T4P_single_locus	Unordered_T4P_single_locus_1	0.889	T4P_pilC	mandatory	410	1.9e-131	434.800	0.997	0.817	72	406
    Unordered	GCF_000006845_014280	T4P_pilD	1428	TFF-SF/T4P_single_locus	Unordered_T4P_single_locus_1	0.889	T4P_pilD	mandatory	286	2.8e-82	272.300	1.000	0.829	28	264
    Unordered	GCF_000006845_001060	T4P_pilN	106	TFF-SF/T4P_single_locus	Unordered_T4P_single_locus_1	0.889	T4P_pilN	mandatory	199	2.3e-33	112.200	0.986	0.714	7	148
    Unordered	GCF_000006845_001050	T4P_pilO	105	TFF-SF/T4P_single_locus	Unordered_T4P_single_locus_1	0.889	T4P_pilO	mandatory	215	2.9e-37	124.800	0.980	0.693	23	171
    Unordered	GCF_000006845_001030	T4P_pilQ	103	TFF-SF/T4P_single_locus	Unordered_T4P_single_locus_1	0.889	T4P_pilQ	mandatory	723	1.9e-62	206.600	0.935	0.238	548	719
    Unordered	GCF_000006845_016430	T4P_pilT	1643	TFF-SF/T4P_single_locus	Unordered_T4P_single_locus_1	0.889	T4P_pilT	mandatory	347	6.9e-167	551.400	0.997	0.983	2	342
    Unordered	GCF_000006845_004190	T4P_fimT	419	TFF-SF/T4P_single_locus	Unordered_T4P_single_locus_1	0.889	T4P_fimT	accessory	221	2.7e-23	78.900	0.985	0.294	7	71
    Unordered	GCF_000006845_004230	T4P_pilA	423	TFF-SF/T4P_single_locus	Unordered_T4P_single_locus_1	0.889	T4P_pilA	accessory	162	8.6e-20	67.800	0.744	0.389	9	71
    Unordered	GCF_000006845_010160	T4P_pilA	1016	TFF-SF/T4P_single_locus	Unordered_T4P_single_locus_1	0.889	T4P_pilA	accessory	149	1.3e-15	54.300	0.821	0.430	5	68
    Unordered	GCF_000006845_012440	T4P_pilA	1244	TFF-SF/T4P_single_locus	Unordered_T4P_single_locus_1	0.889	T4P_pilA	accessory	129	1.5e-19	67.000	0.859	0.519	6	72
    Unordered	GCF_000006845_001070	T4P_pilM	107	TFF-SF/T4P_single_locus	Unordered_T4P_single_locus_1	0.889	T4P_pilM	accessory	371	3.3e-43	144.300	0.988	0.429	30	188
    Unordered	GCF_000006845_001040	T4P_pilP	104	TFF-SF/T4P_single_locus	Unordered_T4P_single_locus_1	0.889	T4P_pilP	accessory	181	2.7e-34	115.600	1.000	0.735	13	145
    Unordered	GCF_000006845_003200	T4P_pilU	320	TFF-SF/T4P_single_locus	Unordered_T4P_single_locus_1	0.889	T4P_pilU	accessory	376	2.2e-170	562.600	0.985	0.896	16	352
    Unordered	GCF_000006845_016440	T4P_pilU	1644	TFF-SF/T4P_single_locus	Unordered_T4P_single_locus_1	0.889	T4P_pilU	accessory	408	1.5e-127	421.800	0.994	0.833	40	379
    Unordered	GCF_000006845_004200	T4P_pilV	420	TFF-SF/T4P_single_locus	Unordered_T4P_single_locus_1	0.889	T4P_pilV	accessory	203	9.6e-16	54.600	1.000	0.276	14	69
    Unordered	GCF_000006845_004210	T4P_pilW	421	TFF-SF/T4P_single_locus	Unordered_T4P_single_locus_1	0.889	T4P_pilW	accessory	326	1.7e-10	38.000	0.517	0.190	17	78
    Unordered	GCF_000006845_004220	T4P_pilX	422	TFF-SF/T4P_single_locus	Unordered_T4P_single_locus_1	0.889	T4P_pilX	accessory	203	2.8e-18	62.600	0.983	0.286	17	74
    Unordered	GCF_000006845_000250	T4P_pilY	25	TFF-SF/T4P_single_locus	Unordered_T4P_single_locus_1	0.889	T4P_pilY	accessory	1006	2.2e-57	191.700	0.728	0.389	463	853
    Unordered	GCF_000006845_000700	T4P_pilY	70	TFF-SF/T4P_single_locus	Unordered_T4P_single_locus_1	0.889	T4P_pilY	accessory	1047	1.9e-57	191.900	0.721	0.362	516	894


.. _uncomplete_unordered:

uncomplete_systems.txt
----------------------

This file is created when a search is performed in the `unordered replicon` mode.
This file list models that probably do not have not full systems in the replicon(s).
For each model, the reason why it is not fulfilled is reported,
followed by the model description and the components found.

.. code-block:: text

    # <header of my choice see FAQ>
    # Unlikely Systems found:

    This replicon probably not contains a system TFF-SF/T2SS:
    The quorum of mandatory genes required (4) is not reached: 1
    The quorum of genes required (6) is not reached: 2

    system id = Unordered_T2SS_3
    model = TFF-SF/T2SS
    replicon = Unordered
    hits = [('GCF_000006845_002600', 'Tad_tadD', 260), ('GCF_000006845_014280', 'T4P_pilD', 1428), ('GCF_000006845_016430', 'T4P_pilT', 1643)]
    wholeness = 0.143

    mandatory genes:
            - T2SS_gspD: 0 ()
            - T2SS_gspE: 0 ()
            - T2SS_gspF: 0 ()
            - T2SS_gspG: 0 ()
            - T2SS_gspC: 0 ()
            - T2SS_gspO: 1 (T4P_pilD)

    accessory genes:
            - T2SS_gspM: 0 ()
            - T2SS_gspH: 0 ()
            - T2SS_gspI: 0 ()
            - T2SS_gspJ: 0 ()
            - T2SS_gspK: 0 ()
            - T2SS_gspN: 0 ()
            - T2SS_gspL: 0 ()
            - Tad_tadD: 1 (Tad_tadD)

    neutral genes:

    forbidden genes:
            - T4P_pilT: 1 (T4P_pilT)

    Use ordered replicon to have better prediction.

    ============================================================



.. _hmmer-outputs-label:

Hmmer results' output files
---------------------------
Raw Hmmer outputs are provided, as long with processed tabular outputs that include hits filtered as
specified by the user. For instance, the Hmmer search for SctC homologs with the corresponding profile
will result in the creation of two output files: "sctC.search_hmm.out" for the raw HMMER output file and
"sctC.res_hmm_extract" for the output file after processing/filtering of the HMMER results by MacSyLib.

The processed output file "sctC.res_hmm_extract" recalls on the first lines the parameters used for
hits filtering and relevant information on the matches, as in this example:

.. code-block:: text

  # gene: sctC extract from /Users/bob/macsylib_results/
        macsylib-20130128_08-57-46/sctC.search_hmm.out hmm output
  # profile length= 544
  # i_evalue threshold= 0.001000
  # coverage threshold= 0.500000
  # hit_id replicon_name position_hit hit_sequence_length gene_name gene_system i_eval score
        profile_coverage sequence_coverage begin end
  PSAE001c01_006940       PSAE001c01      3450    803     sctC    T3SS    1.1e-41 141.6
        0.588235  0.419676        395     731
  PSAE001c01_018920       PSAE001c01      4634    776     sctC    T3SS    9.2e-48 161.7
        0.976103  0.724227        35      596
  PSAE001c01_031420       PSAE001c01      5870    658     sctC    T3SS    2.7e-52 176.7
        0.963235  0.844985        49      604
  PSAE001c01_051090       PSAE001c01      7801    714     sctC    T3SS    1.9e-46 157.4
        0.571691  0.463585        374     704


.. _logs_and_conf:

Logs and configuration files
----------------------------

Three specific output files are systematically built, whatever the search mode, to store information on MacSyLib's execution:

 * **macsylib.conf** - contains the configuration information of the run. It is useful to recover all the parameters used for the run.
 * **macsylib.log** - the log file, contains raw information on the run. Please send it to us with any **bug report**.
