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

import itertools
import logging
from collections import defaultdict, Counter
from operator import attrgetter

import macsylib.gene
from .error import MacsylibError
from .gene import ModelGene, GeneStatus
from .hit import Loner, LonerMultiSystem, get_best_hit_4_func, ModelHit, CoreHit, HitWeight
from .database import RepliconInfo
from .model import Model

_log = logging.getLogger(__name__)


"""
Module to build and manage Clusters of Hit
A cluster is a set of hits each of which hits less than inter_gene_max_space from its neighbor
"""


def _colocates(h1: ModelHit, h2: ModelHit, rep_info: RepliconInfo) -> bool:
    """
    compute the distance (in number of gene between) between 2 hits

    :param h1: the first hit to compute inter hit distance
    :param h2: the second hit to compute inter hit distance
    :return: True if the 2 hits spaced by lesser or equal genes than inter_gene_max_space.
             Managed circularity.
    """
    # compute the number of genes between h1 and h2
    dist = h2.position - h1.position - 1
    g1 = h1.gene_ref
    g2 = h2.gene_ref
    model = g1.model
    d1 = g1.inter_gene_max_space
    d2 = g2.inter_gene_max_space

    if d1 is None and d2 is None:
        inter_gene_max_space = model.inter_gene_max_space
    elif d1 is None:
        inter_gene_max_space = d2
    elif d2 is None:
        inter_gene_max_space = d1
    else:  # d1 and d2 are defined
        inter_gene_max_space = min(d1, d2)

    if 0 <= dist <= inter_gene_max_space:
        return True
    elif dist <= 0 and rep_info.topology == 'circular':
        # h1 and h2 overlap the ori
        dist = rep_info.max - h1.position + h2.position - rep_info.min
        return dist <= inter_gene_max_space
    return False


def scaffold_to_cluster(cluster_scaffold: list[ModelHit], model: Model, hit_weights: HitWeight) -> Cluster:
    """
    transform a list of ModelHit in a cluster if the hit colocalize and they are not all neutral
    and they do not code for same gene
    add the new cluster to the clusters

    :param cluster_scaffold: model hit to transform in cluster
    :param model: The model related to thus cluster
    :param hit_weights: the hit weight to compute scores
    :return: Cluster
    """
    gene_types = {hit.gene_ref.name for hit in cluster_scaffold}

    if len(gene_types) > 1:
        if all([_hit.gene_ref.status == GeneStatus.NEUTRAL for _hit in cluster_scaffold]):
            # contains different genes but all are neutral
            # we do not consider a group of neutral as a cluster
            _log.debug(f"{', '.join([h.id for h in cluster_scaffold])} "
                       f"is composed of only neutral. It's not a cluster.")
            return None
        else:
            return  Cluster(cluster_scaffold, model, hit_weights)
    else:
        cluster = Cluster(cluster_scaffold, model, hit_weights)
        if cluster.loner:
            # it's a group of one loner add as cluster
            # it will be squashed at  next step (_get_true_loners )
            # the hit transformation in loner is performed at the end when circularity and merging is done
            return cluster
        elif model.min_genes_required == 1:
            if cluster.hits[0].gene_ref.status == GeneStatus.NEUTRAL:
                # even min_genes_required == 1
                # a neutral alone is not a cluster
                _log.debug(f"{', '.join([h.id for h in cluster_scaffold])} "
                       f"is composed of only neutral. It's not a cluster.")
                return None
            else:
                return cluster
        else:
            _log.debug(f"({', '.join([h.id for h in cluster_scaffold])}) "
                       f"is composed of only type of gene {cluster_scaffold[0].gene_ref.name}. It's not a cluster.")
            return None


def clusterize_hits_on_distance_only(hits: list[ModelHit], model: Model, hit_weights: HitWeight, rep_info: RepliconInfo) -> list[Cluster]:
    """
    clusterize hit regarding the distance between them

    :param hits: the hits to clusterize
    :param model: the model to consider
    :param hit_weights: the hit weight to compute the score
    :param rep_info: The information on the replicon
    :return: the clusters
    """
    clusters = []
    cluster_scaffold = []
    # sort hits by increasing position and then descending score
    hits.sort(key=lambda h: (h.position, - h.score))
    # remove duplicates hits (several hits for the same sequence),
    # keep the first one, this with the best score
    # position == sequence rank in replicon
    hits = [next(group) for pos, group in itertools.groupby(hits, lambda h: h.position)]
    if hits:
        hit = hits[0]
        cluster_scaffold.append(hit)
        previous_hit = cluster_scaffold[0]

        for m_hit in hits[1:]:
            if _colocates(previous_hit, m_hit, rep_info):
                cluster_scaffold.append(m_hit)
            else:
                # close the current scaffold
                cluster = scaffold_to_cluster(cluster_scaffold, model, hit_weights)
                if cluster is not None:
                    clusters.append(cluster)
                # open new scaffold
                cluster_scaffold = [m_hit]
            previous_hit = m_hit

        # close the last current cluster
        cluster = scaffold_to_cluster(cluster_scaffold, model, hit_weights)
        if cluster is not None:
            clusters.append(cluster)
        else:
            # handle circularity
            if rep_info.topology == 'circular':
                # if there are clusters
                # maybe the last hit in scaffold collocate with the first hit of the first cluster
                if clusters and _colocates(cluster_scaffold[-1], clusters[0].hits[0], rep_info):
                    new_cluster = Cluster(cluster_scaffold, model, hit_weights)
                    clusters[0].merge(new_cluster, before=True)
                elif _colocates(cluster_scaffold[-1], hits[0], rep_info):
                    # maybe it colocalize with the first hit (which was not a cluster)
                    cluster_scaffold.append(hits[0])
                    cluster = scaffold_to_cluster(cluster_scaffold, model, hit_weights)
                    if cluster is not None:
                        clusters.append(cluster)
        # handle circularity
        if rep_info.topology == 'circular' and len(clusters):
            if _colocates(clusters[-1].hits[-1], clusters[0].hits[0], rep_info):
                clusters[0].merge(clusters[-1], before=True)
                clusters = clusters[:-1]
    return clusters


def is_a(hit: ModelHit | CoreHit, ref_hits: set[str]) -> bool:
    """

    :param hit: The hit to check
    :param ref_hits: the gene name of the reference hit
    :return: True if the *hit* belong to the reference hits, False otherwise
    """
    return hit.gene_ref.name in ref_hits


def closest_hit(hit: ModelHit, ref_hits:list[ModelHit]) -> ModelHit:
    """

    :param hit: the hit
    :param ref_hits: The reference hits. the distance between *hit* and each *ref_hit*
                    will be computed. the closest *ref_hit* will be returned
    :return: The closest *ref_hit* to the hit. If two *ref_hits* are equidistant form the *hit*
             return those with the lowest position.
             for isnstance::

                position     40  20  60
                closest_hit( ref_hit, [H1, H2]

            will return *H1*
    """
    ref_hits = sorted(ref_hits, key=attrgetter('position'))
    closest_int = ref_hits[0]
    closest_dist = abs(hit.position - closest_int.position)
    for integrase in ref_hits[1:]:
        distance = abs(hit.position - integrase.position)
        if distance < closest_dist:
            closest_dist = distance
            closest_int = integrase
    return closest_int


def split_cluster_on_key_genes(key_genes: set[str], cluster: Cluster) -> list[Cluster]:
    """
    split a Cluster containing several key genes to have one cluster per key genes, with their closest hits

    For instance if a set of gene clusterize as following (we considering that all gene are 10 genea between next one::

        positions  10   20    30   40   50    60     70
        genes       A   KG1    B    C    D    KG2     E

    The resulting cluster after split around the 2 KG (key genes)::

        c1 = [A, KG1, B, C], c2 = [D, KG2, E]

    The question is for gene C which is equidistant from KG1 KG2
    C will be clustered with the most left cluster

    :param key_genes: the gene names which be seed for cluster
    :param cluster: The cluster to split
    :return:
    """
    clusters = []
    scaffolds = defaultdict(list)
    key_gene_hits = []
    not_key_genes_hits = []
    for hit in cluster.hits:
        if is_a(hit, key_genes):
            key_gene_hits.append(hit)
        else:
            not_key_genes_hits.append(hit)


    if not key_gene_hits:
        return []
    for hit in not_key_genes_hits:
        closest_int = closest_hit(hit, key_gene_hits)
        scaffolds[closest_int].append(hit)

    for integrase, scaffold in scaffolds.items():
        scaffold.append(integrase)
        scaffold.sort(key=lambda h: h.position)
        cluster = scaffold_to_cluster(scaffold, cluster.model, cluster.hit_weights)
        clusters.append(cluster)
    clusters.sort(key=lambda c: c.hits[0].position)
    return clusters


def clusterize_hits_around_key_genes(key_genes: set[str],
                                     hits: list[ModelHit],
                                     model: Model,
                                     hit_weights: HitWeight,
                                     rep_info: RepliconInfo) -> list[Cluster]:
    """
    clusterize hit regarding the distance between them and around key_gene

    :param hits: the hits to clusterize
    :type hits: list of :class:`macsylib.model.ModelHit` objects
    :param model: the model to consider
    :type model: :class:`macsylib.model.Model` object
    :param hit_weights: the hit weight to compute the score
    :type hit_weights: :class:`macsylib.hit.HitWeight` object
    :type rep_info: :class:`macsylib.Indexes.RepliconInfo` object

    :return: the clusters
    :rtype: list of :class:`macsylib.cluster.Cluster` objects.
    """

    dist_cls = clusterize_hits_on_distance_only(hits, model, hit_weights, rep_info)
    key_gene_clst = []
    for clst in dist_cls:
        key_gene_nb = sum([1 for hit in clst.hits if is_a(hit, key_genes)])
        if key_gene_nb == 0:
            continue
        elif key_gene_nb == 1:
            key_gene_clst.append(clst)
        else:
            clusters = split_cluster_on_key_genes(key_genes, clst)
            key_gene_clst.extend(clusters)
    key_gene_clst.sort(key=lambda c: c.hits[0].position)
    return key_gene_clst


def _get_true_loners(clusters: list[Cluster]) -> tuple[dict[str: Loner | LonerMultiSystem], list[Cluster]]:
    """
    We call a True Loner a Cluster composed of one or several hit related to the same gene tagged as loner
    (by opposition with hit representing a gene tagged loner but include in cluster with several other genes)

    :param clusters: the clusters
    :return: tuple of 2 elts

             * dict containing true clusters  {str func_name : :class:`macsylib.hit.Loner | :class:`macsylib.hit.LonerMultiSystem` object}
             * list of :class:`macsylib.cluster.Cluster` objects
    """
    def add_true_loner(clstr: Cluster) -> None:
        """
        Add the hit of the Cluster clstr to the true_loners
        The clstr must contain only one hit or a stretch of same gene.
        :param clstr:
        """
        hits = clstr.hits
        clstr_len = len(hits)
        if clstr_len > 1:
            _log.warning(f"Squash cluster of {clstr_len} {clstr[0].gene_ref.name} loners "
                         f"({hits[0].position} -> {hits[-1].position})")
        func_name = clstr[0].gene_ref.alternate_of().name
        if func_name in true_loners:
            true_loners[func_name].extend(hits)
        else:
            true_loners[func_name] = hits

    ###################
    # get True Loners #
    ###################
    # true_loner is a hit which encode for a gene tagged as loner
    # and which does NOT clusterize with some other hits of interest
    true_clusters = []
    true_loners = {}
    if clusters:
        model = clusters[0].model
        hit_weights = clusters[0].hit_weights
        for clstr in clusters:
            if clstr.loner:
                # it's  a true Loner or a stretch of same loner
                add_true_loner(clstr)
            else:
                # it's a cluster of 1 hit
                # but it's NOT a loner
                # min_genes_required == 1
                true_clusters.append(clstr)

        for func_name, loners in true_loners.items():
            # transform ModelHit in Loner
            true_loners[func_name] = []
            for i, _ in enumerate(loners):
                if loners[i].multi_system:
                    # the counterpart have been already computed during the MS hit instantiation
                    # instead of the Loner not multisystem it include the hits which clusterize
                    true_loners[func_name].append(LonerMultiSystem(loners[i]))
                else:
                    counterpart = loners[:]
                    hit = counterpart.pop(i)
                    true_loners[func_name].append(Loner(hit, counterpart=counterpart))
            # replace List of Loners/MultiSystem by the best hit
            best_loner = get_best_hit_4_func(func_name, true_loners[func_name], key='score')
            true_loners[func_name] = best_loner

        true_loners = {func_name: Cluster([loner], model, hit_weights) for func_name, loner in true_loners.items()}
    return true_loners, true_clusters


def build_clusters(hits: list[ModelHit],
                   rep_info: RepliconInfo,
                   model: Model,
                   hit_weights: HitWeight) -> tuple[list[Cluster], dict[str: Loner | LonerMultiSystem]]:
    """
    From a list of filtered hits, and replicon information (topology, length),
    build all lists of hits that satisfied the constraints:

        * max_gene_inter_space
        * loner
        * multi_system

    If Yes create a cluster.
    A cluster contains at least two hits separated by less or equal than max_gene_inter_space
    Except for loner genes which are allowed to be alone in a cluster

    :param hits: list of filtered hits
    :param rep_info: the replicon to analyse
    :param model: the model to study
    :param hit_weights: the hit weight needed to compute the cluster score
    :return: list of regular clusters,
             the special clusters (loners not in cluster and multi systems)
    :rtype: tuple with 2 elements

            * true_clusters which is list of :class:`Cluster` objects
            * true_loners: a dict { str function: :class:macsylib.hit.Loner | :class:macsylib.hit.LonerMultiSystem object}
    """
    if hits:
        clusters = clusterize_hits_on_distance_only(hits, model, hit_weights, rep_info)
        # The hits in clusters are either ModelHit or MultiSystem
        # (they are cast during model.filter(hits) method)
        # the MultiSystem have no yet counterpart
        # which will compute once System will be computed
        # to take in account only hits in true system candidates
        # whereas the counterpart for loner & LonerMultiSystems during get_true_loners
        true_loners, true_clusters = _get_true_loners(clusters)

    else:  # there is not hits
        true_clusters = []
        true_loners = {}
    return true_clusters, true_loners


class Cluster:
    """
    Handle hits relative to a model which collocates
    """

    _id = itertools.count(1)

    def __init__(self, hits: list[CoreHit]|list[ModelHit], model, hit_weights) -> None:
        """

        :param hits: the hits constituting this cluster
        :param model: the model associated to this cluster
        :param hit_weights: the weight of the hit to compute the score
        """
        self._hits = hits
        self.model = model
        self._check_replicon_consistency()
        self._score = None
        self._genes_roles = None
        self._hit_weights = hit_weights
        self.id = f"c{next(self._id)}"


    def __len__(self) -> int:
        return len(self.hits)


    def __getitem__(self, index: str) -> CoreHit | ModelHit | Cluster:
        if isinstance(index, int):
            return self.hits[index]
        elif isinstance(index, slice):
            start, stop, step = index.indices((len(self._hits)))
            return self.__class__([self._hits[index] for index in range(start, stop, step)],
                                  self.model,
                                  self._hit_weights)
        else:
            raise TypeError(f"{self.__class__.__name__} indices must be integers or slices, not {type(index).__name__}")


    @property
    def hits(self) -> list[CoreHit | ModelHit]:
        """

        :return: the hits sorted by the increasing position
        """
        return self._hits[:]


    @hits.setter
    def hits(self, hits: list[CoreHit | ModelHit]) -> None:
        """

        set cluster hits
        """
        self._hits = hits


    @property
    def hit_weights(self) -> HitWeight:
        """

        :return: the different weight for the hits used to compute the score
        """
        return self._hit_weights


    @property
    def loner(self) -> bool:
        """

        :return: True if this cluster is made of only some hits representing the same gene and this gene is tag as loner
                 False otherwise:

                 - contains several hits coding for different genes
                 - contains one hit but gene is not tag as loner (max_gene_required = 1)
        """
        # need this method in build_cluster before to transform ModelHit in Loner
        # so cannot rely on Loner type
        # beware return True if several hits of same gene composed this cluster (I use a set!)
        return len({h.gene_ref.name for h in self.hits}) == 1 and self.hits[0].gene_ref.loner

    @property
    def multi_system(self) -> bool:
        """
        :return: True if this cluster is made of only one hit representing a multi_system gene
                 False otherwise:

                 - contains several hits
                 - contains one hit but gene is not tag as loner (max_gene_required = 1)
        """

        # by default gene_ref.multi_system == gene_ref.alternate_of().multi_system
        return len(self) == 1 and self.hits[0].gene_ref.multi_system


    def _check_replicon_consistency(self) -> None:
        """
        :raise: MacsylibError if all hits of a cluster are NOT related to the same replicon
        """
        rep_name = self.hits[0].replicon_name
        if not all([h.replicon_name == rep_name for h in self.hits]):
            msg = "Cannot build a cluster from hits coming from different replicons"
            _log.error(msg)
            raise MacsylibError(msg)


    def __contains__(self, m_hit: ModelHit) -> bool:
        """

        :param m_hit: The hit to test
        :return: True if the hit is in the cluster hits, False otherwise
        """
        return m_hit in self.hits


    @property
    def functions(self) -> frozenset[str]:
        """

        :return: The set of functions encoded by this cluster
                 *function* mean gene name or reference gene name for exchangeables genes
                 for instance ::

                     <model vers="2.0">
                         <gene a presence="mandatory"/>
                         <gene b presence="accessory"/>
                            <exchangeable>
                                <gene c />
                            </exchangeable>
                         <gene/>
                     </model>

                 the functions for a cluster corresponding to this model wil be {'a' , 'b'}
        """
        if self._genes_roles is None:
            self._genes_roles = frozenset({h.gene_ref.alternate_of().name for h in self.hits})
        return self._genes_roles


    def fulfilled_function(self, *genes: ModelGene | str) -> frozenset[str]:
        """

        :param genes: The genes which must be tested.
        :return: the common functions between genes and this cluster.
        """
        # we do not filter out neutral from the model
        genes_roles = self.functions
        functions = set()
        for gene in genes:
            if isinstance(gene, macsylib.gene.ModelGene):
                function = gene.name
            else:
                # gene is a string
                function = gene
            functions.add(function)
        return genes_roles.intersection(functions)

    def count_function(self) -> Counter[str]:
        return Counter(h.gene_ref.alternate_of().name for h in self.hits)

    def merge(self, cluster: Cluster, before: bool = False) -> None:
        """
        merge the cluster param in this one. (do it in place)

        :param cluster:
        :param bool before: If False the hits of the cluster will be added at the end of this one,
                            Otherwise the cluster hits will be inserted before the hits of this one.
        :raise MacError: if the two clusters have not the same model
        """
        if cluster.model != self.model:
            raise MacsylibError("Try to merge Clusters from different model")
        else:
            if before:
                self._hits = cluster.hits + self.hits
            else:
                self._hits.extend(cluster.hits)

    @property
    def replicon_name(self) -> str:
        """

        :return: The name of the replicon where this cluster is located
        :rtype: str
        """
        return self.hits[0].replicon_name


    @property
    def score(self) -> float:
        """

        :return: The score for this cluster
        """
        if self._score is not None:
            return self._score
        else:
            seen_hits = {}
            _log.debug("===================== compute score for cluster =====================")
            for m_hit in self.hits:
                _log.debug(f"-------------- test model hit {m_hit.gene.name} --------------")

                # attribute a score for this hit
                # according to status of the gene_ref in the model: mandatory/accessory
                if m_hit.status == GeneStatus.MANDATORY:
                    hit_score = self._hit_weights.mandatory
                elif m_hit.status == GeneStatus.ACCESSORY:
                    hit_score = self._hit_weights.accessory
                elif m_hit.status == GeneStatus.NEUTRAL:
                    hit_score = self._hit_weights.neutral
                else:
                    raise MacsylibError(f"a Cluster contains hit {m_hit.gene.name} {m_hit.position}"
                                       f" which is neither mandatory nor accessory: {m_hit.status}")
                _log.debug(f"{m_hit.id} is {m_hit.status} hit score = {hit_score}")

                # weighted the hit score according to the hit match the gene or
                # is an exchangeable
                if m_hit.gene_ref.is_exchangeable:
                    hit_score *= self._hit_weights.exchangeable
                    _log.debug(f"{m_hit.id} is exchangeable hit score = {hit_score}")
                else:
                    hit_score *= self._hit_weights.itself

                if self.loner or self.multi_system:
                    hit_score *= self._hit_weights.out_of_cluster
                    _log.debug(f"{m_hit.id} is out of cluster (Loner) score = {hit_score}")

                # funct is the name of the gene if it code for itself
                # or the name of the reference gene if it's an exchangeable
                funct = m_hit.gene_ref.alternate_of().name
                if funct in seen_hits:
                    # count only one occurrence of each function per cluster
                    # the score use is the max of hit score for this function
                    if hit_score > seen_hits[funct]:
                        seen_hits[funct] = hit_score
                        _log.debug(f"{m_hit.id} code for {funct} update hit_score to {hit_score}")
                    else:
                        _log.debug(f"{m_hit.id} code for {funct} which is already take in count in cluster")
                else:
                    _log.debug(f"{m_hit.id} {m_hit.gene_ref.name} is not already in cluster")
                    seen_hits[funct] = hit_score

            hits_scores = seen_hits.values()
            score = sum(hits_scores)
            _log.debug(f"cluster score = sum({list(hits_scores)}) = {score}")
        _log.debug("===============================================================")
        self._score = score
        return score


    def __str__(self) -> str:
        """

        :return: a string representation of this cluster
        """
        rep = f"""Cluster:
- model = {self.model.name}
- replicon = {self.replicon_name}
- hits = {', '.join([f"({h.id}, {h.gene.name}, {h.position})" for h in self.hits])}"""
        return rep


    def replace(self, old: ModelHit, new: ModelHit) -> None:
        """
        replace hit old in this cluster by new one. (do it in place)
        beware the hits in a cluster are sorted by their position so if old hit and new hit have not same position
        the order will be changed

        :param old: the hit to replace
        :param new: the new hit
        :return: None
        """
        idx = self._hits.index(old)
        self._hits[idx] = new
