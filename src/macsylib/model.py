#########################################################################
# MacSyLib - Python library to detect macromolecular systems            #
#            in prokaryotes protein dataset using systems modelling     #
#            and similarity search.                                     #
#                                                                       #
# Authors: Sophie Abby, Bertrand Neron                                  #
# Copyright (c) 2014-2025  Institut Pasteur (Paris) and CNRS.           #
# See the COPYRIGHT file for details                                    #
#                                                                       #
# This file is part of MacSyLib package.                                #
#                                                                       #
# MacSyLib is free software: you can redistribute it and/or modify      #
# it under the terms of the GNU General Public License as published by  #
# the Free Software Foundation, either version 3 of the License, or     #
# (at your option) any later version.                                   #
#                                                                       #
# MacSyLib is distributed in the hope that it will be useful,           #
# but WITHOUT ANY WARRANTY; without even the implied warranty of        #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the          #
# GNU General Public License for more details .                         #
#                                                                       #
# You should have received a copy of the GNU General Public License     #
# along with MacSyLib (COPYING).                                        #
# If not, see <https://www.gnu.org/licenses/>.                          #
#########################################################################
from __future__ import annotations

import logging
from itertools import chain
from typing import Iterator, Callable

from .error import ModelInconsistencyError
from .registries import DefinitionLocation
from .hit import CoreHit, ModelHit
from .gene import GeneStatus, ModelGene

_log = logging.getLogger(__name__)


class ModelBank:
    """
    Store all Models objects.
    """

    def __init__(self) -> None:
        self._model_bank = {}


    def __getitem__(self, fqn: str) -> Model:
        """
        :param fqn: the fully qualified name of the model
        :return: the model corresponding to the fqn.
        :raise KeyError: if the model corresponding to the name does not exist
        """
        if fqn in self._model_bank:
            return self._model_bank[fqn]
        else:
            raise KeyError(fqn)


    def __contains__(self, model: Model) -> bool:
        """
        Implement the membership test operator

        :param model: the model to test
        :return: True if the model is in the Model factory, False otherwise
        """
        return model in self._model_bank.values()


    def __iter__(self) -> Iterator:
        """
        :return: an iterator object on the models contained in the bank
        """
        return iter(self._model_bank.values())


    def __len__(self) -> int:
        """
        :return: the number of models stored in the bank
        """
        return len(self._model_bank)


    def add_model(self, model: Model) -> None:
        """
        :param model: the model to add
        :raise: KeyError if a model with the same name is already registered.
        """
        if model.fqn in self._model_bank:
            raise KeyError(f"a model named {model.name} is already registered in the models' bank")
        else:
            self._model_bank[model.fqn] = model


class MetaModel(type):
    """
    control the different type of gene in a model ('mandatory, accessory, ....)
    and how to access to them.
    The type of genes are defined in the model itself via *_gene_category* class attribute.
    """

    def getter_maker(cat: str) -> Callable:
        """
        Create a property which allow to access to the gene corresponding of the cat of the model

        :param cat: the type of gene category to which we create the getter
        :return: unbound method
        """
        def getter(self):
            return getattr(self, f"_{cat}_genes")
        return getter


    def setter_maker(cat: str) -> Callable:
        """
        Create the method add_<cat>_gene which allow to add gene in the right category of the model

        :param cat: the type of gene category to which we create the mutator
        :return: unbound method
        """
        def setter(self, gene):
            gene.set_status(getattr(GeneStatus, cat.upper()))
            getattr(self, f"_{cat}_genes").append(gene)
        return setter


    def __call__(cls, *args, **kwargs):
        new_model_inst = super().__call__(*args, **kwargs)
        setattr(cls, "gene_category", property(lambda cls: cls._gene_category))
        for cat in new_model_inst.gene_category:
            # set the private attribute in the Model instance
            setattr(new_model_inst, f"_{cat}_genes", [])
            # set the public property in the Model class
            setattr(cls, f"{cat}_genes", property(MetaModel.getter_maker(cat)))
            # add method to add new gene in the Model class
            setattr(cls, f"add_{cat}_gene", MetaModel.setter_maker(cat))
        return new_model_inst


class Model(metaclass=MetaModel):
    """
    Handles a macromolecular model.

    Contains all its pre-defined characteristics expected to be fulfilled to predict a complete model:
        - component list (genes that are mandatory, accessory, neutral, forbidden)
        - quorum (number of genes)
        - genetic architecture

    """

    _gene_category = ('mandatory', 'accessory', 'neutral', 'forbidden')


    def __init__(self, fqn: str, inter_gene_max_space: int, min_mandatory_genes_required: int = None,
                 min_genes_required: int = None, max_nb_genes: int = None, multi_loci: bool = False) -> None:
        """
        :param fqn: the fully qualified name of the model CRISPR-Cas/sub-typing/CAS-TypeIE
        :param inter_gene_max_space: the maximum distance between two genes (**co-localization** parameter)
        :param min_mandatory_genes_required: the quorum of mandatory genes to define this model
        :param min_genes_required: the quorum of genes to define this model
        :param max_nb_genes: The number of gene to be considered as full system
                             Used to compute the wholeness.
                             If None the mx_nb_genes = mandatory + accessory
        :param multi_loci: if the systems can split in different loci on the genome
        :raise ModelInconsistencyError: if an error is found in model logic.
                                        For instance *genes_required* > *min_mandatory_genes_required*
        """
        self.fqn = fqn
        self._name = DefinitionLocation.split_fqn(self.fqn)[-1]
        self._inter_gene_max_space = inter_gene_max_space
        self._min_mandatory_genes_required = min_mandatory_genes_required
        self._min_genes_required = min_genes_required
        if self._min_mandatory_genes_required is not None and self._min_genes_required is not None:
            if self._min_genes_required < self._min_mandatory_genes_required:
                raise ModelInconsistencyError(f"{self.fqn}: min_genes_required '{self.min_genes_required}' "
                                              f"must be greater or equal than min_mandatory_genes_required "
                                              f"'{self.min_mandatory_genes_required}'"
                                              )
        self._max_nb_genes = max_nb_genes
        self._multi_loci = multi_loci


    def __str__(self) -> str:
        rep = f"name: {self.name}\n"
        rep += f"fqn: {self.fqn}\n"
        for cat in self._gene_category:
            rep += f"==== {cat} genes ====\n"
            for gene in getattr(self, f"{cat}_genes"):
                rep += f"{gene.name}\n"
        rep += "============== end pprint model ================\n"
        return rep


    def __hash__(self) -> int:
        """

        :return:
        """
        return hash(self.fqn)


    def __lt__(self, other: Model) -> bool:
        """
        :param other: the other model to compare
        :return: True if this fully qualified name is lesser than to other fully qualified name.
                 False otherwise.
        """
        return self.fqn < other.fqn


    def __gt__(self, other: Model) -> bool:
        """
        :param other: the other model to compare
        :return: True if this fully qualified name is greater than to other fully qualified name.
                 False otherwise.
        """
        return self.fqn > other.fqn


    def __eq__(self, other: Model) -> bool:
        """
        :param other: the other model to compare
        :return: True if this fully qualified name is equal to other fully qualified name.
                 False otherwise.
        """
        return self.fqn == other.fqn


    @property
    def name(self) -> str:
        """
        :return: the short name of this model
        """
        return self._name


    @property
    def family_name(self) -> str:
        """
        :return: the family name of the model for instance 'CRISPRCas' or 'TXSS'
        """
        return DefinitionLocation.root_name(self.fqn)


    @property
    def inter_gene_max_space(self) -> int:
        """
        :return: set the maximum distance allowed between 2 genes for this model
        """
        # self._inter_gene_max_space come from the definition (xml)
        # cfg_inter_gene_max_space come from the configuration command line option or conf file
        # so cfg_inter_gene_max_space must superseed self._inter_gene_max_space
        return self._inter_gene_max_space


    @property
    def min_mandatory_genes_required(self) -> int:
        """
        :return: get the quorum of mandatory genes required for this model
        """
        if self._min_mandatory_genes_required is None:
            return len(self.mandatory_genes)
        return self._min_mandatory_genes_required


    @property
    def min_genes_required(self) -> int:
        """
        :return: get the minimum number of genes to assess for the model presence.
        :rtype: integer
        """
        if self._min_genes_required is None:
            return len(self.mandatory_genes)
        return self._min_genes_required


    @property
    def max_nb_genes(self) -> int:
        """
        :return: the maximum number of genes to assess the model presence.
        """
        if self._max_nb_genes is None:
            max_nb_genes = len(self.mandatory_genes) + len(self.accessory_genes)
        else:
            max_nb_genes = self._max_nb_genes
        return max_nb_genes


    @property
    def multi_loci(self) -> bool:
        """
        :return: True if the model is authorized to be inferred from multiple loci, False otherwise
        """

        return self._multi_loci


    def get_gene(self, gene_name: str) -> ModelGene:
        """
        :param gene_name: the name of the gene to get
        :return: the gene corresponding to gene_name.
        :raise: KeyError the model does not contain any gene with name gene_name.
        """
        # create a dict with genes from all categories
        all_genes = {g.name: g for sublist in [getattr(self, f"{cat}_genes") for cat in self._gene_category]
                     for g in sublist}
        if gene_name in all_genes:
            return all_genes[gene_name]
        else:
            for gene in all_genes.values():
                for ex in gene.exchangeables:
                    if ex.name == gene_name:
                        return ex
        raise KeyError(f"Model {self.name} does not contain gene {gene_name}")


    def genes(self, exchangeable: bool = False) -> set[ModelGene]:
        """
        :param exchangeable: include exchangeable if True
        :return: all the genes described in the model.
                 with exchangeables if exchangeable is True.
                 otherwise only "first level" genes.
        """
        # we assume that a gene cannot appear twice in a model
        primary_genes = {g for sublist in [getattr(self, f"{cat}_genes") for cat in self._gene_category]
                         for g in sublist}
        if exchangeable:
            exchangeable_genes = [g_ex for g in primary_genes for g_ex in g.exchangeables]
            all_genes = set(chain(primary_genes, exchangeable_genes))
        else:
            all_genes = primary_genes
        return all_genes


    def filter(self, hits: list[CoreHit]) -> list[ModelHit]:
        """
        filter out the hits according to this model and cast them in ModelHit.
        The filtering is based on the name of CoreGene associated to hit
        and the name of ModelGene of the model
        (the name of the ModelGene is the name of the CoreGene embedded in the ModelGene)
        only the hits related to genes implied in the model are kept.

        :param hits: list of hits to filter
        :type hits: list of :class:`macsylib.report.CoreHit` object
        :return: list of hits
        :rtype: list of :class:`macsylib.report.Model` object
        """
        all_genes = {g.name: g for g in self.genes(exchangeable=True)}
        compatible_hits = []
        for hit in hits:
            if hit.gene.name in all_genes:
                gene = all_genes[hit.gene.name]
                mh = ModelHit(hit, gene, gene.status)
                compatible_hits.append(mh)

        return compatible_hits
