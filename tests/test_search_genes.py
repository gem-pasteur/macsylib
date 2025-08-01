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
import unittest
import shutil
import tempfile
import argparse

import macsylib
from macsylib.config import Config, MacsyDefaults
from macsylib.model import Model
from macsylib.gene import CoreGene, ModelGene
from macsylib.hit import CoreHit
from macsylib.registries import ModelLocation
from macsylib.profile import ProfileFactory
from macsylib.database import Indexes
from macsylib.search_genes import search_genes, worker_cpu
from tests import MacsyTest


class TestSearchGenes(MacsyTest):

    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory(prefix='test_msf_search_genes_')
        self.tmp_dir = self._tmp_dir.name
        macsylib.init_logger(name='macsylib')
        macsylib.logger_set_level(level=30)

        args = argparse.Namespace()
        args.sequence_db = self.find_data("base", "test_base.fa")
        args.db_type = 'gembase'
        args.models_dir = self.find_data('models')
        args.log_level = 30
        args.out_dir = os.path.join(self.tmp_dir, 'job_1')
        args.res_search_dir = args.out_dir
        args.no_cut_ga = True
        args.index_dir = os.path.join(self.tmp_dir)
        os.mkdir(args.out_dir)

        self.cfg = Config(MacsyDefaults(), args)

        self.model_name = 'foo'
        self.model_location = ModelLocation(path=os.path.join(args.models_dir, self.model_name))

        idx = Indexes(self.cfg)
        idx.build()
        self.profile_factory = ProfileFactory(self.cfg)

    def tearDown(self):
        self._tmp_dir.cleanup()

    def test_worker_cpu(self):
        worker_meth = self.cfg.worker
        from macsylib import search_genes
        threads_available_ori = search_genes.threads_available
        try:
            self.cfg.worker = lambda: 5
            worker, cpu = worker_cpu(10, self.cfg)
            self.assertEqual(worker, 5)
            self.assertEqual(cpu, 1)

            self.cfg.worker = lambda: 11
            worker, cpu = worker_cpu(5, self.cfg)
            self.assertEqual(worker, 11)
            self.assertEqual(cpu, 2)

            self.cfg.worker = lambda: 0
            search_genes.threads_available = lambda: 12
            worker, cpu = worker_cpu(5, self.cfg)
            self.assertEqual(worker, 12)
            self.assertEqual(cpu, 2)

        finally:
            self.cfg.worker = worker_meth
            search_genes.threads_available = threads_available_ori

    def test_search_fail(self):
        gene_name = "abc"
        c_gene_abc = CoreGene(self.model_location, gene_name, self.profile_factory)
        with self.assertRaises(AttributeError) as ctx:
            search_genes([c_gene_abc], self.cfg)
        self.assertEqual(str(ctx.exception),
                         "'CoreGene' object has no attribute 'core_gene'")


    @unittest.skipIf(not shutil.which('hmmsearch'), 'hmmsearch not found in PATH')
    def test_search(self):
        gene_name = "abc"
        model_foo = Model("foo", 10)
        model_bar = Model("bar", 10)
        c_gene_abc = CoreGene(self.model_location, gene_name, self.profile_factory)
        mg_abc_1 = ModelGene(c_gene_abc, model_foo)
        mg_abc_2 = ModelGene(c_gene_abc, model_bar)
        report = search_genes([mg_abc_1, mg_abc_2], self.cfg)
        expected_hit = [CoreHit(c_gene_abc, "ESCO030p01_000260", 706, "ESCO030p01",
                                26, float(1.000e-200), float(660.800), float(1.000), float(0.714), 160, 663
                                )]
        self.assertEqual(len(report), 1)
        self.assertEqual(expected_hit[0], report[0].hits[0])


    @unittest.skipIf(not shutil.which('hmmsearch'), 'hmmsearch not found in PATH')
    def test_search_recover(self):
        # first job searching using hmmsearch
        gene_name = "abc"
        model_foo = Model("foo", 10)
        c_gene_abc = CoreGene(self.model_location, gene_name, self.profile_factory)
        mg_abc_1 = ModelGene(c_gene_abc, model_foo)
        report = search_genes([mg_abc_1], self.cfg)
        expected_hit = [CoreHit(c_gene_abc, "ESCO030p01_000260", 706, "ESCO030p01",
                                26, float(1.000e-200), float(660.800), float(1.000), float(0.714), 160, 663
                                )]

        # second job using recover
        # disable hmmer to be sure that test use the recover inner function
        self.cfg.hmmer = lambda: "hmmer_disable"
        # and create a new dir for the second job
        previous_job_path = self.cfg.working_dir()
        self.cfg.previous_run = lambda: previous_job_path
        self.cfg.out_dir = lambda: os.path.join(self.tmp_dir, 'job_2')
        os.mkdir(self.cfg.out_dir())

        # rerun with previous run
        # but we have to reset the profile attached to the gene gene._profile._report
        self.profile_factory = ProfileFactory(self.cfg)
        report = search_genes([mg_abc_1], self.cfg)
        self.assertEqual(len(report), 1)
        self.assertEqual(expected_hit[0], report[0].hits[0])


        # test ordered replicon
        # the only thing that change is the name of the replicon
        self.cfg._set_db_type('ordered_replicon')
        self.profile_factory = ProfileFactory(self.cfg)
        seq_name = os.path.basename(os.path.splitext(self.cfg.sequence_db())[0])
        expected_hit[0].replicon_name = seq_name
        report = search_genes([mg_abc_1], self.cfg)
        self.assertEqual(len(report), 1)
        self.assertEqual(expected_hit[0], report[0].hits[0])

        # test ordered replicon
        # there is no diff with ordered_replicon
        self.cfg._set_db_type('unordered')
        self.profile_factory = ProfileFactory(self.cfg)
        seq_name = os.path.basename(os.path.splitext(self.cfg.sequence_db())[0])
        expected_hit[0].replicon_name = seq_name
        report = search_genes([mg_abc_1], self.cfg)
        self.assertEqual(len(report), 1)
        self.assertEqual(expected_hit[0], report[0].hits[0])
