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

import os
import argparse
import random

from macsylib.error import MacsylibError
from macsylib.config import Config, MacsyDefaults
from macsylib.registries import ModelLocation
from macsylib.gene import CoreGene, ModelGene, Exchangeable, GeneStatus
from macsylib.profile import ProfileFactory
from macsylib.hit import CoreHit, ModelHit, Loner, MultiSystem, LonerMultiSystem, HitWeight
from macsylib.model import Model
from macsylib.database import RepliconInfo
from macsylib.cluster import (Cluster, build_clusters, _colocates, clusterize_hits_on_distance_only, _get_true_loners,
                              scaffold_to_cluster, is_a, closest_hit, split_cluster_on_key_genes,
                              clusterize_hits_around_key_genes)
from tests import MacsyTest


class TestBuildCluster(MacsyTest):

    def setUp(self) -> None:
        self.args = argparse.Namespace()
        self.args.sequence_db = self.find_data("base", "test_1.fasta")
        self.args.db_type = 'gembase'
        self.args.models_dir = self.find_data('models')
        self.args.res_search_dir = "blabla"

        self.cfg = Config(MacsyDefaults(), self.args)
        self.model_name = 'foo'
        self.model_location = ModelLocation(path=os.path.join(self.args.models_dir, self.model_name))
        self.profile_factory = ProfileFactory(self.cfg)
        self.hit_weights = HitWeight(**self.cfg.hit_weights())


    def test_build_clusters(self):
        # handle name, topology type, and min/max positions in the sequence dataset for a replicon and list of genes.
        # each genes is representing by a tuple (seq_id, length)"""
        rep_info = RepliconInfo('linear', 1, 60, [(f"g_{i}", i * 10) for i in range(1, 7)])

        #              fqn      , inter_gene_max_sapce
        model = Model("foo/T2SS", 11)

        core_genes = []
        model_genes = []
        for g_name in ('gspD', 'sctC', 'sctJ', 'sctN', 'abc'):
            core_gene = CoreGene(self.model_location, g_name, self.profile_factory)
            core_genes.append(core_gene)
            model_genes.append(ModelGene(core_gene, model))
        model_genes[4]._loner = True

        model.add_mandatory_gene(model_genes[0])
        model.add_mandatory_gene(model_genes[1])
        model.add_accessory_gene(model_genes[2])
        model.add_accessory_gene(model_genes[3])
        model.add_neutral_gene(model_genes[4])

        #     CoreHit(gene, hit_id, hit_seq_length, replicon_name, position, i_eval, score,
        #         profile_coverage, sequence_coverage, begin_match, end_match
        #                                                     pos     score
        h10 = CoreHit(core_genes[0], "h10", 10, "replicon_1", 10, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh10 = ModelHit(h10, gene_ref=model_genes[0], gene_status=GeneStatus.MANDATORY)
        h11 = CoreHit(core_genes[0], "h11", 10, "replicon_1", 10, 1.0, 11.0, 1.0, 1.0, 10, 20)
        mh11 = ModelHit(h11, gene_ref=model_genes[0], gene_status=GeneStatus.MANDATORY)

        h20 = CoreHit(core_genes[1], "h20", 10, "replicon_1", 20, 1.0, 20.0, 1.0, 1.0, 10, 20)
        mh20 = ModelHit(h20, gene_ref=model_genes[1], gene_status=GeneStatus.MANDATORY)
        h21 = CoreHit(core_genes[2], "h21", 10, "replicon_1", 20, 1.0, 21.0, 1.0, 1.0, 10, 20)
        mh21 = ModelHit(h21, gene_ref=model_genes[1], gene_status=GeneStatus.MANDATORY)

        h30 = CoreHit(core_genes[2], "h30", 10, "replicon_1", 30, 1.0, 30.0, 1.0, 1.0, 10, 20)
        mh30 = ModelHit(h30, gene_ref=model_genes[2], gene_status=GeneStatus.ACCESSORY)
        h31 = CoreHit(core_genes[1], "h31", 10, "replicon_1", 30, 1.0, 31.0, 1.0, 1.0, 10, 20)
        mh31 = ModelHit(h31, gene_ref=model_genes[1], gene_status=GeneStatus.MANDATORY)

        h50 = CoreHit(core_genes[2], "h50", 10, "replicon_1", 50, 1.0, 50.0, 1.0, 1.0, 10, 20)
        mh50 = ModelHit(h50, gene_ref=model_genes[2], gene_status=GeneStatus.ACCESSORY)
        h51 = CoreHit(core_genes[2], "h51", 10, "replicon_1", 50, 1.0, 51.0, 1.0, 1.0, 10, 20)
        mh51 = ModelHit(h51, gene_ref=model_genes[2], gene_status=GeneStatus.ACCESSORY)

        h60 = CoreHit(core_genes[2], "h60", 10, "replicon_1", 60, 1.0, 60.0, 1.0, 1.0, 10, 20)
        mh60 = ModelHit(h60, gene_ref=model_genes[2], gene_status=GeneStatus.ACCESSORY)
        h61 = CoreHit(core_genes[3], "h61", 10, "replicon_1", 60, 1.0, 61.0, 1.0, 1.0, 10, 20)
        mh61 = ModelHit(h61, gene_ref=model_genes[3], gene_status=GeneStatus.ACCESSORY)

        # case replicon is linear, 2 clusters
        hits = [mh10, mh11, mh20, mh21, mh30, mh31, mh50, mh51, mh60, mh61]
        random.shuffle(hits)
        true_clusters, special_clusters = build_clusters(hits, rep_info, model, self.hit_weights)
        self.assertEqual(len(true_clusters), 2)
        self.assertListEqual(true_clusters[0].hits, [mh11, mh21, mh31])
        self.assertListEqual(true_clusters[1].hits, [mh51, mh61])
        self.assertEqual(special_clusters, {})

        # case replicon is linear with a single hit (not loner) between 2 clusters
        h70 = CoreHit(core_genes[3], "h70", 10, "replicon_1", 70, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh70 = ModelHit(h70, gene_ref=model_genes[3], gene_status=GeneStatus.ACCESSORY)
        h80 = CoreHit(core_genes[4], "h80", 10, "replicon_1", 80, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh80 = ModelHit(h80, gene_ref=model_genes[4], gene_status=GeneStatus.NEUTRAL)
        hits = [mh10, mh11, mh20, mh21, mh50, mh51, mh70, mh80]
        random.shuffle(hits)
        true_clusters, special_clusters = build_clusters(hits, rep_info, model, self.hit_weights)
        self.assertEqual(len(true_clusters), 2)
        self.assertListEqual(true_clusters[0].hits, [mh11, mh21])
        self.assertListEqual(true_clusters[1].hits, [mh70, mh80])
        self.assertEqual(special_clusters, {})

        # replicon is linear, 3 clusters, the last one contains only one hit (loner h80)
        rep_info = RepliconInfo('linear', 1, 100, [(f"g_{i}", i*10) for i in range(1, 101)])
        h80 = CoreHit(core_genes[4], "h80", 10, "replicon_1", 80, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh80 = ModelHit(h80, gene_ref=model_genes[4], gene_status=GeneStatus.NEUTRAL)
        hits = [mh10, mh11, mh20, mh21, mh30, mh31, mh50, mh51, mh60, mh61, mh80]
        random.shuffle(hits)
        true_clusters, special_clusters = build_clusters(hits, rep_info, model, self.hit_weights)
        self.assertEqual(len(true_clusters), 2)
        self.assertListEqual(true_clusters[0].hits, [mh11, mh21, mh31])
        self.assertListEqual(true_clusters[1].hits, [mh51, mh61])
        self.assertEqual(len(special_clusters), 1)
        self.assertListEqual(special_clusters['abc'].hits, [mh80])

        # replicon is circular contains only one cluster
        rep_info = RepliconInfo('circular', 1, 60, [(f"g_{i}", i*10) for i in range(1, 7)])
        hits = [mh10, mh20, mh30]
        true_clusters, special_clusters = build_clusters(hits, rep_info, model, self.hit_weights)
        self.assertEqual(len(true_clusters), 1)
        self.assertListEqual(true_clusters[0].hits, [mh10, mh20, mh30])
        self.assertEqual(special_clusters, {})

        # replicon is circular the last cluster is merge  with the first So we have only one cluster
        rep_info = RepliconInfo('circular', 1, 60, [(f"g_{i}", i*10) for i in range(1, 7)])
        hits = [mh10, mh11, mh20, mh21, mh30, mh31, mh50, mh51, mh60, mh61]
        true_clusters, special_clusters = build_clusters(hits, rep_info, model, self.hit_weights)
        self.assertEqual(len(true_clusters), 1)
        self.assertListEqual(true_clusters[0].hits, [mh51, mh61, mh11, mh21, mh31])
        self.assertEqual(special_clusters, {})

        # replicon is circular the last hit is incorporate to the first cluster
        # mh80 is not considered as loner it is included in a cluster
        rep_info = RepliconInfo('circular', 1, 80, [(f"g_{i}", i*10) for i in range(1, 9)])
        h80 = CoreHit(core_genes[3], "h80", 10, "replicon_1", 80, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh80 = ModelHit(h80, gene_ref=model_genes[4], gene_status=GeneStatus.NEUTRAL)
        hits = [mh10, mh11, mh20, mh21, mh30, mh31, mh50, mh51, mh60, mh61, mh80]
        random.shuffle(hits)
        true_clusters, special_clusters = build_clusters(hits, rep_info, model, self.hit_weights)
        self.assertEqual(len(true_clusters), 2)
        self.assertListEqual(true_clusters[0].hits, [mh80, mh11, mh21, mh31])
        self.assertListEqual(true_clusters[1].hits, [mh51, mh61])
        self.assertEqual(special_clusters, {})

        # replicon is linear the last hit is not merged with the first cluster
        # mh80 is link to gene_4 'abc'. So, in this test, it's not a loner.
        rep_info = RepliconInfo('linear', 1, 62, [(f"g_{i}", i*10) for i in range(1, 7)])
        hits = [mh10, mh11, mh20, mh21, mh30, mh31, mh50, mh51, mh60, mh61]
        random.shuffle(hits)
        true_clusters, special_clusters = build_clusters(hits, rep_info, model, self.hit_weights)
        self.assertEqual(len(true_clusters), 2)
        self.assertListEqual(true_clusters[0].hits, [mh11, mh21, mh31])
        self.assertListEqual(true_clusters[1].hits, [mh51, mh61])
        self.assertEqual(special_clusters, {})

        # case replicon is linear, 2 clusters, the hits 11,21,31 and 51,61 are contiguous
        #                                                              pos
        h10 = CoreHit(core_genes[0], "h10", 10, "replicon_1", 10, 1.0, 11.0, 1.0, 1.0, 10, 20)
        mh10 = ModelHit(h10, gene_ref=model_genes[0], gene_status=GeneStatus.MANDATORY)
        h11 = CoreHit(core_genes[2], "h11", 10, "replicon_1", 11, 1.0, 21.0, 1.0, 1.0, 10, 20)
        mh11 = ModelHit(h11, gene_ref=model_genes[2], gene_status=GeneStatus.ACCESSORY)
        h12 = CoreHit(core_genes[1], "h12", 10, "replicon_1", 12, 1.0, 31.0, 1.0, 1.0, 10, 20)
        mh12 = ModelHit(h12, gene_ref=model_genes[1], gene_status=GeneStatus.MANDATORY)
        h50 = CoreHit(core_genes[2], "h50", 10, "replicon_1", 50, 1.0, 51.0, 1.0, 1.0, 10, 20)
        mh50 = ModelHit(h50, gene_ref=model_genes[2], gene_status=GeneStatus.ACCESSORY)
        h51 = CoreHit(core_genes[3], "h51", 10, "replicon_1", 51, 1.0, 61.0, 1.0, 1.0, 10, 20)
        mh51 = ModelHit(h51, gene_ref=model_genes[3], gene_status=GeneStatus.ACCESSORY)
        hits = [mh10, mh11, mh12, mh50, mh51]
        random.shuffle(hits)
        true_clusters, special_clusters = build_clusters(hits, rep_info, model, self.hit_weights)
        self.assertEqual(len(true_clusters), 2)
        self.assertListEqual(true_clusters[0].hits, [mh10, mh11, mh12])
        self.assertListEqual(true_clusters[1].hits, [mh50, mh51])
        self.assertEqual(special_clusters, {})

        # case replicon is linear
        # one cluster with one hit loner
        h80 = CoreHit(core_genes[4], "h80", 10, "replicon_1", 80, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh80 = ModelHit(h80, gene_ref=model_genes[4], gene_status=GeneStatus.NEUTRAL)
        hits = [mh80]
        true_clusters, special_clusters = build_clusters(hits, rep_info, model, self.hit_weights)
        self.assertEqual(len(true_clusters), 0)
        self.assertListEqual(special_clusters['abc'].hits, [mh80])

        # case replicon is linear
        # one cluster with one hit min_gene_required == 1
        # last hit is a cluster
        model = Model("foo/T2SS", 11, min_mandatory_genes_required=1, min_genes_required=1)
        core_genes = []
        model_genes = []
        for g_name in ('gspD', 'sctC'):
            core_gene = CoreGene(self.model_location, g_name, self.profile_factory)
            core_genes.append(core_gene)
            model_genes.append(ModelGene(core_gene, model))
        model.add_mandatory_gene(model_genes[0])
        model.add_accessory_gene(model_genes[1])

        h80 = CoreHit(core_genes[1], "h80", 10, "replicon_1", 80, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh80 = ModelHit(h80, gene_ref=model_genes[1], gene_status=GeneStatus.ACCESSORY)
        hits = [mh80]
        true_clusters, special_clusters = build_clusters(hits, rep_info, model, self.hit_weights)
        self.assertEqual(len(true_clusters), 1)
        self.assertListEqual(true_clusters[0].hits, [mh80])
        self.assertEqual(special_clusters, {})

        # case replicon is linear
        # one cluster with one hit min_gene_required == 1
        # first hit is a cluster
        model = Model("foo/T2SS", 11, min_mandatory_genes_required=1, min_genes_required=1)
        core_genes = []
        model_genes = []
        for g_name in ('gspD', 'sctC'):
            core_gene = CoreGene(self.model_location, g_name, self.profile_factory)
            core_genes.append(core_gene)
            model_genes.append(ModelGene(core_gene, model))
        model.add_mandatory_gene(model_genes[0])
        model.add_accessory_gene(model_genes[1])

        h10 = CoreHit(core_genes[0], "h10", 10, "replicon_1", 10, 1.0, 11.0, 1.0, 1.0, 10, 20)
        mh10 = ModelHit(h10, gene_ref=model_genes[0], gene_status=GeneStatus.MANDATORY)
        h80 = CoreHit(core_genes[1], "h80", 10, "replicon_1", 80, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh80 = ModelHit(h80, gene_ref=model_genes[1], gene_status=GeneStatus.ACCESSORY)
        hits = [mh10, mh80]
        random.shuffle(hits)
        true_clusters, special_clusters = build_clusters(hits, rep_info, model, self.hit_weights)
        self.assertEqual(len(true_clusters), 2)
        self.assertListEqual(true_clusters[0].hits, [mh10])
        self.assertListEqual(true_clusters[1].hits, [mh80])
        self.assertEqual(special_clusters, {})

        # case replicon is linear
        # one cluster with one hit min_gene_required != 1
        model = Model("foo/T2SS", 11, min_mandatory_genes_required=1, min_genes_required=2)
        core_genes = []
        model_genes = []
        for g_name in ('gspD', 'sctC'):
            core_gene = CoreGene(self.model_location, g_name, self.profile_factory)
            core_genes.append(core_gene)
            model_genes.append(ModelGene(core_gene, model))
        model.add_mandatory_gene(model_genes[0])
        model.add_accessory_gene(model_genes[1])
        h80 = CoreHit(core_genes[1], "h80", 10, "replicon_1", 80, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh80 = ModelHit(h80, gene_ref=model_genes[1], gene_status=GeneStatus.ACCESSORY)
        hits = [mh80]
        true_clusters, special_clusters = build_clusters(hits, rep_info, model, self.hit_weights)
        self.assertListEqual(true_clusters, [])
        self.assertEqual(special_clusters, {})

        # case replicon is linear, no hits
        true_clusters, special_clusters = build_clusters([], rep_info, model, self.hit_weights)
        self.assertListEqual(true_clusters, [])
        self.assertEqual(special_clusters, {})


    def test_colocates(self):
        rep_info = RepliconInfo('linear', 1, 60, [(f"g_{i}", i * 10) for i in range(1, 7)])

        #              fqn      , inter_gene_max_sapce
        model = Model("foo/T2SS", 7)

        core_genes = {}
        model_genes = {}
        for g_name in ('gspD', 'sctC', 'sctJ', 'sctN'):
            core_gene = CoreGene(self.model_location, g_name, self.profile_factory)
            core_genes[g_name] = core_gene
            model_genes[g_name] = ModelGene(core_gene, model)

        model.add_mandatory_gene(model_genes['gspD'])
        model.add_mandatory_gene(model_genes['sctC'])
        model.add_accessory_gene(model_genes['sctJ'])
        model.add_accessory_gene(model_genes['sctN'])

        h10 = CoreHit(core_genes['gspD'], "h10", 10, "replicon_1", 10, 1.0, 11.0, 1.0, 1.0, 10, 20)
        mh10 = ModelHit(h10, gene_ref=model_genes['gspD'], gene_status=GeneStatus.MANDATORY)

        h15 = CoreHit(core_genes['sctC'], "h15", 10, "replicon_1", 15, 1.0, 21.0, 1.0, 1.0, 10, 20)
        mh15 = ModelHit(h15, gene_ref=model_genes['sctC'], gene_status=GeneStatus.ACCESSORY)
        self.assertTrue(_colocates(mh10, mh15, rep_info))

        h20 = CoreHit(core_genes['sctJ'], "h20", 10, "replicon_1", 20, 1.0, 21.0, 1.0, 1.0, 10, 20)
        mh20 = ModelHit(h20, gene_ref=model_genes['sctJ'], gene_status=GeneStatus.ACCESSORY)
        self.assertFalse(_colocates(mh10, mh20, rep_info))

        model_genes['sctJ']._inter_gene_max_space = 10
        self.assertTrue(_colocates(mh10, mh20, rep_info))

        # case inter_gene_max_space is define at gene level sctJ and > than model intergene_max_space
        h30 = CoreHit(core_genes['sctJ'], "h30", 10, "replicon_1", 30, 1.0, 21.0, 1.0, 1.0, 10, 20)
        mh30 = ModelHit(h30, gene_ref=model_genes['sctJ'], gene_status=GeneStatus.ACCESSORY)
        model_genes['sctJ']._inter_gene_max_space = 30
        self.assertTrue(_colocates(mh10, mh30, rep_info))

        # same case but inter_gene_max_space is define in first gene
        h30 = CoreHit(core_genes['sctJ'], "h30", 10, "replicon_1", 30, 1.0, 21.0, 1.0, 1.0, 10, 20)
        mh30 = ModelHit(h30, gene_ref=model_genes['sctJ'], gene_status=GeneStatus.ACCESSORY)
        model_genes['sctJ']._inter_gene_max_space = 5
        h35 = CoreHit(core_genes['sctN'], "h35", 10, "replicon_1", 35, 1.0, 21.0, 1.0, 1.0, 10, 20)
        mh35 = ModelHit(h35, gene_ref=model_genes['sctN'], gene_status=GeneStatus.ACCESSORY)
        self.assertTrue(_colocates(mh30, mh35, rep_info))

        # case inter_gene_max_sapce is define at gene level sctJ and > than model intergene_max_space
        h30 = CoreHit(core_genes['sctJ'], "h30", 10, "replicon_1", 15, 1.0, 21.0, 1.0, 1.0, 10, 20)
        mh30 = ModelHit(h30, gene_ref=model_genes['sctJ'], gene_status=GeneStatus.ACCESSORY)
        model_genes['sctJ']._inter_gene_max_space = 5
        self.assertTrue(_colocates(mh10, mh30, rep_info))

        h30 = CoreHit(core_genes['sctJ'], "h30", 10, "replicon_1", 17, 1.0, 21.0, 1.0, 1.0, 10, 20)
        mh30 = ModelHit(h30, gene_ref=model_genes['sctJ'], gene_status=GeneStatus.ACCESSORY)
        model_genes['sctJ']._inter_gene_max_space = 5
        self.assertFalse(_colocates(mh10, mh30, rep_info))

        # case inter_gene_max_sapce is define at gene level sctJ and gspD use the smallest one
        model_genes['gspD']._inter_gene_max_space = 7
        h30 = CoreHit(core_genes['sctJ'], "h30", 10, "replicon_1", 17, 1.0, 21.0, 1.0, 1.0, 10, 20)
        mh30 = ModelHit(h30, gene_ref=model_genes['sctJ'], gene_status=GeneStatus.ACCESSORY)
        self.assertFalse(_colocates(mh10, mh30, rep_info))

        h30 = CoreHit(core_genes['sctJ'], "h30", 10, "replicon_1", 15, 1.0, 21.0, 1.0, 1.0, 10, 20)
        mh30 = ModelHit(h30, gene_ref=model_genes['sctJ'], gene_status=GeneStatus.ACCESSORY)
        model_genes['sctJ']._inter_gene_max_space = 5
        self.assertTrue(_colocates(mh10, mh30, rep_info))


    def test_clusterize_hits_on_distance_only(self):
        # handle name, topology type, and min/max positions in the sequence dataset for a replicon and list of genes.
        # each genes is representing by a tuple (seq_id, length)"""
        rep_info = RepliconInfo('linear', 1, 60, [(f"g_{i}", i * 10) for i in range(1, 7)])

        #              fqn      , inter_gene_max_sapce
        model = Model("foo/T2SS", 11)

        core_genes = []
        model_genes = []
        for g_name in ('gspD', 'sctC', 'sctJ', 'sctN', 'abc', 'tadZ'):
            core_gene = CoreGene(self.model_location, g_name, self.profile_factory)
            core_genes.append(core_gene)
            model_genes.append(ModelGene(core_gene, model))
        model_genes[4]._loner = True

        model.add_mandatory_gene(model_genes[0])
        model.add_mandatory_gene(model_genes[1])
        model.add_accessory_gene(model_genes[2])
        model.add_accessory_gene(model_genes[3])
        model.add_accessory_gene(model_genes[4])  # loner
        model.add_neutral_gene(model_genes[5])

        #     CoreHit(gene, hit_id, hit_seq_length, replicon_name, position, i_eval, score,
        #         profile_coverage, sequence_coverage, begin_match, end_match
        #                                                     pos     score
        h10 = CoreHit(core_genes[0], "h10", 10, "replicon_1", 10, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh10 = ModelHit(h10, gene_ref=model_genes[0], gene_status=GeneStatus.MANDATORY)
        h11 = CoreHit(core_genes[0], "h11", 10, "replicon_1", 10, 1.0, 11.0, 1.0, 1.0, 10, 20)
        mh11 = ModelHit(h11, gene_ref=model_genes[0], gene_status=GeneStatus.MANDATORY)

        h20 = CoreHit(core_genes[1], "h20", 10, "replicon_1", 20, 1.0, 20.0, 1.0, 1.0, 10, 20)
        mh20 = ModelHit(h20, gene_ref=model_genes[1], gene_status=GeneStatus.MANDATORY)
        h21 = CoreHit(core_genes[2], "h21", 10, "replicon_1", 20, 1.0, 21.0, 1.0, 1.0, 10, 20)
        mh21 = ModelHit(h21, gene_ref=model_genes[1], gene_status=GeneStatus.MANDATORY)

        h30 = CoreHit(core_genes[2], "h30", 10, "replicon_1", 30, 1.0, 30.0, 1.0, 1.0, 10, 20)
        mh30 = ModelHit(h30, gene_ref=model_genes[2], gene_status=GeneStatus.ACCESSORY)
        h31 = CoreHit(core_genes[1], "h31", 10, "replicon_1", 30, 1.0, 31.0, 1.0, 1.0, 10, 20)
        mh31 = ModelHit(h31, gene_ref=model_genes[1], gene_status=GeneStatus.MANDATORY)

        h50 = CoreHit(core_genes[2], "h50", 10, "replicon_1", 50, 1.0, 50.0, 1.0, 1.0, 10, 20)
        mh50 = ModelHit(h50, gene_ref=model_genes[2], gene_status=GeneStatus.ACCESSORY)
        h51 = CoreHit(core_genes[2], "h51", 10, "replicon_1", 50, 1.0, 51.0, 1.0, 1.0, 10, 20)
        mh51 = ModelHit(h51, gene_ref=model_genes[2], gene_status=GeneStatus.ACCESSORY)

        h60 = CoreHit(core_genes[3], "h60", 10, "replicon_1", 60, 1.0, 60.0, 1.0, 1.0, 10, 20)
        mh60 = ModelHit(h60, gene_ref=model_genes[3], gene_status=GeneStatus.ACCESSORY)
        h61 = CoreHit(core_genes[3], "h61", 10, "replicon_1", 60, 1.0, 61.0, 1.0, 1.0, 10, 20)
        mh61 = ModelHit(h61, gene_ref=model_genes[3], gene_status=GeneStatus.ACCESSORY)

        # case replicon is linear, 2 clusters
        hits = [mh10, mh11, mh20, mh21, mh30, mh31, mh50, mh51, mh60, mh61]
        random.shuffle(hits)
        got_clusters = clusterize_hits_on_distance_only(hits, model, self.hit_weights, rep_info)
        self.assertEqual(len(got_clusters), 2)
        self.assertListEqual(got_clusters[0].hits, [mh11, mh21, mh31])
        self.assertListEqual(got_clusters[1].hits, [mh51, mh61])

        # case replicon is linear with a single hit (not loner) between 2 clusters
        h70 = CoreHit(core_genes[3], "h70", 10, "replicon_1", 70, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh70 = ModelHit(h70, gene_ref=model_genes[3], gene_status=GeneStatus.ACCESSORY)
        h80 = CoreHit(core_genes[4], "h80", 10, "replicon_1", 80, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh80 = ModelHit(h80, gene_ref=model_genes[4], gene_status=GeneStatus.ACCESSORY)
        hits = [mh10, mh11, mh20, mh21, mh50, mh51, mh70, mh80]
        random.shuffle(hits)
        got_clusters = clusterize_hits_on_distance_only(hits, model, self.hit_weights, rep_info)
        self.assertEqual(len(got_clusters), 2)
        self.assertListEqual(got_clusters[0].hits, [mh11, mh21])
        self.assertListEqual(got_clusters[1].hits, [mh70, mh80])

        # replicon is linear, 3 clusters, the last one contains only one hit (loner h80)
        rep_info = RepliconInfo('linear', 1, 100, [(f"g_{i}", i * 10) for i in range(1, 101)])
        h80 = CoreHit(core_genes[4], "h80", 10, "replicon_1", 80, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh80 = ModelHit(h80, gene_ref=model_genes[4], gene_status=GeneStatus.ACCESSORY)
        hits = [mh10, mh11, mh20, mh21, mh30, mh31, mh50, mh51, mh60, mh61, mh80]
        random.shuffle(hits)
        got_clusters = clusterize_hits_on_distance_only(hits, model, self.hit_weights, rep_info)
        self.assertEqual(len(got_clusters), 3)
        self.assertListEqual(got_clusters[0].hits, [mh11, mh21, mh31])
        self.assertListEqual(got_clusters[1].hits, [mh51, mh61])
        self.assertListEqual(got_clusters[2].hits, [mh80])

        # replicon is circular contains only one cluster
        rep_info = RepliconInfo('circular', 1, 60, [(f"g_{i}", i * 10) for i in range(1, 7)])
        hits = [mh10, mh20, mh30]
        got_clusters = clusterize_hits_on_distance_only(hits, model, self.hit_weights, rep_info)
        self.assertEqual(len(got_clusters), 1)
        self.assertListEqual(got_clusters[0].hits, [mh10, mh20, mh30])

        # replicon is circular the last cluster is merge  with the first So we have only one cluster
        rep_info = RepliconInfo('circular', 1, 60, [(f"g_{i}", i * 10) for i in range(1, 7)])
        hits = [mh10, mh11, mh20, mh21, mh30, mh31, mh50, mh51, mh60, mh61]
        got_clusters = clusterize_hits_on_distance_only(hits, model, self.hit_weights, rep_info)
        self.assertEqual(len(got_clusters), 1)
        self.assertListEqual(got_clusters[0].hits, [mh51, mh61, mh11, mh21, mh31])

        # replicon is linear the last cluster SHOULD NOT be merged with the first So we have 2 clusters
        rep_info = RepliconInfo('linear', 1, 60, [(f"g_{i}", i * 10) for i in range(1, 7)])
        hits = [mh10, mh11, mh20, mh21, mh30, mh31, mh50, mh51, mh60, mh61]
        got_clusters = clusterize_hits_on_distance_only(hits, model, self.hit_weights, rep_info)
        self.assertEqual(len(got_clusters), 2)
        self.assertListEqual(got_clusters[0].hits, [mh11, mh21, mh31])
        self.assertListEqual(got_clusters[1].hits, [mh51, mh61])

        # replicon is circular the last hit is incorporate to the first cluster
        # mh80 is not considered as loner it is included in a cluster
        rep_info = RepliconInfo('circular', 1, 80, [(f"g_{i}", i * 10) for i in range(1, 9)])
        h80 = CoreHit(core_genes[3], "h80", 10, "replicon_1", 80, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh80 = ModelHit(h80, gene_ref=model_genes[3], gene_status=GeneStatus.ACCESSORY)
        hits = [mh10, mh11, mh20, mh21, mh30, mh31, mh50, mh51, mh60, mh61, mh80]
        random.shuffle(hits)
        got_clusters = clusterize_hits_on_distance_only(hits, model, self.hit_weights, rep_info)
        self.assertEqual(len(got_clusters), 2)
        self.assertListEqual(got_clusters[0].hits, [mh80, mh11, mh21, mh31])
        self.assertListEqual(got_clusters[1].hits, [mh51, mh61])

        # replicon is linear the last hit SHOULD NOT be incorporated to the first cluster
        # mh80 is not considered as loner it is included in a cluster
        rep_info = RepliconInfo('linear', 1, 80, [(f"g_{i}", i * 10) for i in range(1, 9)])
        h80 = CoreHit(core_genes[3], "h80", 10, "replicon_1", 80, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh80 = ModelHit(h80, gene_ref=model_genes[3], gene_status=GeneStatus.ACCESSORY)
        hits = [mh10, mh11, mh20, mh21, mh30, mh31, mh50, mh51, mh60, mh61, mh80]
        random.shuffle(hits)
        got_clusters = clusterize_hits_on_distance_only(hits, model, self.hit_weights, rep_info)
        self.assertEqual(len(got_clusters), 2)
        self.assertListEqual(got_clusters[0].hits, [mh11, mh21, mh31])
        self.assertListEqual(got_clusters[1].hits, [mh51, mh61])

        # replicon is circular
        # last hit colocalize with first hit which is not in a cluster
        rep_info = RepliconInfo('circular', 1, 80, [(f"g_{i}", i * 10) for i in range(1, 9)])
        h80 = CoreHit(core_genes[3], "h80", 10, "replicon_1", 80, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh80 = ModelHit(h80, gene_ref=model_genes[3], gene_status=GeneStatus.ACCESSORY)
        hits = [mh10, mh11, mh30, mh31, mh50, mh51, mh60, mh61, mh80]
        random.shuffle(hits)
        got_clusters = clusterize_hits_on_distance_only(hits, model, self.hit_weights, rep_info)
        self.assertEqual(len(got_clusters), 2)
        self.assertListEqual(got_clusters[0].hits, [mh51, mh61])
        self.assertListEqual(got_clusters[1].hits, [mh80, mh11])

        # replicon is circular
        # last hit mh80 colocalize with first hit mh10_alt which is not in a cluster but the 2 hits are neutral: it's not a cluster
        rep_info = RepliconInfo('circular', 1, 80, [(f"g_{i}", i * 10) for i in range(1, 9)])

        h10_alt = CoreHit(core_genes[3], "h10_alt", 10, "replicon_1", 10, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh10_alt = ModelHit(h10_alt, gene_ref=model_genes[5], gene_status=GeneStatus.ACCESSORY)
        h80 = CoreHit(core_genes[3], "h80", 10, "replicon_1", 80, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh80 = ModelHit(h80, gene_ref=model_genes[5], gene_status=GeneStatus.ACCESSORY)
        hits = [mh10_alt, mh30, mh31, mh50, mh51, mh60, mh61, mh80]
        random.shuffle(hits)
        got_clusters = clusterize_hits_on_distance_only(hits, model, self.hit_weights, rep_info)
        self.assertEqual(len(got_clusters), 1)
        self.assertListEqual(got_clusters[0].hits, [mh51, mh61])

        # replicon is circular
        # last hit mh80 does not colocates whit first one mh50
        rep_info = RepliconInfo('circular', 1, 80, [(f"g_{i}", i * 10) for i in range(1, 9)])

        h10_alt = CoreHit(core_genes[3], "h10_alt", 10, "replicon_1", 10, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh10_alt = ModelHit(h10_alt, gene_ref=model_genes[5], gene_status=GeneStatus.ACCESSORY)
        h80 = CoreHit(core_genes[3], "h80", 10, "replicon_1", 80, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh80 = ModelHit(h80, gene_ref=model_genes[5], gene_status=GeneStatus.ACCESSORY)
        hits = [mh10_alt,  mh50]
        random.shuffle(hits)
        got_clusters = clusterize_hits_on_distance_only(hits, model, self.hit_weights, rep_info)
        self.assertEqual(len(got_clusters), 0)

        # # replicon is linear
        # # last hit DO NOT colocalize with first hit which is not in a cluster
        rep_info = RepliconInfo('linear', 1, 80, [(f"g_{i}", i * 10) for i in range(1, 9)])
        h80 = CoreHit(core_genes[3], "h80", 10, "replicon_1", 80, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh80 = ModelHit(h80, gene_ref=model_genes[3], gene_status=GeneStatus.ACCESSORY)
        hits = [mh10, mh11, mh30, mh31, mh50, mh51, mh60, mh61, mh80]
        random.shuffle(hits)
        got_clusters = clusterize_hits_on_distance_only(hits, model, self.hit_weights, rep_info)
        self.assertEqual(len(got_clusters), 1)
        self.assertListEqual(got_clusters[0].hits, [mh51, mh61])


        # replicon is linear the last hit is not merged with the first cluster
        # mh80 is link to gene_4 'abc'. So, in this test, it's not a loner.
        rep_info = RepliconInfo('linear', 1, 62, [(f"g_{i}", i * 10) for i in range(1, 7)])
        hits = [mh10, mh11, mh20, mh21, mh30, mh31, mh50, mh51, mh60, mh61]
        random.shuffle(hits)
        got_clusters = clusterize_hits_on_distance_only(hits, model, self.hit_weights, rep_info)
        self.assertEqual(len(got_clusters), 2)
        self.assertListEqual(got_clusters[0].hits, [mh11, mh21, mh31])
        self.assertListEqual(got_clusters[1].hits, [mh51, mh61])

        # case replicon is linear, 2 clusters, the hits 11,21,31 and 51,61 are contiguous
        #                                                              pos
        h10 = CoreHit(core_genes[0], "h10", 10, "replicon_1", 10, 1.0, 11.0, 1.0, 1.0, 10, 20)
        mh10 = ModelHit(h10, gene_ref=model_genes[0], gene_status=GeneStatus.MANDATORY)
        h11 = CoreHit(core_genes[2], "h11", 10, "replicon_1", 11, 1.0, 21.0, 1.0, 1.0, 10, 20)
        mh11 = ModelHit(h11, gene_ref=model_genes[2], gene_status=GeneStatus.ACCESSORY)
        h12 = CoreHit(core_genes[1], "h12", 10, "replicon_1", 12, 1.0, 31.0, 1.0, 1.0, 10, 20)
        mh12 = ModelHit(h12, gene_ref=model_genes[1], gene_status=GeneStatus.MANDATORY)
        h50 = CoreHit(core_genes[2], "h50", 10, "replicon_1", 50, 1.0, 51.0, 1.0, 1.0, 10, 20)
        mh50 = ModelHit(h50, gene_ref=model_genes[2], gene_status=GeneStatus.ACCESSORY)
        h51 = CoreHit(core_genes[3], "h51", 10, "replicon_1", 51, 1.0, 61.0, 1.0, 1.0, 10, 20)
        mh51 = ModelHit(h51, gene_ref=model_genes[3], gene_status=GeneStatus.ACCESSORY)
        hits = [mh10, mh11, mh12, mh50, mh51]
        random.shuffle(hits)
        got_clusters = clusterize_hits_on_distance_only(hits, model, self.hit_weights, rep_info)
        self.assertEqual(len(got_clusters), 2)
        self.assertListEqual(got_clusters[0].hits, [mh10, mh11, mh12])
        self.assertListEqual(got_clusters[1].hits, [mh50, mh51])

        # case replicon is linear
        # one cluster with one hit loner
        h80 = CoreHit(core_genes[4], "h80", 10, "replicon_1", 80, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh80 = ModelHit(h80, gene_ref=model_genes[4], gene_status=GeneStatus.ACCESSORY)
        hits = [mh80]
        got_clusters = clusterize_hits_on_distance_only(hits, model, self.hit_weights, rep_info)
        self.assertEqual(len(got_clusters), 1)
        self.assertListEqual(got_clusters[0].hits, [mh80])

        # case replicon is linear
        # one cluster with one hit min_gene_required == 1
        # last hit is a cluster
        model = Model("foo/T2SS", 11, min_mandatory_genes_required=1, min_genes_required=1)
        core_genes = []
        model_genes = []
        for g_name in ('gspD', 'sctC'):
            core_gene = CoreGene(self.model_location, g_name, self.profile_factory)
            core_genes.append(core_gene)
            model_genes.append(ModelGene(core_gene, model))
        model.add_mandatory_gene(model_genes[0])
        model.add_accessory_gene(model_genes[1])

        h80 = CoreHit(core_genes[1], "h80", 10, "replicon_1", 80, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh80 = ModelHit(h80, gene_ref=model_genes[1], gene_status=GeneStatus.ACCESSORY)
        hits = [mh80]
        got_clusters = clusterize_hits_on_distance_only(hits, model, self.hit_weights, rep_info)
        self.assertEqual(len(got_clusters), 1)
        self.assertListEqual(got_clusters[0].hits, [mh80])

        # case replicon is linear
        # one cluster with one hit min_gene_required == 1
        # first hit is a cluster
        model = Model("foo/T2SS", 11, min_mandatory_genes_required=1, min_genes_required=1)
        core_genes = []
        model_genes = []
        for g_name in ('gspD', 'sctC'):
            core_gene = CoreGene(self.model_location, g_name, self.profile_factory)
            core_genes.append(core_gene)
            model_genes.append(ModelGene(core_gene, model))
        model.add_mandatory_gene(model_genes[0])
        model.add_accessory_gene(model_genes[1])

        h10 = CoreHit(core_genes[0], "h10", 10, "replicon_1", 10, 1.0, 11.0, 1.0, 1.0, 10, 20)
        mh10 = ModelHit(h10, gene_ref=model_genes[0], gene_status=GeneStatus.MANDATORY)
        h80 = CoreHit(core_genes[1], "h80", 10, "replicon_1", 80, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh80 = ModelHit(h80, gene_ref=model_genes[1], gene_status=GeneStatus.ACCESSORY)
        hits = [mh10, mh80]
        random.shuffle(hits)
        got_clusters = clusterize_hits_on_distance_only(hits, model, self.hit_weights, rep_info)
        self.assertEqual(len(got_clusters), 2)
        self.assertListEqual(got_clusters[0].hits, [mh10])
        self.assertListEqual(got_clusters[1].hits, [mh80])

        # case replicon is linear
        # one cluster with one hit min_gene_required != 1
        model = Model("foo/T2SS", 11, min_mandatory_genes_required=1, min_genes_required=2)
        core_genes = []
        model_genes = []
        for g_name in ('gspD', 'sctC'):
            core_gene = CoreGene(self.model_location, g_name, self.profile_factory)
            core_genes.append(core_gene)
            model_genes.append(ModelGene(core_gene, model))
        model.add_mandatory_gene(model_genes[0])
        model.add_accessory_gene(model_genes[1])
        h80 = CoreHit(core_genes[1], "h80", 10, "replicon_1", 80, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh80 = ModelHit(h80, gene_ref=model_genes[1], gene_status=GeneStatus.ACCESSORY)
        hits = [mh80]
        got_clusters = clusterize_hits_on_distance_only(hits, model, self.hit_weights, rep_info)
        self.assertListEqual(got_clusters, [])

        # case replicon is linear, no hits
        got_clusters = clusterize_hits_on_distance_only([], model, self.hit_weights, rep_info)
        self.assertListEqual(got_clusters, [])

        #############################################
        model = Model("foo/T2SS", 11)
        core_genes = []
        model_genes = []
        for g_name in ('gspD', 'sctC', 'sctJ', 'sctN', 'abc', 'tadZ'):
            core_gene = CoreGene(self.model_location, g_name, self.profile_factory)
            core_genes.append(core_gene)
            model_genes.append(ModelGene(core_gene, model))
        model_genes[4]._loner = True

        model.add_mandatory_gene(model_genes[0])
        model.add_mandatory_gene(model_genes[1])
        model.add_accessory_gene(model_genes[2])
        model.add_accessory_gene(model_genes[3])
        model.add_accessory_gene(model_genes[4])  # loner
        model.add_neutral_gene(model_genes[5])

        # case replicon is linear
        # one cluster composed of only loners
        h80 = CoreHit(core_genes[4], "h80", 10, "replicon_1", 80, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh80 = ModelHit(h80, gene_ref=model_genes[4], gene_status=GeneStatus.ACCESSORY)
        h85 = CoreHit(core_genes[4], "h85", 10, "replicon_1", 85, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh85 = ModelHit(h85, gene_ref=model_genes[4], gene_status=GeneStatus.ACCESSORY)
        h89 = CoreHit(core_genes[4], "h89", 10, "replicon_1", 89, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh89 = ModelHit(h89, gene_ref=model_genes[4], gene_status=GeneStatus.ACCESSORY)

        hits = [mh80, mh85, mh89]
        random.shuffle(hits)
        got_clusters = clusterize_hits_on_distance_only(hits, model, self.hit_weights, rep_info)

        # The squash of cluster of loner is done after clusterize_hits_on_distance_only step
        # in _get_tue_loners
        # I should get one cluster of 3 loners
        self.assertEqual(len(got_clusters), 1)
        self.assertListEqual(got_clusters[0].hits, [mh80, mh85, mh89])

        # case replicon is linear
        # one cluster composed of only one type of gene
        # I should not get cluster
        h10 = CoreHit(core_genes[1], "h10", 10, "replicon_1", 10, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh10 = ModelHit(h10, gene_ref=model_genes[1], gene_status=GeneStatus.MANDATORY)
        h15 = CoreHit(core_genes[1], "h15", 10, "replicon_1", 15, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh15 = ModelHit(h15, gene_ref=model_genes[1], gene_status=GeneStatus.MANDATORY)
        h19 = CoreHit(core_genes[1], "h19", 10, "replicon_1", 19, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh19 = ModelHit(h19, gene_ref=model_genes[1], gene_status=GeneStatus.MANDATORY)

        hits = [mh10, mh15, mh19]
        random.shuffle(hits)
        got_clusters = clusterize_hits_on_distance_only(hits, model, self.hit_weights, rep_info)
        self.assertListEqual(got_clusters, [])

        # case replicon is linear
        # one cluster composed of only one type of gene and it's exhangeable
        core_flgB = CoreGene(self.model_location, 'flgB', self.profile_factory)
        exchangeable = Exchangeable(core_flgB, model_genes[2])
        h20 = CoreHit(core_genes[2], "h20", 10, "replicon_1", 20, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh20 = ModelHit(h20, gene_ref=model_genes[2], gene_status=GeneStatus.ACCESSORY)
        h25 = CoreHit(core_genes[2], "h25", 10, "replicon_1", 25, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh25 = ModelHit(h25, gene_ref=model_genes[2], gene_status=GeneStatus.ACCESSORY)
        h29 = CoreHit(core_flgB, "h29", 10, "replicon_1", 29, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh29 = ModelHit(h29, gene_ref=exchangeable, gene_status=GeneStatus.ACCESSORY)

        hits = [mh20, mh25, mh29]
        random.shuffle(hits)
        got_clusters = clusterize_hits_on_distance_only(hits, model, self.hit_weights, rep_info)
        self.assertEqual(len(got_clusters), 1)
        self.assertListEqual(got_clusters[0].hits, [mh20, mh25, mh29])


    def test_split_cluster_on_key_genes(self):
        model = Model("foo/T2SS", 11)
        core_genes = []
        model_genes = []
        for g_name in ('gspD', 'sctC', 'sctJ', 'sctN', 'abc', 'tadZ', 'flgB'):
            core_gene = CoreGene(self.model_location, g_name, self.profile_factory)
            core_genes.append(core_gene)
            model_genes.append(ModelGene(core_gene, model))

        model.add_mandatory_gene(model_genes[0])
        model.add_mandatory_gene(model_genes[1]) # integrase
        model.add_accessory_gene(model_genes[2])
        model.add_accessory_gene(model_genes[3])
        model.add_accessory_gene(model_genes[4])
        model.add_accessory_gene(model_genes[5]) # integrase
        model.add_accessory_gene(model_genes[6])

        int_20 = CoreHit(core_genes[1], "int_h20", 10, "replicon_1", 20, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh_int_20 = ModelHit(int_20, gene_ref=model_genes[1], gene_status=GeneStatus.MANDATORY)
        int_60 = CoreHit(core_genes[5], "int_h20", 10, "replicon_1", 60, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh_int_60 = ModelHit(int_60, gene_ref=model_genes[5], gene_status=GeneStatus.MANDATORY)
        key_genes = [mh_int_20, mh_int_60]

        h_10 = CoreHit(core_genes[0], "h10", 10, "replicon_1", 10, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh_10 = ModelHit(h_10, gene_ref=model_genes[0], gene_status=GeneStatus.MANDATORY)
        h_30 = CoreHit(core_genes[2], "h30", 10, "replicon_1", 30, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh_30 = ModelHit(h_30, gene_ref=model_genes[2], gene_status=GeneStatus.ACCESSORY)
        h_40 = CoreHit(core_genes[3], "h40", 10, "replicon_1", 40, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh_40 = ModelHit(h_40, gene_ref=model_genes[3], gene_status=GeneStatus.ACCESSORY)
        h_50 = CoreHit(core_genes[4], "h50", 10, "replicon_1", 50, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh_50 = ModelHit(h_50, gene_ref=model_genes[4], gene_status=GeneStatus.ACCESSORY)
        h_70 = CoreHit(core_genes[6], "h70", 10, "replicon_1", 70, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh_70 = ModelHit(h_70, gene_ref=model_genes[6], gene_status=GeneStatus.ACCESSORY)
        c = Cluster([mh_10, mh_int_20, mh_30, mh_40, mh_50, mh_int_60, mh_70], model, self.hit_weights)
        clusters = split_cluster_on_key_genes({h.gene_ref.name for h in key_genes}, c)
        self.assertEqual(len(clusters), 2)
        self.assertEqual(clusters[0].hits, [mh_10, mh_int_20, mh_30, mh_40])
        self.assertEqual(clusters[1].hits, [mh_50, mh_int_60, mh_70])

        c = Cluster([mh_10, mh_30, mh_40, mh_50, mh_70], model, self.hit_weights)
        clusters = split_cluster_on_key_genes({h.gene_ref.name for h in (mh_int_20, mh_int_60)}, c)
        self.assertEqual(clusters, [])


    def test_clusterize_hits_around_key_genes(self):
        rep_info = RepliconInfo('linear', 1, 80, [(f"g_{i}", i * 10) for i in range(1, 9)])
        model = Model("foo/T2SS", 11)
        core_genes = []
        model_genes = []
        for g_name in ('gspD', 'sctC', 'sctJ', 'sctN', 'abc', 'tadZ', 'flgB'):
            core_gene = CoreGene(self.model_location, g_name, self.profile_factory)
            core_genes.append(core_gene)
            model_genes.append(ModelGene(core_gene, model))

        model.add_mandatory_gene(model_genes[0])
        model.add_mandatory_gene(model_genes[1])  # integrase
        model.add_accessory_gene(model_genes[2])
        model.add_accessory_gene(model_genes[3])
        model.add_accessory_gene(model_genes[4])
        model.add_accessory_gene(model_genes[5])  # integrase
        model.add_accessory_gene(model_genes[6])

        int_20 = CoreHit(core_genes[1], "int_h20", 10, "replicon_1", 20, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh_int_20 = ModelHit(int_20, gene_ref=model_genes[1], gene_status=GeneStatus.MANDATORY)
        int_60 = CoreHit(core_genes[5], "int_h20", 10, "replicon_1", 60, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh_int_60 = ModelHit(int_60, gene_ref=model_genes[5], gene_status=GeneStatus.MANDATORY)
        key_genes = [mh.gene_ref.name for mh in (mh_int_20, mh_int_60)]

        # mh_10 -> mh_70 colocalize and contains 2 integrases the cluster must be split in 2
        h_10 = CoreHit(core_genes[0], "h10", 10, "replicon_1", 10, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh_10 = ModelHit(h_10, gene_ref=model_genes[0], gene_status=GeneStatus.MANDATORY)
        h_30 = CoreHit(core_genes[2], "h30", 10, "replicon_1", 30, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh_30 = ModelHit(h_30, gene_ref=model_genes[2], gene_status=GeneStatus.ACCESSORY)
        h_40 = CoreHit(core_genes[3], "h40", 10, "replicon_1", 40, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh_40 = ModelHit(h_40, gene_ref=model_genes[3], gene_status=GeneStatus.ACCESSORY)
        h_50 = CoreHit(core_genes[4], "h50", 10, "replicon_1", 50, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh_50 = ModelHit(h_50, gene_ref=model_genes[4], gene_status=GeneStatus.ACCESSORY)
        h_70 = CoreHit(core_genes[6], "h70", 10, "replicon_1", 70, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh_70 = ModelHit(h_70, gene_ref=model_genes[6], gene_status=GeneStatus.ACCESSORY)

        # mh_100, mh_110, mh_120 colocalize but it does not contains an integrase so it's not a cluster
        h_100 = CoreHit(core_genes[2], "h30", 10, "replicon_1", 100, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh_100 = ModelHit(h_100, gene_ref=model_genes[2], gene_status=GeneStatus.ACCESSORY)
        h_110 = CoreHit(core_genes[3], "h110", 10, "replicon_1", 110, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh_110 = ModelHit(h_110, gene_ref=model_genes[3], gene_status=GeneStatus.ACCESSORY)
        h_120 = CoreHit(core_genes[4], "h120", 10, "replicon_1", 120, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh_120 = ModelHit(h_120, gene_ref=model_genes[4], gene_status=GeneStatus.ACCESSORY)

        # One cluster with 2 integrases which need to be split
        # Plus one set of colocating hits but without integrase
        clusters = clusterize_hits_around_key_genes(key_genes,
                                            [mh_10, mh_int_20, mh_30, mh_40, mh_50, mh_int_60, mh_70, mh_100, mh_110,
                                             mh_120],
                                             model, self.hit_weights, rep_info)

        self.assertEqual(len(clusters), 2)
        self.assertEqual(clusters[0].hits, [mh_10, mh_int_20, mh_30, mh_40])
        self.assertEqual(clusters[1].hits, [mh_50, mh_int_60, mh_70])

        # One cluster with One integrase
        clusters = clusterize_hits_around_key_genes(key_genes,
                                            [mh_10, mh_int_20, mh_30, mh_40],
                                             model, self.hit_weights, rep_info)

        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0].hits, [mh_10, mh_int_20, mh_30, mh_40])


    def test_closest_hit(self):
        #              fqn      , inter_gene_max_sapce
        model = Model("foo/T2SS", 11)
        core_genes = []
        model_genes = []
        for g_name in ('gspD', 'sctC', 'sctJ', 'sctN', 'abc', 'tadZ'):
            core_gene = CoreGene(self.model_location, g_name, self.profile_factory)
            core_genes.append(core_gene)
            model_genes.append(ModelGene(core_gene, model))

        model.add_mandatory_gene(model_genes[0])
        model.add_mandatory_gene(model_genes[1])
        model.add_accessory_gene(model_genes[2])
        model.add_accessory_gene(model_genes[3])
        model.add_accessory_gene(model_genes[4])
        model.add_accessory_gene(model_genes[5])

        int_20 = CoreHit(core_genes[1], "int_h20", 10, "replicon_1", 20, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh_int_20 = ModelHit(int_20, gene_ref=model_genes[1], gene_status=GeneStatus.MANDATORY)
        int_60 = CoreHit(core_genes[5], "int_h20", 10, "replicon_1", 60, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh_int_60 = ModelHit(int_60, gene_ref=model_genes[5], gene_status=GeneStatus.MANDATORY)
        ref_hits = [mh_int_20, mh_int_60]  # 'sctC', 'abc'

        h_10 = CoreHit(core_genes[0], "h10", 10, "replicon_1", 10, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh_10 = ModelHit(h_10, gene_ref=model_genes[0], gene_status=GeneStatus.MANDATORY)
        self.assertEqual(closest_hit(mh_10, ref_hits), mh_int_20)

        h_30 = CoreHit(core_genes[2], "h30", 10, "replicon_1", 30, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh_30 = ModelHit(h_30, gene_ref=model_genes[2], gene_status=GeneStatus.MANDATORY)
        self.assertEqual(closest_hit(mh_30, ref_hits), mh_int_20)

        h_50 = CoreHit(core_genes[4], "h50", 10, "replicon_1", 50, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh_50 = ModelHit(h_50, gene_ref=model_genes[4], gene_status=GeneStatus.MANDATORY)
        self.assertEqual(closest_hit(mh_50, ref_hits), mh_int_60)

        # h40 is at same distance from int_20 and int_60
        # but algorithm favor the first solution
        h_40 = CoreHit(core_genes[3], "h40", 10, "replicon_1", 40, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh_40 = ModelHit(h_40, gene_ref=model_genes[3], gene_status=GeneStatus.MANDATORY)
        self.assertEqual(closest_hit(mh_40, ref_hits), mh_int_20)


    def test_is_a(self):
        #              fqn      , inter_gene_max_sapce
        model = Model("foo/T2SS", 11)
        core_genes = []
        model_genes = []
        for g_name in ('gspD', 'sctC', 'sctJ', 'sctN'):
            core_gene = CoreGene(self.model_location, g_name, self.profile_factory)
            core_genes.append(core_gene)
            model_genes.append(ModelGene(core_gene, model))

        model.add_mandatory_gene(model_genes[0])
        model.add_mandatory_gene(model_genes[1])

        #     CoreHit(gene, hit_id, hit_seq_length, replicon_name, position, i_eval, score,
        #         profile_coverage, sequence_coverage, begin_match, end_match
        #                                                     pos     score
        h10 = CoreHit(core_genes[0], "h10", 10, "replicon_1", 10, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh10 = ModelHit(h10, gene_ref=model_genes[0], gene_status=GeneStatus.MANDATORY)

        h20 = CoreHit(core_genes[1], "h20", 10, "replicon_1", 20, 1.0, 20.0, 1.0, 1.0, 10, 20)
        mh20 = ModelHit(h20, gene_ref=model_genes[1], gene_status=GeneStatus.MANDATORY)

        self.assertFalse(is_a(mh10, {'sctC', 'sctN'}))
        self.assertTrue(is_a(mh20, {'sctC', 'sctN'}))


    def test_scaffold_to_cluster(self):
        #              fqn      , inter_gene_max_sapce
        model = Model("foo/T2SS", inter_gene_max_space=11, min_genes_required=4)

        core_genes = []
        model_genes = []
        for g_name in ('gspD', 'sctC', 'sctJ', 'sctN', 'abc', 'tadZ'):
            core_gene = CoreGene(self.model_location, g_name, self.profile_factory)
            core_genes.append(core_gene)
            model_genes.append(ModelGene(core_gene, model))
        model_genes[3]._loner = True

        model.add_mandatory_gene(model_genes[0])
        model.add_mandatory_gene(model_genes[1])
        model.add_accessory_gene(model_genes[2])
        model.add_accessory_gene(model_genes[3])  # loner
        model.add_neutral_gene(model_genes[4])
        model.add_neutral_gene(model_genes[5])

        #     CoreHit(gene, hit_id, hit_seq_length, replicon_name, position, i_eval, score,
        #         profile_coverage, sequence_coverage, begin_match, end_match
        #                                                     pos     score
        h10 = CoreHit(core_genes[0], "h10", 10, "replicon_1", 10, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh10 = ModelHit(h10, gene_ref=model_genes[0], gene_status=GeneStatus.MANDATORY)

        h20 = CoreHit(core_genes[1], "h20", 10, "replicon_1", 20, 1.0, 20.0, 1.0, 1.0, 10, 20)
        mh20 = ModelHit(h20, gene_ref=model_genes[1], gene_status=GeneStatus.MANDATORY)

        h30 = CoreHit(core_genes[2], "h30", 10, "replicon_1", 30, 1.0, 30.0, 1.0, 1.0, 10, 20)
        mh30 = ModelHit(h30, gene_ref=model_genes[2], gene_status=GeneStatus.ACCESSORY)

        h40 = CoreHit(core_genes[3], "h40", 10, "replicon_1", 40, 1.0, 50.0, 1.0, 1.0, 10, 20)
        mh40 = ModelHit(h40, gene_ref=model_genes[3], gene_status=GeneStatus.ACCESSORY)

        h50 = CoreHit(core_genes[4], "h50", 10, "replicon_1", 50, 1.0, 60.0, 1.0, 1.0, 10, 20)
        mh50 = ModelHit(h50, gene_ref=model_genes[4], gene_status=GeneStatus.NEUTRAL)

        h60 = CoreHit(core_genes[5], "h60", 10, "replicon_1", 60, 1.0, 61.0, 1.0, 1.0, 10, 20)
        mh60 = ModelHit(h60, gene_ref=model_genes[5], gene_status=GeneStatus.NEUTRAL)

        hits = [mh10, mh20, mh30, mh40, mh50, mh60]

        # case several hits mandatory, accessory (with one loner), and neutral
        # should be a cluster
        c = scaffold_to_cluster(hits, model, self.hit_weights)
        self.assertTrue(isinstance(c, Cluster))
        self.assertEqual(len(c), len(hits))
        self.assertEqual(c.hits, hits)

        # 1 hit model min_gene_required > 1
        c = scaffold_to_cluster([mh10], model, self.hit_weights)
        self.assertIsNone(c)

        # 1 hit but a Loner
        # it's a cluster
        c = scaffold_to_cluster([mh40], model, self.hit_weights)
        self.assertEqual(c.hits, [mh40])

        # several hits but all Loner
        # it's a cluster
        h400 = CoreHit(core_genes[3], "h400", 10, "replicon_1", 400, 1.0, 50.0, 1.0, 1.0, 10, 20)
        mh400 = ModelHit(h400, gene_ref=model_genes[3], gene_status=GeneStatus.ACCESSORY)
        hits = [mh40, mh400]
        c = scaffold_to_cluster([mh40, mh400], model, self.hit_weights)
        self.assertEqual(c.hits, [mh40, mh400])


        # several hits but only neutral
        # it's not a cluster
        c = scaffold_to_cluster([mh50, mh60], model, self.hit_weights)
        self.assertIsNone(c)

        # several hits but same type of gene
        # it's not a cluster
        h100 = CoreHit(core_genes[0], "h100", 10, "replicon_1", 100, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh100 = ModelHit(h100, gene_ref=model_genes[0], gene_status=GeneStatus.MANDATORY)
        h200 = CoreHit(core_genes[0], "h200", 10, "replicon_1", 200, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh200 = ModelHit(h200, gene_ref=model_genes[0], gene_status=GeneStatus.MANDATORY)
        h300 = CoreHit(core_genes[0], "h300", 10, "replicon_1", 300, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh300 = ModelHit(h300, gene_ref=model_genes[0], gene_status=GeneStatus.MANDATORY)
        c = scaffold_to_cluster([mh100, mh200, mh300], model, self.hit_weights)
        self.assertIsNone(c)

        # 1 hit model min_gene_required == 1
        # it's a cluster
        model._min_genes_required = 1
        c = scaffold_to_cluster([mh10], model, self.hit_weights)
        self.assertEqual(c.hits, [mh10])

        # 1 hit NEUTRAL model min_gene_required == 1
        # it's NOT a cluster
        c = scaffold_to_cluster([mh50], model, self.hit_weights)
        self.assertIsNone(c)

    def test_get_true_loners(self):
        #              fqn      , inter_gene_max_sapce
        model = Model("foo/T2SS", 11)

        core_genes = []
        model_genes = []
        for g_name in ('gspD', 'sctC', 'sctJ', 'sctN', 'abc',  'flgB'):
            core_gene = CoreGene(self.model_location, g_name, self.profile_factory)
            core_genes.append(core_gene)
            model_genes.append(ModelGene(core_gene, model))
        model_genes[4]._loner = True
        model_genes[5]._loner = True
        model_genes[5]._multi_system = True

        model.add_mandatory_gene(model_genes[0])
        model.add_mandatory_gene(model_genes[1])
        model.add_accessory_gene(model_genes[2])
        model.add_accessory_gene(model_genes[3])
        model.add_neutral_gene(model_genes[4])
        model.add_accessory_gene(model_genes[5])


        #     CoreHit(gene, hit_id, hit_seq_length, replicon_name, position, i_eval, score,
        #         profile_coverage, sequence_coverage, begin_match, end_match
        #                                                     pos     score
        ch_11 = CoreHit(core_genes[0], "h11", 10, "replicon_1", 10, 1.0, 11.0, 1.0, 1.0, 10, 20)
        mh_11 = ModelHit(ch_11, gene_ref=model_genes[0], gene_status=GeneStatus.MANDATORY)

        ch_21 = CoreHit(core_genes[2], "h21", 10, "replicon_1", 20, 1.0, 21.0, 1.0, 1.0, 10, 20)
        mh_21 = ModelHit(ch_21, gene_ref=model_genes[1], gene_status=GeneStatus.MANDATORY)

        h31 = CoreHit(core_genes[1], "h31", 10, "replicon_1", 30, 1.0, 31.0, 1.0, 1.0, 10, 20)
        mh31 = ModelHit(h31, gene_ref=model_genes[1], gene_status=GeneStatus.MANDATORY)

        ch_51 = CoreHit(core_genes[2], "h51", 10, "replicon_1", 50, 1.0, 51.0, 1.0, 1.0, 10, 20)
        mh_51 = ModelHit(ch_51, gene_ref=model_genes[2], gene_status=GeneStatus.ACCESSORY)

        ch_61 = CoreHit(core_genes[3], "h61", 10, "replicon_1", 60, 1.0, 61.0, 1.0, 1.0, 10, 20)
        mh_61 = ModelHit(ch_61, gene_ref=model_genes[3], gene_status=GeneStatus.ACCESSORY)

        # case replicon is linear with a single hit (not loner) between 2 clusters
        ch_70 = CoreHit(core_genes[3], "h70", 10, "replicon_1", 70, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh_70 = ModelHit(ch_70, gene_ref=model_genes[3], gene_status=GeneStatus.ACCESSORY)
        ch_80 = CoreHit(core_genes[4], "h80", 10, "replicon_1", 80, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh_80 = ModelHit(ch_80, gene_ref=model_genes[4], gene_status=GeneStatus.NEUTRAL)
        c0 = Cluster([mh_11, mh_21], model, self.hit_weights)
        c1 = Cluster([mh_70, mh_80], model, self.hit_weights)
        true_loners, true_clusters = _get_true_loners([c0, c1])
        self.assertEqual(len(true_clusters), 2)
        self.assertListEqual(true_clusters[0].hits, [mh_11, mh_21])
        self.assertListEqual(true_clusters[1].hits, [mh_70, mh_80])
        self.assertEqual(true_loners, {})

        # replicon is linear, 3 clusters, the last one contains only one hit (loner h80)
        ch_80 = CoreHit(core_genes[4], "h80", 10, "replicon_1", 80, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh_80 = ModelHit(ch_80, gene_ref=model_genes[4], gene_status=GeneStatus.NEUTRAL)

        c0 = Cluster([mh_11, mh_21, mh31], model, self.hit_weights)
        c1 = Cluster([mh_51, mh_61], model, self.hit_weights)
        c2 = Cluster([mh_80], model, self.hit_weights)
        true_loners, true_clusters = _get_true_loners([c0, c1, c2])
        self.assertEqual(len(true_clusters), 2)
        self.assertListEqual(true_clusters[0].hits, [mh_11, mh_21, mh31])
        self.assertListEqual(true_clusters[1].hits, [mh_51, mh_61])
        self.assertEqual(len(true_loners), 1)
        self.assertListEqual(true_loners['abc'].hits, [mh_80])

        # replicon is linear, 2 clusters, the last one contains 3 hits including one loner
        # although the gene is mark as loner as the hit is in cluster
        # it is not considered as True Loner
        # so it's type should be a ModelHit not Loner
        ch_80 = CoreHit(core_genes[4], "h80", 10, "replicon_1", 80, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh_80 = ModelHit(ch_80, gene_ref=model_genes[4], gene_status=GeneStatus.NEUTRAL)

        c0 = Cluster([mh_11, mh_21, mh31], model, self.hit_weights)
        c1 = Cluster([mh_51, mh_61, mh_80], model, self.hit_weights)
        true_loners, true_clusters = _get_true_loners([c0, c1])
        self.assertEqual(len(true_clusters), 2)
        self.assertListEqual(true_clusters[0].hits, [mh_11, mh_21, mh31])
        self.assertListEqual(true_clusters[1].hits, [mh_51, mh_61, mh_80])
        self.assertEqual(len(true_loners), 0)
        self.assertTrue(isinstance(true_clusters[1].hits[-1], ModelHit))
        self.assertFalse(isinstance(true_clusters[1].hits[-1], Loner))

        # case replicon is linear
        # one cluster with one hit loner
        ch_80 = CoreHit(core_genes[4], "h80", 10, "replicon_1", 80, 1.0, 80.0, 1.0, 1.0, 10, 20)
        mh_80 = ModelHit(ch_80, gene_ref=model_genes[4], gene_status=GeneStatus.NEUTRAL)
        c0 = Cluster([mh_80], model, self.hit_weights)
        true_loners, true_clusters = _get_true_loners([c0])
        self.assertEqual(len(true_clusters), 0)
        self.assertTrue(isinstance(true_loners['abc'], Cluster))
        self.assertTrue(isinstance(true_loners['abc'][0], Loner))
        self.assertListEqual(true_loners['abc'].hits, [mh_80])

        # replicon is linear,
        # 2 clusters,
        #  - one regular cluster
        #  - 3 loner multisystem (same gene)
        ch_90 = CoreHit(core_genes[5], "h90", 10, "replicon_1", 90, 1.0, 90.0, 1.0, 1.0, 10, 20)
        ch_100 = CoreHit(core_genes[5], "h100", 10, "replicon_1", 100, 1.0, 100.0, 1.0, 1.0, 10, 20)
        ch_110 = CoreHit(core_genes[5], "h110", 10, "replicon_1", 110, 1.0, 110.0, 1.0, 1.0, 10, 20)
        mh_90 = MultiSystem(ch_90, gene_ref=model_genes[5], gene_status=GeneStatus.ACCESSORY)
        mh_100 = MultiSystem(ch_100, gene_ref=model_genes[5], gene_status=GeneStatus.ACCESSORY)
        mh_110 = MultiSystem(ch_110, gene_ref=model_genes[5], gene_status=GeneStatus.ACCESSORY)

        ms_90 = MultiSystem(mh_90, counterpart=[mh_100, mh_110])
        ms_100 = MultiSystem(mh_100, counterpart=[mh_90, mh_110])
        ms_110 = MultiSystem(mh_110, counterpart=[mh_90, mh_100])
        c0 = Cluster([mh_11, mh_21, mh31], model, self.hit_weights)
        c1 = Cluster([ms_90], model, self.hit_weights)
        c2 = Cluster([ms_100], model, self.hit_weights)
        c3 = Cluster([ms_110], model, self.hit_weights)

        true_loners, true_clusters = _get_true_loners([c0, c1, c2, c3])
        self.assertEqual(len(true_clusters), 1)
        self.assertEqual(len(true_loners), 1)
        # check that the loner is a LonerMultiSystem
        # that is the hit with best score mh110 110.0
        # and hold the right counterpart
        self.assertTrue(isinstance(true_loners['flgB'], Cluster))
        self.assertTrue(isinstance(true_loners['flgB'][0], LonerMultiSystem))
        self.assertListEqual(true_loners['flgB'].hits, [ms_110])
        self.assertSetEqual(set(true_loners['flgB'][0].counterpart), set([mh_90, mh_100]))


class TestCluster(MacsyTest):

    def setUp(self) -> None:
        self.args = argparse.Namespace()
        self.args.sequence_db = self.find_data("base", "test_1.fasta")
        self.args.db_type = 'gembase'
        self.args.models_dir = self.find_data('models')
        self.args.res_search_dir = "blabla"

        self.cfg = Config(MacsyDefaults(), self.args)
        self.model_name = 'foo'
        self.model_location = ModelLocation(path=os.path.join(self.args.models_dir, self.model_name))
        self.profile_factory = ProfileFactory(self.cfg)
        self.hit_weights = HitWeight(**self.cfg.hit_weights())


    def test_init(self):
        model_1 = Model("foo/T2SS", 11)

        c_gene_1 = CoreGene(self.model_location, "gspD", self.profile_factory)
        c_gene_2 = CoreGene(self.model_location, "sctC", self.profile_factory)
        c_gene_3 = CoreGene(self.model_location, "sctJ", self.profile_factory)

        gene_1 = ModelGene(c_gene_1, model_1)

        h10 = CoreHit(c_gene_1, "h10", 10, "replicon_1", 10, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh10 = ModelHit(h10, gene_1, GeneStatus.MANDATORY)
        h20 = CoreHit(c_gene_2, "h20", 10, "replicon_1", 20, 1.0, 20.0, 1.0, 1.0, 10, 20)
        mh20 = ModelHit(h20, gene_1, GeneStatus.MANDATORY)
        h30 = CoreHit(c_gene_3, "h30", 10, "replicon_2", 30, 1.0, 30.0, 1.0, 1.0, 10, 20)
        mh30 = ModelHit(h30, gene_1, GeneStatus.ACCESSORY)
        h50 = CoreHit(c_gene_3, "h50", 10, "replicon_2", 50, 1.0, 50.0, 1.0, 1.0, 10, 20)
        mh50 = ModelHit(h50, gene_1, GeneStatus.ACCESSORY)

        with self.assertRaises(MacsylibError) as ctx:
            with self.catch_log():
                Cluster([mh10, mh20, mh30, mh50], model_1, self.hit_weights)
        msg = "Cannot build a cluster from hits coming from different replicons"
        self.assertEqual(str(ctx.exception), msg)


    def test_replicon_name(self):
        model = Model("foo/T2SS", 11)

        c_gene_1 = CoreGene(self.model_location, "gspD", self.profile_factory)
        c_gene_2 = CoreGene(self.model_location, "sctC", self.profile_factory)

        gene_1 = ModelGene(c_gene_1, model)
        gene_2 = ModelGene(c_gene_2, model)

        replicon_name = "replicon_1"
        #     CoreHit(gene, model, hit_id, hit_seq_length, replicon_name, position, i_eval, score,
        #         profile_coverage, sequence_coverage, begin_match, end_match
        h10 = CoreHit(c_gene_1, "h10", 10, replicon_name, 10, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh10 = ModelHit(h10, gene_1, GeneStatus.MANDATORY)
        h20 = CoreHit(c_gene_2, "h20", 10, replicon_name, 20, 1.0, 20.0, 1.0, 1.0, 10, 20)
        mh20 = ModelHit(h20, gene_2, GeneStatus.MANDATORY)

        c1 = Cluster([mh10, mh20], model, self.hit_weights)
        self.assertEqual(c1.replicon_name, replicon_name)


    def test_len(self):
        model = Model("foo/T2SS", 11)

        c_gene_1 = CoreGene(self.model_location, "gspD", self.profile_factory)
        c_gene_2 = CoreGene(self.model_location, "sctC", self.profile_factory)

        gene_1 = ModelGene(c_gene_1, model)
        gene_2 = ModelGene(c_gene_2, model)

        #     CoreHit(gene, model, hit_id, hit_seq_length, replicon_name, position, i_eval, score,
        #         profile_coverage, sequence_coverage, begin_match, end_match
        h10 = CoreHit(c_gene_1, "h10", 10, "replicon_1", 10, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh10 = ModelHit(h10, gene_1, GeneStatus.MANDATORY)
        h20 = CoreHit(c_gene_2, "h20", 10, "replicon_1", 20, 1.0, 20.0, 1.0, 1.0, 10, 20)
        mh20 = ModelHit(h20, gene_2, GeneStatus.MANDATORY)

        c1 = Cluster([mh10, mh20], model, self.hit_weights)
        self.assertEqual(len(c1), 2)

    def test_loner(self):
        model = Model("foo/bar", 11)

        c_gene_1 = CoreGene(self.model_location, "gspD", self.profile_factory)
        c_gene_2 = CoreGene(self.model_location, "sctC", self.profile_factory)

        gene_1 = ModelGene(c_gene_1, model, loner=True)
        gene_2 = ModelGene(c_gene_2, model)

        #     CoreHit(gene, model, hit_id, hit_seq_length, replicon_name, position, i_eval, score,
        #         profile_coverage, sequence_coverage, begin_match, end_match
        h10 = CoreHit(c_gene_1, "h10", 10, "replicon_1", 10, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh10 = ModelHit(h10, gene_1, GeneStatus.MANDATORY)
        l_h10 = Loner(h10, gene_1, GeneStatus.MANDATORY)
        h20 = CoreHit(c_gene_2, "h20", 10, "replicon_1", 20, 1.0, 20.0, 1.0, 1.0, 10, 20)
        mh20 = ModelHit(h20, gene_2, GeneStatus.MANDATORY)

        c1 = Cluster([l_h10], model, self.hit_weights)
        c2 = Cluster([mh20], model, self.hit_weights)
        c3 = Cluster([mh10, mh20], model, self.hit_weights)
        self.assertTrue(c1.loner)
        self.assertFalse(c2.loner)
        self.assertFalse(c3.loner)


    def test_multi_system(self):
        model = Model("foo/bar", 11)

        c_gene_1 = CoreGene(self.model_location, "gspD", self.profile_factory)
        c_gene_2 = CoreGene(self.model_location, "sctC", self.profile_factory)

        gene_1 = ModelGene(c_gene_1, model, multi_system=True)
        gene_2 = ModelGene(c_gene_2, model)

        #     CoreHit(gene, model, hit_id, hit_seq_length, replicon_name, position, i_eval, score,
        #         profile_coverage, sequence_coverage, begin_match, end_match
        h10 = CoreHit(c_gene_1, "h10", 10, "replicon_1", 10, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh10 = ModelHit(h10, gene_1, GeneStatus.MANDATORY)
        l_h10 = MultiSystem(h10, gene_1, GeneStatus.MANDATORY)
        h20 = CoreHit(c_gene_2, "h20", 10, "replicon_1", 20, 1.0, 20.0, 1.0, 1.0, 10, 20)
        mh20 = ModelHit(h20, gene_2, GeneStatus.MANDATORY)

        c1 = Cluster([l_h10], model, self.hit_weights)
        c2 = Cluster([mh20], model, self.hit_weights)
        c3 = Cluster([mh10, mh20], model, self.hit_weights)
        self.assertTrue(c1.multi_system)
        self.assertFalse(c2.multi_system)
        self.assertFalse(c3.multi_system)


    def test_contains(self):
        model = Model("foo/T2SS", 11)

        c_gene_1 = CoreGene(self.model_location, "gspD", self.profile_factory)
        c_gene_2 = CoreGene(self.model_location, "sctC", self.profile_factory)
        c_gene_3 = CoreGene(self.model_location, "sctJ", self.profile_factory)

        gene_1 = ModelGene(c_gene_1, model)
        gene_2 = ModelGene(c_gene_2, model)
        gene_3 = ModelGene(c_gene_3, model)

        #     CoreHit(gene, model, hit_id, hit_seq_length, replicon_name, position, i_eval, score,
        #         profile_coverage, sequence_coverage, begin_match, end_match
        h10 = CoreHit(c_gene_1, "h10", 10, "replicon_1", 10, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh10 = ModelHit(h10, gene_1, GeneStatus.MANDATORY)
        h20 = CoreHit(c_gene_2, "h20", 10, "replicon_1", 20, 1.0, 20.0, 1.0, 1.0, 10, 20)
        mh20 = ModelHit(h20, gene_2, GeneStatus.MANDATORY)
        h30 = CoreHit(c_gene_3, "h30", 10, "replicon_1", 30, 1.0, 30.0, 1.0, 1.0, 10, 20)
        mh30 = ModelHit(h30, gene_3, GeneStatus.ACCESSORY)
        h50 = CoreHit(c_gene_3, "h50", 10, "replicon_1", 50, 1.0, 50.0, 1.0, 1.0, 10, 20)
        mh50 = ModelHit(h50, gene_3, GeneStatus.ACCESSORY)
        c1 = Cluster([mh10, mh20, mh50], model, self.hit_weights)

        self.assertTrue(mh10 in c1)
        self.assertFalse(mh30 in c1)


    def test_fulfilled_function(self):
        model = Model("foo/T2SS", 11)

        c_gene_1 = CoreGene(self.model_location, "gspD", self.profile_factory)
        c_gene_2 = CoreGene(self.model_location, "sctC", self.profile_factory)
        c_gene_3 = CoreGene(self.model_location, "sctJ", self.profile_factory)
        c_gene_4 = CoreGene(self.model_location, "sctJ_FLG", self.profile_factory)

        gene_1 = ModelGene(c_gene_1, model)
        gene_2 = ModelGene(c_gene_2, model)
        gene_3 = ModelGene(c_gene_3, model)
        gene_4 = Exchangeable(c_gene_4, gene_3)
        gene_3.add_exchangeable(gene_4)

        #     CoreHit(gene, model, hit_id, hit_seq_length, replicon_name, position, i_eval, score,
        #         profile_coverage, sequence_coverage, begin_match, end_match
        h10 = CoreHit(c_gene_1, "h10", 10, "replicon_1", 10, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh10 = ModelHit(h10, gene_1, GeneStatus.MANDATORY)
        h20 = CoreHit(c_gene_2, "h20", 10, "replicon_1", 20, 1.0, 20.0, 1.0, 1.0, 10, 20)
        mh20 = ModelHit(h20, gene_2, GeneStatus.MANDATORY)

        c = Cluster([mh10, mh20], model, self.hit_weights)

        self.assertSetEqual(c.fulfilled_function(gene_1),
                            {'gspD'})
        self.assertSetEqual(c.fulfilled_function(gene_3),
                            set())

        # test with several genes
        self.assertSetEqual(c.fulfilled_function(gene_3, gene_1),
                            {'gspD'})

        # The cluster contains exchangeable
        h50 = CoreHit(c_gene_4, "h50", 10, "replicon_1", 50, 1.0, 50.0, 1.0, 1.0, 10, 20)
        mh50 = ModelHit(h50, gene_4, GeneStatus.ACCESSORY)
        c = Cluster([mh10, mh50], model, self.hit_weights)
        self.assertSetEqual(c.fulfilled_function(gene_3),
                            {'sctJ'})


    def test_score(self):
        model = Model("foo/T2SS", 10)
        c_gene_gspd = CoreGene(self.model_location, "gspD", self.profile_factory)
        gene_gspd = ModelGene(c_gene_gspd, model)
        model.add_mandatory_gene(gene_gspd)

        c_gene_tadZ = CoreGene(self.model_location, "tadZ", self.profile_factory)
        gene_tadZ = ModelGene(c_gene_tadZ, model)
        model.add_mandatory_gene(gene_tadZ)

        c_gene_sctj = CoreGene(self.model_location, "sctC", self.profile_factory)
        gene_sctj = ModelGene(c_gene_sctj, model)

        c_gene_sctJ_FLG = CoreGene(self.model_location, "sctJ_FLG", self.profile_factory)

        analog_sctJ_FLG = Exchangeable(c_gene_sctJ_FLG, gene_sctj)
        gene_sctj.add_exchangeable(analog_sctJ_FLG)
        model.add_accessory_gene(gene_sctj)

        c_gene_sctn = CoreGene(self.model_location, "sctN", self.profile_factory)
        gene_sctn = ModelGene(c_gene_sctn, model, loner=True)
        c_gene_sctn_FLG = CoreGene(self.model_location, "sctN_FLG", self.profile_factory)
        homolog_sctn_FLG = Exchangeable(c_gene_sctn_FLG, gene_sctn)
        gene_sctn.add_exchangeable(homolog_sctn_FLG)
        model.add_accessory_gene(gene_sctn)

        c_gene_toto = CoreGene(self.model_location, "toto", self.profile_factory)
        gene_toto = ModelGene(c_gene_toto, model)
        model.add_neutral_gene(gene_toto)

        c_gene_flie = CoreGene(self.model_location, "fliE", self.profile_factory)
        gene_flie = ModelGene(c_gene_flie, model, loner=True, multi_system=True)
        model.add_mandatory_gene(gene_flie)

        #     CoreHit(gene, model, hit_id, hit_seq_length, replicon_name, position, i_eval, score,
        #         profile_coverage, sequence_coverage, begin_match, end_match
        h_gspd = CoreHit(c_gene_gspd, "h_gspd", 10, "replicon_id", 1, 1.0, 1.0, 1.0, 1.0, 10, 20)
        mh_gspd = ModelHit(h_gspd, gene_gspd, GeneStatus.MANDATORY)
        h_tadz = CoreHit(c_gene_tadZ, "h_tadz", 20, "replicon_id", 1, 1.0, 1.0, 1.0, 1.0, 10, 20)
        mh_tadz = ModelHit(h_tadz, gene_tadZ, GeneStatus.MANDATORY)

        h_sctj = CoreHit(c_gene_sctj, "h_sctj", 30, "replicon_id", 1, 1.0, 1.0, 1.0, 1.0, 10, 20)
        mh_sctj = ModelHit(h_sctj, gene_sctj, GeneStatus.ACCESSORY)

        h_sctn = CoreHit(c_gene_sctn, "sctn", 40, "replicon_id", 1, 1.0, 1.0, 1.0, 1.0, 10, 20)
        mh_sctn = ModelHit(h_sctn, gene_sctn, GeneStatus.ACCESSORY)
        h_sctn_hom = CoreHit(c_gene_sctn_FLG, "h_scth_hom", 30, "replicon_id", 1, 1.0, 1.0, 1.0, 1.0, 10, 20)
        mh_sctn_hom = ModelHit(h_sctn_hom, homolog_sctn_FLG, GeneStatus.ACCESSORY)

        h_toto = CoreHit(c_gene_sctn, "toto", 50, "replicon_id", 1, 1.0, 1.0, 1.0, 1.0, 10, 20)
        mh_toto = ModelHit(h_toto, gene_toto, GeneStatus.NEUTRAL)

        h_flie = CoreHit(c_gene_flie, "h_flie", 100, "replicon_id", 1, 1.0, 1.0, 1.0, 1.0, 10, 20)

        l_flie = Loner(h_flie, gene_flie, GeneStatus.MANDATORY)
        ms_flie = MultiSystem(h_flie, gene_flie, GeneStatus.MANDATORY)
        lms_flie = LonerMultiSystem(h_flie, gene_flie, GeneStatus.MANDATORY)

        # 2 mandatory, 2 accessory no analog/homolog
        c1 = Cluster([mh_gspd, mh_tadz, mh_sctj, mh_sctn], model, self.hit_weights)
        self.assertEqual(c1.score, 3.0)

        # 2 mandatory, 2 accessory 1 neutral, no analog/homolog
        c1 = Cluster([mh_gspd, mh_tadz, mh_sctj, mh_sctn, mh_toto], model, self.hit_weights)
        self.assertEqual(c1.score, 3.0)

        # 1 mandatory + 1 mandatory duplicated 1 time
        # 1 accessory + 1 accessory duplicated 1 times
        # no analog/homolog
        c1 = Cluster([mh_gspd, mh_tadz, mh_sctj, mh_sctn, mh_gspd, mh_sctn], model, self.hit_weights)
        self.assertEqual(c1.score, 3.0)

        # 2 mandatory
        # 1 accessory + 1 accessory homolog
        c1 = Cluster([mh_gspd, mh_tadz, mh_sctj, mh_sctn_hom], model, self.hit_weights)
        self.assertEqual(c1.score, 2.9)

        # 2 mandatory
        # 1 accessory homolog + 2 accessory (check that the score used is the accessory not homolg)
        c1 = Cluster([mh_sctn_hom, mh_gspd, mh_tadz, mh_sctj, mh_sctn], model, self.hit_weights)
        self.assertEqual(c1.score, 3.0)

        # test true loners
        c1 = Cluster([l_flie], model, self.hit_weights)
        self.assertEqual(c1.score, 0.7)

        # test multi system out of cluster
        c1 = Cluster([ms_flie], model, self.hit_weights)
        self.assertEqual(c1.score, 0.7)

        # test multi system out of cluster
        c1 = Cluster([lms_flie], model, self.hit_weights)
        self.assertEqual(c1.score, 0.7)

        # test the cache score
        c1 = Cluster([ms_flie], model, self.hit_weights)
        self.assertEqual(c1.score, 0.7)

        non_valid_hit = ModelHit(h_sctn, gene_sctn, GeneStatus.FORBIDDEN)
        c1 = Cluster([mh_gspd, non_valid_hit, mh_tadz], model, self.hit_weights)
        with self.assertRaises(MacsylibError) as ctx:
            c1.score
        self.assertEqual(str(ctx.exception),
                         "a Cluster contains hit sctN 1 which is neither mandatory nor accessory: forbidden")


    def test_merge(self):
        model = Model("foo/T2SS", 11)

        c_gene_1 = CoreGene(self.model_location, "gspD", self.profile_factory)
        c_gene_2 = CoreGene(self.model_location, "sctC", self.profile_factory)
        c_gene_3 = CoreGene(self.model_location, "sctJ", self.profile_factory)

        gene_1 = ModelGene(c_gene_1, model)
        gene_2 = ModelGene(c_gene_2, model)
        gene_3 = ModelGene(c_gene_3, model)

        #     CoreHit(gene, model, hit_id, hit_seq_length, replicon_name, position, i_eval, score,
        #         profile_coverage, sequence_coverage, begin_match, end_match
        h10 = CoreHit(c_gene_1, "h10", 10, "replicon_1", 10, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh10 = ModelHit(h10, gene_1, GeneStatus.MANDATORY)
        h20 = CoreHit(c_gene_2, "h20", 10, "replicon_1", 20, 1.0, 20.0, 1.0, 1.0, 10, 20)
        mh20 = ModelHit(h20, gene_2, GeneStatus.MANDATORY)
        h30 = CoreHit(c_gene_3, "h30", 10, "replicon_1", 30, 1.0, 30.0, 1.0, 1.0, 10, 20)
        mh30 = ModelHit(h30, gene_3, GeneStatus.ACCESSORY)
        h50 = CoreHit(c_gene_3, "h50", 10, "replicon_1", 50, 1.0, 50.0, 1.0, 1.0, 10, 20)
        mh50 = ModelHit(h50, gene_3, GeneStatus.ACCESSORY)

        c1 = Cluster([mh10, mh20], model, self.hit_weights)
        c2 = Cluster([mh30, mh50], model, self.hit_weights)
        c1.merge(c2)
        self.assertListEqual(c1.hits, [mh10, mh20, mh30, mh50])

        c1 = Cluster([mh10, mh20], model, self.hit_weights)
        c2 = Cluster([mh30, mh50], model, self.hit_weights)
        c2.merge(c1)
        self.assertListEqual(c2.hits, [mh30, mh50, mh10, mh20])

        c1 = Cluster([mh10, mh20], model, self.hit_weights)
        c2 = Cluster([mh30, mh50], model, self.hit_weights)
        c1.merge(c2, before=True)
        self.assertListEqual(c1.hits, [mh30, mh50, mh10, mh20])

        model_2 = Model("foo/T3SS", 11)
        c_gene_3 = CoreGene(self.model_location, "sctJ", self.profile_factory)
        gene_3 = ModelGene(c_gene_3, model)

        h30 = CoreHit(c_gene_3, "h30", 10, "replicon_2", 30, 1.0, 30.0, 1.0, 1.0, 10, 20)
        mh30 = ModelHit(h30, gene_3, GeneStatus.ACCESSORY)
        h50 = CoreHit(c_gene_3, "h50", 10, "replicon_2", 50, 1.0, 50.0, 1.0, 1.0, 10, 20)
        mh50 = ModelHit(h50, gene_3, GeneStatus.ACCESSORY)
        c3 = Cluster([mh30, mh50], model_2, self.hit_weights)
        with self.assertRaises(MacsylibError) as ctx:
            c1.merge(c3)
        self.assertEqual(str(ctx.exception), "Try to merge Clusters from different model")


    def test_str(self):
        model = Model("foo/T2SS", 11)

        c_gene_1 = CoreGene(self.model_location, "gspD", self.profile_factory)
        c_gene_2 = CoreGene(self.model_location, "sctC", self.profile_factory)

        gene_1 = ModelGene(c_gene_1, model)
        gene_2 = ModelGene(c_gene_2, model)

        #     CoreHit(gene, model, hit_id, hit_seq_length, replicon_name, position, i_eval, score,
        #         profile_coverage, sequence_coverage, begin_match, end_match
        h10 = CoreHit(c_gene_1, "h10", 10, "replicon_1", 10, 1.0, 10.0, 1.0, 1.0, 10, 20)
        mh10 = ModelHit(h10, gene_1, GeneStatus.MANDATORY)
        h20 = CoreHit(c_gene_2, "h20", 10, "replicon_1", 20, 1.0, 20.0, 1.0, 1.0, 10, 20)
        mh20 = ModelHit(h20, gene_2, GeneStatus.MANDATORY)
        c1 = Cluster([mh10, mh20], model, self.hit_weights)
        s ="""Cluster:
- model = T2SS
- replicon = replicon_1
- hits = (h10, gspD, 10), (h20, sctC, 20)"""
        self.assertEqual(str(c1), s)


    def test_replace(self):
        model = Model("foo/T2SS", 11)

        c_gene_1 = CoreGene(self.model_location, "gspD", self.profile_factory)
        c_gene_2 = CoreGene(self.model_location, "sctC", self.profile_factory)
        c_gene_3 = CoreGene(self.model_location, "sctJ", self.profile_factory)

        gene_1 = ModelGene(c_gene_1, model)
        gene_2 = ModelGene(c_gene_2, model)
        gene_3 = ModelGene(c_gene_3, model)

        #     CoreHit(gene, model, hit_id, hit_seq_length, replicon_name, position, i_eval, score,
        #         profile_coverage, sequence_coverage, begin_match, end_match
        h10 = CoreHit(c_gene_1, "h10", 10, "replicon_1", 10, 1.0, 10.0, 1.0, 1.0, 10, 20)
        h20 = CoreHit(c_gene_2, "h20", 10, "replicon_1", 20, 1.0, 20.0, 1.0, 1.0, 10, 20)
        h30 = CoreHit(c_gene_3, "h30", 10, "replicon_1", 30, 1.0, 30.0, 1.0, 1.0, 10, 20)
        h50 = CoreHit(c_gene_3, "h50", 10, "replicon_1", 50, 1.0, 50.0, 1.0, 1.0, 10, 20)
        mh10 = ModelHit(h10, gene_1, GeneStatus.MANDATORY)
        mh20 = ModelHit(h20, gene_2, GeneStatus.MANDATORY)
        mh30 = ModelHit(h30, gene_3, GeneStatus.ACCESSORY)
        mh50 = ModelHit(h50, gene_3, GeneStatus.ACCESSORY)

        c1 = Cluster([mh10, mh20, mh30], model, self.hit_weights)
        c1.replace(mh20, mh50)
        self.assertEqual(c1.hits,
                         [mh10, mh50, mh30])
