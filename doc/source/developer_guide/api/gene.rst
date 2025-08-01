.. MacSyLib - python library that provide functions for
    detection of macromolecular systems in protein datasets
    using systems modelling and similarity search.
    Authors: Sophie Abby, Bertrand Néron
    Copyright © 2014-2025 Institut Pasteur (Paris) and CNRS.
    See the COPYRIGHT file for details
    MacsyLib is distributed under the terms of the GNU General Public License (GPLv3).
    See the COPYING file for details.

.. _gene_module:

****
gene
****

The :ref:`Gene object <gene>` represents genes encoding the protein components of a Model.
There is 2 kind of gene The ``CoreGene`` (:class:`macsylib.gene.CoreGene`) which must be unique given a name.
A ``CoreGene`` must have a corresponding HMM protein profile.
A ``ModelGene`` encapsulate a CoreGene and is linked to a Model.

.. warning::
    To optimize computation and to avoid concurrency problems when we search several models,
    each gene must be instantiated only once, and stored in gene_bank.
    gene_bank is a :class:`macsylib.gene.GeneBank` object.
    The gene_bank and model_bank (:class:`macsylib.model.ModelBank` object)
    are instantiated in :func:`macsylib.search_systems.search_systems` function
    and filled by a definition_parser (:class:`macsylib.defintion_parser.DefinitionParser`)

Example to get a CoreGene object: ::

    # get a model object
    model_a = model_bank("TXSS/model_a")
    model_b = model_bank("TXSS/model_b")

    # get of a <CoreGene> object
    t2ss =  gene_bank[("TXSS", "T2SS")]
    pilO = gene_bank[("TXSS", "pilO")]

to create a ModelGene ::

    modelA_t2ss(t2ss, model_A)
    modelA_pilO(pilO, model_a, loner=True, inter_gene_max_space=12)
    modelB_pilO(pilO, model_b, inter_gene_max_space=5)

There is only *one* instance of CoreGene with a given name (model family name, gene name) in one MSF run.
But several instance of a ModelGene with the same name may exists.
Above, there is 2 <ModelGene> representing *pilO* one in model_a the second in model_b with different properties.

Exchangeable inherits from ModelGene.
Then a gene in some model is seen as a Gene, in some other models as an Exchangeable.
But there only one instance of the corresponding CoreGene.::

    core_sctn = gene_bank(("TXSS", "sctN"))
    core_sctn_flg = gene_bank(("TXSS", "sctN_FLG"))
    model_sctn = ModelGene(core_sctn, model_a)
    ex_sctn_flg = Exchangeable(core_stn_flg, model_sctn)
    model_sctn.add_exchangeable(ex_sctn_flg)

    model_sctn_flg = ModelGene(core_sctn_flg, model_b)

which means that in model_a the gene *sctn* can be functionally replaced by *sctn_flg*.
In Model_a it appear as an alternative to sctn but in model_B it appear as sctn_flg itself.
In one MacSyLib run several instances of ModelGene and/or Exchangeable with the same name may coexists .
But in A whole macsylib run there is only one instance core_sctn_flg and core_sctn.

.. _gene_api:

gene API reference
==================

GeneBank
========

 .. autoclass:: macsylib.gene.GeneBank
   :members:
   :private-members:
   :special-members:

.. _gene:

Gene
====

There is two classes to modelize a gene: :class:`macsylib.gene.CoreGene` and :class:`macsylib.gene.ModelGene`.
The CoreGene are created using the :class:`macsylib.gene.GeneBank` factory and there is only one instance
of a CoreGene with a given name.
Whereas several ModelGene with the same name can appear in different model and can have differents properties,
`loner` in one model and not in an other, have different `inter_gene_max_space` ...
The ModelGene is attached to the model and is composed of a CoreGene.

.. note::
    The :class:`macsylib.hit.Hit` object are link to a CoreGene, whereas the :class:`macsylib.hit.ValidHit` `ref_gene`
    attribute reference a :class:`macsylib.gene.ModelGene`


CoreGene
========

.. autoclass:: macsylib.gene.CoreGene
   :members:
   :private-members:
   :special-members:


ModelGene
=========

.. autoclass:: macsylib.gene.ModelGene
   :members:
   :private-members:
   :special-members:

.. _exchangeable_api:

Exchangeable
============

.. autoclass:: macsylib.gene.Exchangeable
   :members:
   :private-members:
   :special-members:


GeneStatus
==========

.. autoclass:: macsylib.gene.GeneStatus
   :members:
   :private-members:
   :special-members:
