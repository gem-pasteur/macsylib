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
import tempfile
import argparse

from macsylib.profile import ProfileFactory, Profile
from macsylib.gene import CoreGene
from macsylib.config import Config, MacsyDefaults
from macsylib.registries import ModelLocation
from macsylib.error import MacsylibError
from tests import MacsyTest


class TestProfileFactory(MacsyTest):

    def setUp(self):
        self._tmp_dir = tempfile.TemporaryDirectory(prefix='test_msf_ProfileFactory_')
        args = argparse.Namespace()
        args.sequence_db = self.find_data("base", "test_1.fasta")
        args.db_type = 'gembase'
        args.models_dir = self.find_data('models')
        args.res_search_dir = self._tmp_dir.name
        args.log_level = 30
        self.cfg = Config(MacsyDefaults(), args)

        self.model_name = 'foo'
        self.models_location = ModelLocation(path=os.path.join(args.models_dir, self.model_name))
        self.profile_factory = ProfileFactory(self.cfg)

    def tearDown(self):
        self._tmp_dir.cleanup()


    def test_get_profile(self):
        gene_name = 'sctJ_FLG'
        gene = CoreGene(self.models_location, gene_name, self.profile_factory)
        profile = self.profile_factory.get_profile(gene, self.models_location)
        self.assertTrue(isinstance(profile, Profile))
        self.assertEqual(profile.gene.name, gene_name)


    def test_get_uniq_object(self):
        gene_name = 'sctJ_FLG'
        gene = CoreGene(self.models_location, gene_name, self.profile_factory)
        profile1 = self.profile_factory.get_profile(gene, self.models_location)
        profile2 = self.profile_factory.get_profile(gene, self.models_location)
        self.assertEqual(profile1, profile2)


    def test_unknow_profile(self):
        gene_name = 'sctJ_FLG'
        gene = CoreGene(self.models_location, gene_name, self.profile_factory)
        gene._name = "bar"
        with self.assertRaises(MacsylibError) as ctx:
            self.profile_factory.get_profile(gene, self.models_location)
        self.assertEqual(str(ctx.exception),
                         f"'{self.model_name}/{gene.name}': No such profile")
