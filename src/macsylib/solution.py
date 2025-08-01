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

import itertools
import networkx as nx
from typing import Generator

from .system import System, RejectedCandidate
from .cluster import Cluster
from .hit import Loner, LonerMultiSystem


class Solution:
    """
    Handle Solution, a solution is a set of compatible Systems

    when compare solutions we check the following criteria

        1. The number of hits
        2. The number of systems
        3. The average of wholeness
        4. The hits position (is used ti give predictable output for unit tests)
    """

    def __init__(self, systems: list[System]) -> None:
        """
        :param systems: The list of system that composed this solution
        """
        self._systems = self._sorted_systems(systems)
        self._score = sum([syst.score for syst in self.systems])
        self._average_woleness = sum([sys.wholeness for sys in self.systems]) / len(self.systems)
        self._hits_number = sum([len(syst.hits) for syst in self.systems])
        self._hits_positions = [h.position for syst in self.systems for h in syst.hits]


    def _sorted_systems(self, systems: list[System]) -> list[System]:
        """
        sort the systems following the positions of th hits that composed the systems

        :param systems: the systems to sort
        :type systems: list of :class:`mcsypy.system.System` objects
        :return: a sorted copy of the *systems*
        :rtype: list of :class:`mcsypy.system.System` objects
        """
        sorted_sys = sorted(systems, key=lambda syst: ([h.position for h in syst.hits],
                                                       syst.model.fqn,
                                                       - syst.score)
                            )
        return sorted_sys


    @property
    def systems(self) -> list[System]:
        """"a sorted list of the *systems* that composed the solution"""
        return self._systems[:]


    @property
    def score(self) -> float:
        """The score of this solution"""
        return self._score


    @property
    def average_wholeness(self) -> float:
        """The average of the systems wholeness"""
        return self._average_woleness


    @property
    def hits_number(self) -> int:
        """The sum of the hits of each system in this solution"""
        return self._hits_number

    @property
    def hits_positions(self) -> list[int]:
        """The list of position of all hits of the solution"""
        return self._hits_positions

    def __len__(self) -> int:
        return len(self.systems)


    def __gt__(self, other) -> bool:
        return (self.hits_number, len(self), self.average_wholeness, self.hits_positions) > \
               (other.hits_number, len(other), other.average_wholeness, other.hits_positions)


    def __lt__(self, other) -> bool:
        return (self.hits_number, len(self), self.average_wholeness, self.hits_positions) < \
               (other.hits_number, len(other), other.average_wholeness, other.hits_positions)

    def __eq__(self, other) -> bool:
        return self.hits_number == other.hits_number and \
               len(self) == len(other) and \
               self.average_wholeness == other.average_wholeness and \
               self.hits_positions == other.hits_positions

    def __iter__(self) -> Generator:
        """
        Solution allow to iterate over the systems

        :return: generator
        """
        return (s for s in self.systems)


def find_best_solutions(systems: list[System]) -> tuple[list[Solution], float]:
    """
    Among the systems choose the combination of systems which does not share :class:`macsylib.hit.CoreHit`
    and maximize the sum of systems scores

    :param systems: the systems to analyse
    :return: the list of :class:`macsylib.solution.Solution` which represent one best solution then it's score.
    :rtype: tuple of 2 elements the best solutions and it's score

    """

    G = nx.Graph()
    # add nodes (vertices)
    G.add_nodes_from(systems)
    # let's create an edges between compatible nodes
    for sys_i, sys_j in itertools.combinations(systems, 2):
        if sys_i.is_compatible(sys_j):
            G.add_edge(sys_i, sys_j)
    # find_cliques return a generator so the call to find cliques does not take time
    # but each time I ask for next item (in the loop below for instance)
    # nx compute the next clique so it can take time.
    # the number of maximal clique grow exponentiamly with the number of node
    # for instance for geneome  SYDY001.0321.00001.C001 ther is
    # 261 nodes, 22566 edges
    # 124 015 680 cliques
    cliques = nx.algorithms.clique.find_cliques(G)
    max_score = None
    for c in cliques:
        # it is important to sum the score of clusters
        # and creat a solution object only for solution I want to keep
        # because there could be lot of cliques
        # but only few will be kept (less than 5)
        # so the wide majority of these cliques will be thrown
        # if I create a Solution object for each clique I spend lot if time and memory to
        # instanciate new object to thrown them few line later :-(
        current_score = sum([s.score for s in c])
        if max_score is None or (current_score > max_score):
            max_score = current_score
            best_solutions = [Solution(c)]  # this solution is better start a new best_solutions
        elif current_score == max_score:
            best_solutions.append(Solution(c))
    # sort the solutions (cliques)
    solutions = sorted(best_solutions, reverse=True)
    return solutions, max_score


def combine_clusters(clusters: list[Cluster],
                     true_loners: dict[str: Loner | LonerMultiSystem],
                     multi_loci: bool = False) -> list[tuple[Cluster]]:
    """
    generate the combinations of clusters, with loners and multi systems

    :param clusters: the clusters to combines
    :param true_loners: the multi-systems hits
    :type true_loners: dict the name of the function code by hit gene_ref.alternate_of as key
                              and 1 :class:`macsylib.cluster.Cluster` with the best a
                              :class:`macsylib.hit.Loner` or
                              :class:`macsylib.hit.LonerMultiSystem` hit  as value
    :param multi_loci: True if the model is multi_loci false otherwise
    :return: all available combination of clusters
    :rtype: List of combination. a combination is a tuple of :class:`macsylib.cluster.Cluster` objects
    """
    if not clusters:
        cluster_combinations = []
    elif multi_loci:
        cluster_combinations = [itertools.combinations(clusters, i) for i in range(1, len(clusters) + 1)]
        cluster_combinations = list(itertools.chain(*cluster_combinations))
    else:
        cluster_combinations = [(clst,) for clst in clusters]

    # add loners
    loners_combinations = true_loners.items()
    loners_combinations = [itertools.combinations(loners_combinations, i) for i in
                           range(1, len(loners_combinations) + 1)]
    loners_combinations = itertools.chain(*loners_combinations)
    combination_w_loners = []
    for loner_comb in loners_combinations:
        loner_functions = [item[0] for item in loner_comb]
        loners = [item[1] for item in loner_comb]
        if cluster_combinations:
            for one_combination in cluster_combinations:
                to_add = True
                for clstr in one_combination:
                    if clstr.fulfilled_function(*loner_functions):
                        to_add = False
                        break
                if to_add:
                    combination_w_loners.append(tuple(list(one_combination) + loners))
        # we always add the loner
        # in case definition may contain only loners
        # or min_gene_required = 1 with one Loner
        combination_w_loners.append(tuple(loners))

    cluster_combinations += combination_w_loners

    return cluster_combinations


def combine_multisystems(rejected_candidates: list[RejectedCandidate], multi_systems: list[Cluster]):
    """

    :param rejected_candidates:
    :param multi_systems: sequence of :class:`macsylib.cluster.Cluster`
                          each cluster must be composed of only one :class:`macsylib.hit.MultiSystem` object
    :return: list of cluster combination with the multisystem
    :rtype: [(:class:`macsylib.cluster.Cluster` cluster1, cluster2, ...),
             (:class:`macsylib.cluster.Cluster` cluster3, cluster4, ...)]
    """
    # instead as clusters with loners
    # we have not to take in account rejected_cluster in new_comb
    # as they already have been challenged and rejected
    if isinstance(rejected_candidates, RejectedCandidate):
        rejected_candidates = [rejected_candidates]
    new_comb = []
    ms_combinations = [itertools.combinations(multi_systems, i) for i in range(1, len(multi_systems) + 1)]
    ms_combinations = list(itertools.chain(*ms_combinations))  # tuple of MultiSystem
    for rej_cand in rejected_candidates:
        for one_ms_combination in ms_combinations:
            combination_hits = {h for clst in one_ms_combination for h in clst.hits}
            functions = [h.gene_ref.alternate_of().name for h in combination_hits]
            if not rej_cand.fulfilled_function(*functions):
                new_comb.append(tuple(rej_cand.clusters + list(one_ms_combination)))
    return new_comb
