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
import sysconfig
import argparse

from macsylib.profile import Profile
from macsylib.gene import CoreGene, ModelGene
from macsylib.model import Model
from macsylib.profile import ProfileFactory
from macsylib.config import Config, MacsyDefaults
from macsylib.registries import ModelLocation
from macsylib.error import MacsylibError

from tests import MacsyTest


class TestProfile(MacsyTest):

    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory(prefix='test_macsy_Profile_')
        args = argparse.Namespace()
        args.sequence_db = self.find_data("base", "test_1.fasta")
        args.db_type = 'gembase'
        args.models_dir = self.find_data('models')
        args.res_search_dir = self._tmp_dir.name
        args.log_level = 50
        self.cfg = Config(MacsyDefaults(), args)

        if os.path.exists(self.cfg.working_dir()):
            shutil.rmtree(self.cfg.working_dir())
        os.makedirs(self.cfg.working_dir())

        self.model_name = 'foo'
        self.model_location = ModelLocation(path=os.path.join(args.models_dir, self.model_name))
        self.profile_factory = ProfileFactory(self.cfg)


    def tearDown(self):
        self._tmp_dir.cleanup()


    def test_len(self):
        model = Model("functional/T12SS-simple-exch", 10)

        gene_name = 'abc'
        c_gene = CoreGene(self.model_location, gene_name, self.profile_factory)
        gene = ModelGene(c_gene, model)

        path = self.model_location.get_profile("abc")
        profile = Profile(gene, self.cfg, path)
        self.assertEqual(len(profile), 501)

        ###########################
        # test compressed profile #
        ###########################
        model = Model("functional_gzip/T12SS-simple-exch", 10)

        gene_name = 'abc'
        c_gene = CoreGene(self.model_location, gene_name, self.profile_factory)
        gene = ModelGene(c_gene, model)

        path = self.model_location.get_profile(gene_name)
        profile = Profile(gene, self.cfg, path)
        self.assertEqual(len(profile), 501)

        model = Model("foo/compressed_profile", 10)
        gene_name = 'abc'
        c_gene = CoreGene(self.model_location, gene_name, self.profile_factory)
        gene = ModelGene(c_gene, model)
        for ext in 'bz2', 'zip':
            with self.subTest(ext=ext):
                path = self.find_data('models', 'foo', 'profiles', f'{ext}.hmm.{ext}')
                with self.catch_log(log_name='macsylib'):
                    with self.assertRaises(MacsylibError) as ctx:
                        Profile(gene, self.cfg, path)
                    self.assertEqual(str(ctx.exception),
                                     f"Cannot read profile {path}: MacSyLib does not support '{ext}' compression "
                                     f"(only gzip).")

        ###################
        # unreadable gzip #
        ###################
        path = self.find_data('models', 'foo', 'profiles', 'bad_ext.hmm.gz')
        with self.catch_log(log_name='macsylib'):
            with self.assertRaises(MacsylibError) as ctx:
                Profile(gene, self.cfg, path)
            self.assertEqual(str(ctx.exception),
                            f"Cannot read profile {path}: Not a gzipped file (b'BZ')"
                             )

    def test_ga_threshold(self):
        # No GA threshold
        model = Model("foo/T2SS", 10)

        gene_name = 'abc'
        c_gene = CoreGene(self.model_location, gene_name, self.profile_factory)
        gene = ModelGene(c_gene, model)
        path = self.model_location.get_profile(gene_name)
        profile = Profile(gene, self.cfg, path)
        self.assertFalse(profile.ga_threshold)

        model = Model("foo/T2SS", 10)
        # GA threshold line ends with ;
        gene_name = 'T5aSS_PF03797'
        c_gene = CoreGene(self.model_location, gene_name, self.profile_factory)
        gene = ModelGene(c_gene, model)
        path = self.model_location.get_profile(gene_name)
        profile = Profile(gene, self.cfg, path)
        self.assertTrue(profile.ga_threshold)

        # GA threshold line do NOT ends with ;
        gene_name = 'PF05930.13'
        c_gene = CoreGene(self.model_location, gene_name, self.profile_factory)
        gene = ModelGene(c_gene, model)
        path = self.model_location.get_profile(gene_name)
        profile = Profile(gene, self.cfg, path)
        self.assertTrue(profile.ga_threshold)

        # GA threshold invalid format string instead float
        gene_name = 'bad_GA'
        with self.catch_log(log_name='macsylib'):
            # When a CoreGene is created a Profile is automatically instanciated
            # So I mute the log to do not polute output
            c_gene = CoreGene(self.model_location, gene_name, self.profile_factory)
        gene = ModelGene(c_gene, model)
        path = self.model_location.get_profile(gene_name)

        with self.catch_log(log_name='macsylib') as log:
            profile = Profile(gene, self.cfg, path)
            catch_msg = log.get_value().strip()
        self.assertFalse(profile.ga_threshold)
        self.assertEqual(catch_msg,
                         "bad_GA GA score is not well formatted expected 2 floats got ''22.00'' ''23.00''.\n"
                         "GA score will not used for gene 'bad_GA'.")

        # GA threshold invalid format only one score
        gene_name = 'bad_GA_2'
        with self.catch_log(log_name='macsylib'):
            # When a CoreGene is created a Profile is automatically instanciated
            # So I mute the log to do not polute output
            c_gene = CoreGene(self.model_location, gene_name, self.profile_factory)
        gene = ModelGene(c_gene, model)
        path = self.model_location.get_profile(gene_name)

        with self.catch_log(log_name='macsylib') as log:
            profile = Profile(gene, self.cfg, path)
            catch_msg = log.get_value().strip()
        self.assertFalse(profile.ga_threshold)
        self.assertEqual(catch_msg,
                         "bad_GA_2 GA score is not well formatted. expected: 'GA float float' got 'GA    22.00'.\n"
                         "GA score will not used for gene 'bad_GA_2'.")

    def test_str(self):
        model = Model("foo/T2SS", 10)

        gene_name = 'abc'
        c_gene = CoreGene(self.model_location, gene_name, self.profile_factory)
        gene = ModelGene(c_gene, model)

        path = self.model_location.get_profile("abc")
        profile = Profile(gene, self.cfg, path)
        s = "{0} : {1}".format(gene.name, path)
        self.assertEqual(str(profile), s)


    @unittest.skipIf(not shutil.which('hmmsearch'), 'hmmsearch not found in PATH')
    def test_execute_hmm_with_GA(self):
        for db_type in ("gembase", "ordered_replicon", "unordered"):
            self.cfg._set_db_type(db_type)
            model = Model("foo/T2SS", 10)

            gene_name = 'T5aSS_PF03797'
            c_gene = CoreGene(self.model_location, gene_name, self.profile_factory)
            gene = ModelGene(c_gene, model)

            # case GA threshold in profile
            profile_path = self.model_location.get_profile("T5aSS_PF03797")
            profile = Profile(gene, self.cfg, profile_path)
            report = profile.execute()
            hmmer_raw_out = profile.hmm_raw_output
            with open(hmmer_raw_out, 'r') as hmmer_raw_out_file:
                first_l = hmmer_raw_out_file.readline()
                # a hmmsearch output file has been produced
                self.assertTrue(first_l.startswith("# hmmsearch :: search profile(s) against a sequence database"))
                for _ in range(5):
                    # skip 4 lines
                    line = hmmer_raw_out_file.readline()
                # a hmmsearch used the abc profile line should become with: "# query HMM file: {the path tp hmm profile used}"
                self.assertTrue(line.find(profile_path) != -1)
                for _ in range(3):
                    # skip 2 lines
                    line = hmmer_raw_out_file.readline()
                self.assertEqual("# model-specific thresholding:     GA cutoffs", line.strip())
            # test if profile is executed only once per run
            report_bis = profile.execute()
            self.assertIs(report, report_bis)


    @unittest.skipIf(not shutil.which('hmmsearch'), 'hmmsearch not found in PATH')
    def test_execute_hmm_protected_path(self):
        # create a hmmdir with space in name
        self.cfg.hmmer_dir = lambda: 'hmmer results'
        # create sequence_db path with space in path
        seq_path = os.path.join(self.cfg.working_dir(), "test_1.fasta")
        shutil.copyfile(self.find_data("base", "test_1.fasta"),
                        seq_path)
        self.cfg._set_sequence_db(seq_path)

        model = Model("foo/T2SS", 10)
        gene_name = 'T5aSS_PF03797'
        c_gene = CoreGene(self.model_location, gene_name, self.profile_factory)
        gene = ModelGene(c_gene, model)

        # case GA threshold in profile
        profile_path = self.model_location.get_profile("T5aSS_PF03797")
        profile = Profile(gene, self.cfg, profile_path)
        profile.execute()
        hmmer_raw_out = profile.hmm_raw_output
        with open(hmmer_raw_out, 'r') as hmmer_raw_out_file:
            first_l = hmmer_raw_out_file.readline()
            # a hmmsearch output file has been produced
            self.assertTrue(first_l.startswith("# hmmsearch :: search profile(s) against a sequence database"))
            for _ in range(5):
                # skip 4 lines
                line = hmmer_raw_out_file.readline()
            # a hmmsearch used the abc profile line should become with: "# query HMM file: {the path tp hmm profile used}"
            self.assertTrue(line.find(profile_path) != -1)
            for _ in range(3):
                # skip 2 lines
                line = hmmer_raw_out_file.readline()
            self.assertEqual("# model-specific thresholding:     GA cutoffs", line.strip())


    @unittest.skipIf(not shutil.which('hmmsearch'), 'hmmsearch not found in PATH')
    def test_execute_hmm_w_GA_n_nocutga(self):
            # case GA threshold in profile but --no-cut-ga is set
            args = argparse.Namespace()
            args.sequence_db = self.find_data("base", "test_1.fasta")
            args.db_type = 'gembase'
            args.models_dir = self.find_data('models')
            args.res_search_dir = self._tmp_dir.name
            args.log_level = 0
            args.e_value_search = 0.5
            args.no_cut_ga = True
            cfg = Config(MacsyDefaults(), args)

            model = Model("foo/T2SS", 10)
            gene_name = 'T5aSS_PF03797'
            c_gene = CoreGene(self.model_location, gene_name, self.profile_factory)
            gene = ModelGene(c_gene, model)
            profile_path = self.model_location.get_profile("T5aSS_PF03797")
            profile = Profile(gene, cfg, profile_path)
            profile.execute()
            hmmer_raw_out = profile.hmm_raw_output
            with open(hmmer_raw_out, 'r') as hmmer_raw_out_file:
                for i in range(9):
                    line = hmmer_raw_out_file.readline()
                self.assertEqual("# sequence reporting threshold:    E-value <= 0.5", line.strip())


    @unittest.skipIf(not shutil.which('hmmsearch'), 'hmmsearch not found in PATH')
    def test_execute_hmm_wo_GA(self):
            # case cut-ga but no GA threshold in hmmprofile
            model = Model("foo/T2SS", 10)
            gene_name = 'abc'
            c_gene = CoreGene(self.model_location, gene_name, self.profile_factory)
            gene = ModelGene(c_gene, model)

            # case -cut-ga and GA threshold in profile
            profile_path = self.model_location.get_profile("abc")
            profile = Profile(gene, self.cfg, profile_path)

            with self.catch_log():
                profile.execute()

            hmmer_raw_out = profile.hmm_raw_output
            with open(hmmer_raw_out, 'r') as hmmer_raw_out_file:
                first_l = hmmer_raw_out_file.readline()
                # a hmmsearch output file has been produced
                self.assertTrue(first_l.startswith("# hmmsearch :: search profile(s) against a sequence database"))
                for _ in range(5):
                    # skip 4 lines
                    line = hmmer_raw_out_file.readline()
                # a hmmsearch used the abc profile line should become with: "# query HMM file: {the path tp hmm profile used}"
                self.assertTrue(line.find(profile_path) != -1)
                for _ in range(3):
                    # skip 2 lines
                    line = hmmer_raw_out_file.readline()
                self.assertEqual('# sequence reporting threshold:    E-value <= 0.1', line.strip())


    def test_execute_unknown_binary(self):
        self.cfg._options['hmmer'] = "Nimportnaoik"
        model = Model("foo/T2SS", 10)

        gene_name = 'abc'
        c_gene = CoreGene(self.model_location, gene_name, self.profile_factory)
        gene = ModelGene(c_gene, model)

        path = self.model_location.get_profile("abc", )
        profile = Profile(gene, self.cfg, path)
        with self.catch_log():
            with self.assertRaises(RuntimeError):
                profile.execute()


    def test_execute_hmmer_failed(self):
        fake_hmmer = os.path.join(self._tmp_dir.name, 'hmmer_failed')
        with open(fake_hmmer, 'w') as hmmer:
            hmmer.write("""#! {}
import sys
sys.exit(127)
""".format(sysconfig.sys.executable))
        try:
            os.chmod(hmmer.name, 0o755)
            self.cfg._options['hmmer'] = hmmer.name
            model = Model("foo/T2SS", 10)

            gene_name = 'abc'
            c_gene = CoreGene(self.model_location, gene_name, self.profile_factory)
            gene = ModelGene(c_gene, model)

            path = self.model_location.get_profile("abc", )
            profile = Profile(gene, self.cfg, path)
            with self.catch_log():
                with self.assertRaisesRegex(RuntimeError,
                                            "an error occurred during Hmmer "
                                            "execution: command = .* : return code = 127 .*"):
                    profile.execute()

        finally:
            try:
                os.unlink(fake_hmmer)
            except Exception:
                pass
