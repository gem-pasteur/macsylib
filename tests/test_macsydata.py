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

import tempfile
import shutil
import os
import argparse
import sys
import tarfile
import unittest
import io
import shlex
from collections import namedtuple

import yaml
import macsylib.registries
from macsylib.registries import scan_models_dir, ModelRegistry
from macsylib import model_package

from tests import MacsyTest
from macsylib.scripts import macsydata
from macsylib.error import MacsydataError, MacsyDataLimitError
import warnings
warnings.simplefilter('ignore', UserWarning,)
try:
    import git
except ModuleNotFoundError:
    git = None


class TestMacsydata(MacsyTest):

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory(prefix='test_msf_macsydata_')
        self.tmpdir = self._tmpdir.name
        self.models_dir = [os.path.join(self.tmpdir, 'models')]
        os.mkdir(self.models_dir[0])

        self.args = argparse.Namespace()
        self.args.org = 'foo'
        self.args.package_name = 'macsylib'
        self._remote_exists = macsydata.RemoteModelIndex.remote_exists
        macsydata.RemoteModelIndex.remote_exists = lambda x: True
        macsydata._log = macsydata.init_logger(20)  # 20 logging.INFO
        self.definition_1 = """<model inter_gene_max_space="20" min_mandatory_genes_required="1" min_genes_required="2" vers="2.0">
    <gene name="flgB" presence="mandatory"/>
    <gene name="flgC" presence="mandatory" inter_gene_max_space="2">
        <exchangeables>
            <gene name="abc" />
        </exchangeables>
    </gene>
</model>"""
        self.definition_2 = """<model inter_gene_max_space="20" min_mandatory_genes_required="1" min_genes_required="2" vers="2.0">
    <gene name="fliE" presence="mandatory" multi_system="True"/>
    <gene name="tadZ" presence="accessory" loner="True"/>
    <gene name="sctC" presence="forbidden"/>
</model>"""


    def tearDown(self):
        macsydata.RemoteModelIndex.remote_exists = self._remote_exists
        self._tmpdir.cleanup()
        # some function in macsydata script suppress the traceback
        # but without traceback it's hard to debug test :-(
        sys.tracebacklimit = 1000  # the default value

        # at each call of macsydata.main
        # init_logger is called and new handler is add
        # remove them
        logger = macsydata._log
        if logger:
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)


    def create_fake_package(self, model,
                            definitions=True,
                            profiles=True,
                            metadata=True,
                            vers=True,
                            readme=True,
                            license=True,
                            dest=''):
        pack_path = os.path.join(self.tmpdir, dest, model)
        os.makedirs(pack_path)
        if definitions:
            def_dir = os.path.join(pack_path, 'definitions')
            os.mkdir(def_dir)
            sub_fam_1 = os.path.join(def_dir, 'sub_fam_1')
            os.mkdir(sub_fam_1)
            sub_fam_2 = os.path.join(def_dir, 'sub_fam_2')
            os.mkdir(sub_fam_2)
            with open(os.path.join(sub_fam_1, "model_1.xml"), 'w') as f:
                f.write(self.definition_1)
            with open(os.path.join(sub_fam_2, "model_2.xml"), 'w') as f:
                f.write(self.definition_2)

        if profiles:
            profile_dir = os.path.join(pack_path, 'profiles')
            os.mkdir(profile_dir)
            for name in ('flgB', 'flgC', 'fliE', 'tadZ', 'sctC', 'abc'):
                shutil.copyfile(self.find_data('models', 'foo', 'profiles', f'{name}.hmm'),
                                os.path.join(profile_dir, f"{name}.hmm")
                                )
        if metadata:
            meta_path = self.find_data('pack_metadata', 'good_metadata.yml')
            meta_dest = os.path.join(pack_path, model_package.Metadata.name)
            with open(meta_path) as meta_file:
                meta = yaml.safe_load(meta_file)
            if not vers:
                meta['vers'] = None
            with open(meta_dest, 'w') as meta_file:
                yaml.dump(meta, meta_file, allow_unicode=True, indent=2)
        if readme:
            with open(os.path.join(pack_path, "README"), 'w') as f:
                f.write("# This a README\n")
        if license:
            with open(os.path.join(pack_path, "LICENSE"), 'w') as f:
                f.write("# This the License\n")
        return pack_path

    def _fake_download(self, pack_name, vers, dest=None):
        unarch_pack_path = self.create_fake_package(pack_name, dest='tmp')
        arch_path = f"{os.path.join(self.tmpdir, 'tmp', pack_name)}-{vers}.tar.gz"
        with tarfile.open(arch_path, "w:gz") as arch:
            arch.add(unarch_pack_path, arcname=pack_name)
        shutil.rmtree(unarch_pack_path)
        return arch_path


    def test_available(self):
        list_pack = macsydata.RemoteModelIndex.list_packages
        list_pack_vers = macsydata.RemoteModelIndex.list_package_vers
        meta = macsydata.RemoteModelIndex.get_metadata
        pack_name = 'fake_model'
        pack_vers = '1.0'
        pack_meta = {'short_desc': 'desc about fake_model'}
        macsydata.RemoteModelIndex.list_packages = lambda x: [pack_name]
        macsydata.RemoteModelIndex.list_package_vers = lambda x, pack: [pack_vers]
        macsydata.RemoteModelIndex.get_metadata = lambda x, pack, vers: pack_meta
        self.create_fake_package('fake_model')
        try:
            with self.catch_io(out=True):
                macsydata.do_available(self.args)
                get_pack = sys.stdout.getvalue().strip()
            pack_name_vers = f"{pack_name} ({pack_vers})"
            # use same formatting as in do_available
            expected_pack = f"{pack_name_vers:26.25} - {pack_meta['short_desc']}"
            self.assertEqual(get_pack, expected_pack)
        finally:
            macsydata.RemoteModelIndex.list_packages = list_pack
            macsydata.RemoteModelIndex.list_package_vers = list_pack_vers
            macsydata.RemoteModelIndex.get_metadata = meta

        # test package with no version available
        # no version = no tags
        list_pack = macsydata.RemoteModelIndex.list_packages
        list_pack_vers = macsydata.RemoteModelIndex.list_package_vers
        meta = macsydata.RemoteModelIndex.get_metadata
        pack_name = 'fake_model_no_vers'
        pack_meta = {'short_desc': 'desc about fake_model'}
        macsydata.RemoteModelIndex.list_packages = lambda x: [pack_name]
        macsydata.RemoteModelIndex.list_package_vers = lambda x, pack: []
        macsydata.RemoteModelIndex.get_metadata = lambda x, pack, vers: pack_meta
        self.create_fake_package('fake_model_no_vers')
        try:
            with self.catch_io(out=True):
                macsydata.do_available(self.args)
                get_pack = sys.stdout.getvalue().strip()
            self.assertEqual(get_pack, '')
        finally:
            macsydata.RemoteModelIndex.list_packages = list_pack
            macsydata.RemoteModelIndex.list_package_vers = list_pack_vers
            macsydata.RemoteModelIndex.get_metadata = meta


    def test_info(self):
        pack_name = "nimportnaoik"
        self.args.model_package = pack_name
        self.args.models_dir = None
        with self.catch_log(log_name='macsylib'):
            # macsylib.registry throw a warning if metadata is not found
            # silenced it
            with self.catch_log(log_name='macsydata') as log:
                with self.assertRaises(ValueError):
                    macsydata.do_info(self.args)
                log_msg = log.get_value()
        self.assertEqual(log_msg.strip(), f"Models '{pack_name}' not found locally.")

        pack_name = "fake_pack"
        self.args.package = pack_name
        fake_pack_path = self.create_fake_package(pack_name)

        def fake_find_installed_package(model_pack_name, models_dir=None, package_name='macsylib'):
            return macsydata.ModelPackage(fake_pack_path)

        find_local_package = macsydata._find_installed_package
        macsydata._find_installed_package = fake_find_installed_package
        try:
            with self.catch_io(out=True):
                macsydata.do_info(self.args)
                msg = sys.stdout.getvalue().strip()
        finally:
            macsydata._find_installed_package = find_local_package

        expected_info = """fake_pack (0.0b2)

maintainer: auth_name <auth_name@mondomain.fr>

this is a short description of the repos

how to cite:
\t- bla bla
\t- link to publication
\t- ligne 1
\t  ligne 2
\t  ligne 3 et bbbbb

documentation
\thttp://link/to/the/documentation

This data are released under CC BY-NC-SA 4.0 (https://creativecommons.org/licenses/by-nc-sa/4.0/)
copyright: 2019, Institut Pasteur, CNRS"""
        self.assertEqual(expected_info, msg)


    def test_list(self):
        fake_packs = ('fake_1', 'fake_2')
        for name in fake_packs:
            self.create_fake_package(name, dest=self.models_dir[0])
        registry = ModelRegistry()
        for model_loc in scan_models_dir(self.models_dir[0]):
            registry.add(model_loc)

        def fake_find_all_installed_package(models_dir=None, package_name='macsylib'):
            return registry

        find_all_packages = macsydata._find_all_installed_packages
        macsydata._find_all_installed_packages = fake_find_all_installed_package

        self.args.verbose = 1
        self.args.outdated = False
        self.args.uptodate = False
        self.args.models_dir = None
        self.args.long = False
        try:
            with self.catch_io(out=True):
                macsydata.do_list(self.args)
                packs = sys.stdout.getvalue().strip()
        finally:
            macsydata._find_all_installed_packages = find_all_packages
        expected_output = "fake_1-0.0b2\nfake_2-0.0b2"
        self.assertEqual(packs,
                         expected_output)


    def test_list_long(self):
        fake_packs = ('fake_1', 'fake_2')
        for name in fake_packs:
            self.create_fake_package(name, dest=self.models_dir[0])
        model_dir = self.tmpdir
        registry = ModelRegistry()
        for model_loc in scan_models_dir(self.models_dir[0]):
            registry.add(model_loc)

        def fake_find_all_installed_package(models_dir=None, package_name='macsylib'):
            return registry

        find_all_packages = macsydata._find_all_installed_packages
        macsydata._find_all_installed_packages = fake_find_all_installed_package

        self.args.verbose = 1
        self.args.outdated = False
        self.args.uptodate = False
        self.args.models_dir = None
        self.args.long = True

        try:
            with self.catch_io(out=True):
                macsydata.do_list(self.args)
                packs = sys.stdout.getvalue().strip()
        finally:
            macsydata._find_all_installed_packages = find_all_packages
        expected_output  = f"""fake_1-0.0b2   ({os.path.join(model_dir, 'models', fake_packs[0])})
fake_2-0.0b2   ({os.path.join(model_dir, 'models', fake_packs[1])})"""

        self.assertEqual(packs,
                         expected_output)


    def test_list_outdated(self):
        fake_packs = ('fake_1', 'fake_2')
        for name in fake_packs:
            self.create_fake_package(name, dest=self.models_dir[0], metadata=True)
        registry = ModelRegistry()
        for model_loc in scan_models_dir(self.models_dir[0]):
            registry.add(model_loc)

        def fake_find_all_installed_package(models_dir=None, package_name='macsylib'):
            return registry

        find_all_packages = macsydata._find_all_installed_packages
        macsydata._find_all_installed_packages = fake_find_all_installed_package

        remote_list_packages_vers = macsydata.RemoteModelIndex.list_package_vers
        macsydata.RemoteModelIndex.list_package_vers = lambda x, name: {'fake_1': ['1.0'],
                                                                        'fake_2': ['0.0b2']}[name]
        self.args.verbose = 1
        self.args.outdated = True
        self.args.uptodate = False
        self.args.models_dir = None
        self.args.long = False
        try:
            with self.catch_io(out=True):
                macsydata.do_list(self.args)
                packs = sys.stdout.getvalue().strip()
        finally:
            macsydata._find_all_installed_packages = find_all_packages
            macsydata.RemoteModelIndex.list_package_vers = remote_list_packages_vers

        expected_output = 'fake_1-1.0 [0.0b2]'
        self.assertEqual(packs,
                         expected_output)


    def test_list_uptodate(self):
        fake_packs = ('fake_1', 'fake_2')
        for name in fake_packs:
            self.create_fake_package(name, dest=self.models_dir[0])
        registry = ModelRegistry()
        for model_loc in scan_models_dir(self.models_dir[0]):
            registry.add(model_loc)

        def fake_find_all_installed_package(models_dir=None, package_name='macsylib'):
            return registry

        find_all_packages = macsydata._find_all_installed_packages
        macsydata._find_all_installed_packages = fake_find_all_installed_package
        remote_list_packages_vers = macsydata.RemoteModelIndex.list_package_vers
        macsydata.RemoteModelIndex.list_package_vers = lambda x, name: {'fake_1': ['1.0'],
                                                                        'fake_2': ['0.0b2']}[name]
        self.args.verbose = 1
        self.args.outdated = False
        self.args.uptodate = True
        self.args.models_dir = None
        self.args.long = False

        try:
            with self.catch_io(out=True):
                macsydata.do_list(self.args)
                packs = sys.stdout.getvalue().strip()
        finally:
            macsydata._find_all_installed_packages = find_all_packages
            macsydata.RemoteModelIndex.list_package_vers = remote_list_packages_vers
        expected_output = 'fake_2-0.0b2'
        self.assertEqual(packs, expected_output)


    def test_list_verbose(self):
        fake_packs = ('fake_1', 'fake_2')
        for name in fake_packs:
            self.create_fake_package(name, dest=self.models_dir[0])
        registry = ModelRegistry()
        for model_loc in scan_models_dir(self.models_dir[0]):
            registry.add(model_loc)

        def fake_find_all_installed_package(models_dir=None, package_name='macsylib'):
            return registry
        find_all_packages = macsydata._find_all_installed_packages
        macsydata._find_all_installed_packages = fake_find_all_installed_package
        remote_list_packages_vers = macsydata.RemoteModelIndex.list_package_vers
        macsydata.RemoteModelIndex.list_package_vers = lambda x, name: {'fake_1': ['1.0'],
                                                                        'fake_2': ['0.0b2']}[name]
        os.unlink(os.path.join(self.models_dir[0], 'fake_1', 'metadata.yml'))
        self.args.verbose = 2
        self.args.outdated = False
        self.args.uptodate = False
        self.args.models_dir = None
        self.args.long = False

        try:
            with self.catch_io(out=True):
                with self.catch_log(log_name='macsydata') as log:
                    macsydata.do_list(self.args)
                    log_msg = log.get_value().strip()
                packs = sys.stdout.getvalue().strip()
        finally:
            macsydata._find_all_installed_packages = find_all_packages
            macsydata.RemoteModelIndex.list_package_vers = remote_list_packages_vers
        self.assertEqual(packs, 'fake_2-0.0b2')
        self.assertEqual(log_msg, f"[Errno 2] No such file or directory: '{self.models_dir[0]}/fake_1/metadata.yml'")


    def test_freeze(self):
        fake_packs = ('fake_1', 'fake_2')
        for name in fake_packs:
            self.create_fake_package(name, dest=self.models_dir[0])
        registry = ModelRegistry()
        for model_loc in scan_models_dir(self.models_dir[0]):
            registry.add(model_loc)
        find_all_packages = macsydata._find_all_installed_packages
        macsydata._find_all_installed_packages = lambda package_name: registry
        try:
            with self.catch_io(out=True):
                macsydata.do_freeze(self.args)
                packs = sys.stdout.getvalue().strip()
        finally:
            macsydata._find_all_installed_packages = find_all_packages
        self.assertEqual(packs,
                         "fake_1==0.0b2\nfake_2==0.0b2")


    def test_cite(self):
        model_pack_name = "nimportnaoik"
        self.args.model_package = model_pack_name
        self.args.models_dir = None
        with self.catch_log(log_name='macsylib'):
            with self.catch_log(log_name='macsydata') as log:
                with self.assertRaises(ValueError):
                    macsydata.do_cite(self.args)
                log_msg = log.get_value()
            self.assertEqual(log_msg.strip(), f"Models '{model_pack_name}' not found locally.")

        pack_name = "fake_pack"
        self.args.model_package = pack_name
        fake_pack_path = self.create_fake_package(pack_name)

        find_local_package = macsydata._find_installed_package
        macsydata._find_installed_package = lambda model_pack_name, models_dir, package_name: macsydata.ModelPackage(fake_pack_path)
        try:
            with self.catch_io(out=True):
                macsydata.do_cite(self.args)
                citation = sys.stdout.getvalue().strip()
        finally:
            macsydata._find_installed_package = find_local_package
        expected_citation = """To cite fake_pack:

_ bla bla
- link to publication
- ligne 1
  ligne 2
  ligne 3 et bbbbb

To cite MacSyLib:

- Néron, Bertrand; Denise, Rémi; Coluzzi, Charles; Touchon, Marie; Rocha, Eduardo P.C.; Abby, Sophie S.
  MacSyFinder v2: Improved modelling and search engine to identify molecular systems in genomes.
  Peer Community Journal, Volume 3 (2023), article no. e28. doi : 10.24072/pcjournal.250.
  https://peercommunityjournal.org/articles/10.24072/pcjournal.250/"""
        self.assertEqual(expected_citation, citation)


    def test_help(self):
        pack_name = "nimportnaoik"
        self.args.model_package = pack_name
        self.args.models_dir = None
        with self.catch_log(log_name='macsylib'):
            # macsylib.registry throw a warning if metadata is not found
            # silenced it
            with self.catch_log(log_name='macsydata') as log:
                with self.assertRaises(ValueError):
                    macsydata.do_help(self.args)
                log_msg = log.get_value()
        self.assertEqual(log_msg.strip(), f"Models '{pack_name}' not found locally.")

        model_pack_name = "fake_pack"
        self.args.model_package = model_pack_name
        fake_pack_path = self.create_fake_package(model_pack_name)

        def fake_find_installed_package(model_pack_name, models_dir=None, package_name='macsylib'):
            return macsydata.ModelPackage(fake_pack_path)

        find_local_package = macsydata._find_installed_package
        macsydata._find_installed_package = fake_find_installed_package
        try:
            with self.catch_io(out=True):
                macsydata.do_help(self.args)
                citation = sys.stdout.getvalue().strip()
        finally:
            macsydata._find_installed_package = find_local_package
        expected_citation = '# This a README'

        self.assertEqual(expected_citation, citation)


    def test_definition_all_def(self):
        model_pack_name = 'fake_1'
        self.args.model = [model_pack_name]
        self.args.models_dir = None
        fake_pack_path = self.create_fake_package(model_pack_name)

        find_local_package = macsydata._find_installed_package
        macsydata._find_installed_package = lambda model_pack_name, models_dir, package_name: macsylib.registries.ModelLocation(path=fake_pack_path)
        try:
            with self.catch_io(out=True):
                macsydata.do_show_definition(self.args)
                stdout = sys.stdout.getvalue().strip()
        finally:
            macsydata._find_installed_package = find_local_package

        expected_output = f"""<!-- fake_1/sub_fam_1/model_1 {fake_pack_path}/definitions/sub_fam_1/model_1.xml -->
{self.definition_1}

<!-- fake_1/sub_fam_2/model_2 {fake_pack_path}/definitions/sub_fam_2/model_2.xml -->
{self.definition_2}"""
        self.assertEqual(expected_output,
                         stdout)


    def test_definition_one_def(self):
        pack_name = 'fake_1'
        self.args.model = [pack_name, 'sub_fam_1/model_1', 'sub_fam_2/model_2']
        self.args.models_dir = None
        fake_pack_path = self.create_fake_package(pack_name)

        find_local_package = macsydata._find_installed_package
        macsydata._find_installed_package = lambda model_pack_name, models_dir, package_name: macsylib.registries.ModelLocation(path=fake_pack_path)
        try:
            with self.catch_io(out=True):
                macsydata.do_show_definition(self.args)
                stdout = sys.stdout.getvalue().strip()
        finally:
            macsydata._find_installed_package = find_local_package

        expected_output = f"""<!-- fake_1/sub_fam_1/model_1 {fake_pack_path}/definitions/sub_fam_1/model_1.xml -->
{self.definition_1}

<!-- fake_1/sub_fam_2/model_2 {fake_pack_path}/definitions/sub_fam_2/model_2.xml -->
{self.definition_2}"""

        self.assertEqual(expected_output,
                         stdout)


    def test_definition_models_dir(self):
        pack_name = 'fake_1'
        fake_pack_path = self.create_fake_package(pack_name, dest='model_dir')
        self.args.model = [pack_name, 'sub_fam_1/model_1', 'sub_fam_2/model_2']
        self.args.models_dir = os.path.dirname(fake_pack_path)

        with self.catch_io(out=True):
            macsydata.do_show_definition(self.args)
            stdout = sys.stdout.getvalue().strip()

        expected_output = f"""<!-- fake_1/sub_fam_1/model_1 {fake_pack_path}/definitions/sub_fam_1/model_1.xml -->
{self.definition_1}

<!-- fake_1/sub_fam_2/model_2 {fake_pack_path}/definitions/sub_fam_2/model_2.xml -->
{self.definition_2}"""
        self.maxDiff = None
        self.assertEqual(expected_output,
                         stdout)


    def test_definition_bad_def(self):
        pack_name = 'fake_1'
        self.args.model = [pack_name, 'niportnaoik']
        self.args.models_dir = None
        fake_pack_path = self.create_fake_package(pack_name)
        find_local_package = macsydata._find_installed_package
        macsydata._find_installed_package = lambda model_package_name, models_dir, package_name: macsylib.registries.ModelLocation(path=fake_pack_path)
        try:
            with self.catch_log(log_name='macsydata') as log:
                macsydata.do_show_definition(self.args)
                log_msg = log.get_value().strip()
        finally:
            macsydata._find_installed_package = find_local_package

        self.assertEqual(log_msg, "Model 'fake_1/niportnaoik' not found.")


    def test_definition_bad_pack(self):
        pack_name = 'nimportnaoik'
        self.args.model = [pack_name]
        self.args.models_dir = None
        with self.catch_log(log_name='macsylib'):
            # macsylib.registry throw a warning if metadata is not found
            # silenced it
            with self.catch_log(log_name='macsydata') as log:
                with self.assertRaises(ValueError):
                    macsydata.do_show_definition(self.args)
                log_msg = log.get_value().strip()

        self.assertEqual(log_msg, f"Model Package '{pack_name}' not found.")

    def test_definition_bad_subfamily(self):
        pack_name = 'fake_1'
        self.args.model = ['/'.join([pack_name, 'niportnaoik'])]
        self.args.models_dir = None
        fake_pack_path = self.create_fake_package(pack_name)
        find_local_package = macsydata._find_installed_package
        macsydata._find_installed_package = lambda model_package_name, models_dir, package_name: macsylib.registries.ModelLocation(path=fake_pack_path)
        try:
            with self.catch_log(log_name='macsydata') as log:
                with self.assertRaises(ValueError):
                    macsydata.do_show_definition(self.args)
                log_msg = log.get_value().strip()
        finally:
            macsydata._find_installed_package = find_local_package

        self.assertEqual(log_msg,
                         f"'niportnaoik' not found in package '{pack_name}'.")


    def test_check(self):
        pack_name = 'fake_1'
        path = self.create_fake_package(pack_name, vers=False)
        self.args.path = path
        with self.catch_log(log_name='macsydata') as log:
            macsydata.do_check(self.args)
            log_msg = log.get_value().strip()
        expected_msg = f"""If everyone were like you, I'd be out of business
To push the models in organization:
\tcd {os.path.join(self.tmpdir, pack_name)}
Transform the models into a git repository
\tgit init .
\tgit add .
\tgit commit -m 'initial commit'
add a remote repository to host the models
for instance if you want to add the models to 'macsy-models'
\tgit remote add origin https://github.com/macsy-models/
\tgit tag -a <tag vers>  # check https://macsylib.readthedocs.io/en/latest/modeler_guide/publish_package.html#sharing-your-models
\tgit push origin <tag vers>"""
        self.maxDiff = None
        self.assertEqual(expected_msg, log_msg)


    def test_check_with_warnings(self):
        pack_name = 'fake_1'
        path = self.create_fake_package(pack_name, readme=False, license=False)
        self.args.path = path
        self.args.tool_name = 'msl_data'

        with self.catch_log(log_name='macsydata') as log:
            macsydata.do_check(self.args)
            log_msg = log.get_value().strip()
        expected_msg = """The model package 'fake_1' have not any LICENSE file. May be you have not right to use it.
The model package 'fake_1' have not any README file.
The field 'vers' is not required anymore.
  It will be ignored and set by macsydata during installation phase according to the git tag.

msl_data says: You're only giving me a partial QA payment?
I'll take it this time, but I'm not happy.
I'll be really happy, if you fix warnings above, before to publish these models."""

        self.assertEqual(expected_msg, log_msg)


    def test_check_with_errors(self):
        pack_name = 'fake_1'
        path = self.create_fake_package(pack_name, profiles=False, definitions=False)
        self.args.path = path

        with self.catch_log(log_name='macsydata') as log:
            with self.assertRaises(ValueError):
                macsydata.do_check(self.args)
            log_msg = log.get_value().strip()
        expected_msg = """The model package 'fake_1' have no 'definitions' directory.
The model package 'fake_1' have no 'profiles' directory.
Please fix issues above, before publishing these models."""
        self.assertEqual(expected_msg, log_msg)


    def test_download(self):
        def fake_download(_, pack_name, vers, dest=None):
            path = os.path.join(self.tmpdir, f"{pack_name}-{vers}.tar.gz")
            os.mkdir(path)
            return path

        # The package requested exists download it
        remote_list_packages_vers = macsydata.RemoteModelIndex.list_package_vers
        macsydata.RemoteModelIndex.list_package_vers = lambda x, name: {'fake_1': ['1.0'],
                                                                        'fake_2': ['0.0b2']}[name]
        remote_download = macsydata.RemoteModelIndex.download
        macsydata.RemoteModelIndex.download = fake_download
        self.args.package = 'fake_1'
        self.args.dest = None
        try:
            with self.catch_log(log_name='macsydata') as log:
                macsydata.do_download(self.args)
                log_msg = log.get_value().strip()
        finally:
            macsydata.RemoteModelIndex.list_package_vers = remote_list_packages_vers
            macsydata.RemoteModelIndex.download = remote_download
        expected_msg = f"""Downloading {self.args.package} 1.0
Successfully downloaded models fake_1 in {os.path.join(self.tmpdir, 'fake_1-1.0.tar.gz')}"""
        self.assertEqual(log_msg, expected_msg)

        # The package requested does NOT exists
        remote_list_packages_vers = macsydata.RemoteModelIndex.list_package_vers
        macsydata.RemoteModelIndex.list_package_vers = lambda x, name: {'fake_1': ['1.0'],
                                                                        'fake_2': ['0.0b2']}[name]
        remote_download = macsydata.RemoteModelIndex.download
        macsydata.RemoteModelIndex.download = fake_download
        self.args.package = 'fake_1>2.0'
        self.args.dest = None
        try:
            with self.catch_log(log_name='macsydata') as log:
                macsydata.do_download(self.args)
                log_msg = log.get_value().strip()
        finally:
            macsydata.RemoteModelIndex.list_package_vers = remote_list_packages_vers
            macsydata.RemoteModelIndex.download = remote_download

        expected_msg = """No version that satisfy requirements '>2.0' for 'fake_1'.
Available versions: 1.0"""
        self.assertEqual(log_msg, expected_msg)

        # The package requested is NOT versioned
        remote_list_packages_vers = macsydata.RemoteModelIndex.list_package_vers
        macsydata.RemoteModelIndex.list_package_vers = lambda x, name: {'fake_1': [],
                                                                        'fake_2': ['0.0b2']}[name]
        remote_download = macsydata.RemoteModelIndex.download
        macsydata.RemoteModelIndex.download = fake_download
        self.args.package = 'fake_1>2.0'
        self.args.dest = None
        try:
            with self.catch_log(log_name='macsydata') as log:
                macsydata.do_download(self.args)
                log_msg = log.get_value().strip()
        finally:
            macsydata.RemoteModelIndex.list_package_vers = remote_list_packages_vers
            macsydata.RemoteModelIndex.download = remote_download

        self.assertEqual(log_msg, '')

        # Github has been requested over the limit
        def fake_download_limit(_, pack_name, vers, dest=None):
            raise MacsyDataLimitError('github limit error')

        remote_download = macsydata.RemoteModelIndex.download
        macsydata.RemoteModelIndex.download = fake_download_limit
        remote_list_packages_vers = macsydata.RemoteModelIndex.list_package_vers
        macsydata.RemoteModelIndex.list_package_vers = lambda x, name: {'fake_1': ['1.0'],
                                                                        'fake_2': ['0.0b2']}[name]
        self.args.package = 'fake_1'
        self.args.dest = None
        try:
            with self.catch_log(log_name='macsydata') as log:
                macsydata.do_download(self.args)
                log_msg = log.get_value().strip()
        finally:
            macsydata.RemoteModelIndex.list_package_vers = remote_list_packages_vers
            macsydata.RemoteModelIndex.download = remote_download
        expected_msg = "Downloading fake_1 1.0\ngithub limit error"
        self.assertEqual(log_msg, expected_msg)


    def test_install_local(self):
        model_pack_name = 'fake_pack'
        model_pack_vers = '3.0'
        macsydata_cache = os.path.join(self.tmpdir, 'cache')
        os.mkdir(macsydata_cache)
        macsydata_tmp = os.path.join(self.tmpdir, 'tmp')
        os.mkdir(macsydata_tmp)
        macsydata_dest = os.path.join(self.tmpdir, 'models')

        unarch_pack_path = self.create_fake_package(model_pack_name, dest='tmp')
        arch_path = f"{os.path.join(macsydata_tmp, model_pack_name)}-{model_pack_vers}.tar.gz"

        with tarfile.open(arch_path, "w:gz") as arch:
            arch.add(unarch_pack_path, arcname=model_pack_name)
        shutil.rmtree(unarch_pack_path)

        self.args.model_package = arch_path
        self.args.cache = macsydata_cache
        self.args.user = False
        self.args.upgrade = False
        self.args.force = False
        self.args.target = macsydata_dest
        self.args.no_clean = False

        macsydata.Config.models_dir = lambda x: self.models_dir
        try:
            with self.catch_log(log_name='macsydata'):
                macsydata.do_install(self.args)
            expected_pack_path = os.path.join(self.models_dir[0], model_pack_name)
            self.assertTrue(os.path.exists(expected_pack_path))
            self.assertTrue(os.path.isdir(expected_pack_path))
            self.assertTrue(os.path.exists(os.path.join(expected_pack_path, 'metadata.yml')))
            self.assertTrue(os.path.exists(os.path.join(expected_pack_path, 'README')))
            self.assertTrue(os.path.exists(os.path.join(expected_pack_path, 'definitions')))
            self.assertTrue(os.path.exists(os.path.join(expected_pack_path, 'profiles')))
        finally:
            del macsydata.Config.models_dir


    def test_install_target(self):
        model_pack_name = 'fake_pack'
        model_pack_vers = '3.0'
        macsydata_cache = os.path.join(self.tmpdir, 'cache')
        os.mkdir(macsydata_cache)
        macsydata_tmp = os.path.join(self.tmpdir, 'tmp')
        os.mkdir(macsydata_tmp)
        macsydata_target = os.path.join(self.tmpdir, 'target')

        unarch_pack_path = self.create_fake_package(model_pack_name, dest='tmp')
        arch_path = f"{os.path.join(macsydata_tmp, model_pack_name)}-{model_pack_vers}.tar.gz"

        with tarfile.open(arch_path, "w:gz") as arch:
            arch.add(unarch_pack_path, arcname=model_pack_name)
        shutil.rmtree(unarch_pack_path)

        self.args.model_package = arch_path
        self.args.cache = macsydata_cache
        self.args.user = False
        self.args.upgrade = False
        self.args.force = False
        self.args.target = macsydata_target
        self.args.no_clean = False

        with self.catch_log(log_name='macsydata'):
            macsydata.do_install(self.args)
        expected_pack_path = os.path.join(macsydata_target, model_pack_name)
        self.assertTrue(os.path.exists(expected_pack_path))
        self.assertTrue(os.path.isdir(expected_pack_path))
        self.assertTrue(os.path.exists(os.path.join(expected_pack_path, 'metadata.yml')))
        self.assertTrue(os.path.exists(os.path.join(expected_pack_path, 'README')))
        self.assertTrue(os.path.exists(os.path.join(expected_pack_path, 'definitions')))
        self.assertTrue(os.path.exists(os.path.join(expected_pack_path, 'profiles')))


    def test_install_bad_target(self):
        model_pack_name = 'fake_pack'
        model_pack_vers = '3.0'
        macsydata_cache = os.path.join(self.tmpdir, 'cache')
        os.mkdir(macsydata_cache)
        macsydata_tmp = os.path.join(self.tmpdir, 'tmp')
        os.mkdir(macsydata_tmp)
        macsydata_target = os.path.join(self.tmpdir, 'target')
        open(macsydata_target, 'w').close()

        unarch_pack_path = self.create_fake_package(model_pack_name, dest='tmp')
        arch_path = f"{os.path.join(macsydata_tmp, model_pack_name)}-{model_pack_vers}.tar.gz"

        with tarfile.open(arch_path, "w:gz") as arch:
            arch.add(unarch_pack_path, arcname=model_pack_name)
        shutil.rmtree(unarch_pack_path)

        self.args.model_package = arch_path
        self.args.cache = macsydata_cache
        self.args.user = False
        self.args.upgrade = False
        self.args.force = False
        self.args.target = macsydata_target
        self.args.no_clean = False

        with self.assertRaises(RuntimeError) as ctx:
            macsydata.do_install(self.args)
        self.assertEqual(str(ctx.exception),
                         f"'{macsydata_target}' already exist and is not a directory."
                         )


    def test_install_local_already_installed(self):
        model_pack_name = 'fake_pack'
        model_pack_vers = '0.0b2'
        macsydata_cache = os.path.join(self.tmpdir, 'cache')
        os.mkdir(macsydata_cache)
        macsydata_tmp = os.path.join(self.tmpdir, 'tmp')
        os.mkdir(macsydata_tmp)
        macsydata_dest = os.path.join(self.tmpdir, 'models')

        unarch_pack_path = self.create_fake_package(model_pack_name, dest='tmp')
        arch_path = f"{os.path.join(macsydata_tmp, model_pack_name)}-{model_pack_vers}.tar.gz"

        with tarfile.open(arch_path, "w:gz") as arch:
            arch.add(unarch_pack_path, arcname=model_pack_name)
        shutil.rmtree(unarch_pack_path)

        self.args.model_package = arch_path
        self.args.cache = macsydata_cache
        self.args.user = False
        self.args.upgrade = False
        self.args.force = False
        self.args.target = macsydata_dest
        self.args.no_clean = False

        macsydata.Config.models_dir = lambda x: self.models_dir
        try:
            with self.catch_log(log_name='macsydata'):
                macsydata.do_install(self.args)
            with self.catch_log(log_name='macsydata') as log:
                macsydata.do_install(self.args)
                msg_log = log.get_value().strip()
            expected_log = f"""Requirement already satisfied: {model_pack_name}=={model_pack_vers} in {os.path.join(self.models_dir[0], model_pack_name)}.
To force installation use option -f --force-reinstall."""
            self.assertEqual(msg_log, expected_log)
        finally:
            del macsydata.Config.models_dir


    def test_install_local_already_installed_force(self):
        model_pack_name = 'fake_pack'
        model_pack_vers = '0.0b2'
        macsydata_cache = os.path.join(self.tmpdir, 'cache')
        os.mkdir(macsydata_cache)
        macsydata_tmp = os.path.join(self.tmpdir, 'tmp')
        os.mkdir(macsydata_tmp)
        macsydata_dest = os.path.join(self.tmpdir, 'models')

        unarch_pack_path = self.create_fake_package(model_pack_name, dest='tmp')
        arch_path = f"{os.path.join(macsydata_tmp, model_pack_name)}-{model_pack_vers}.tar.gz"

        with tarfile.open(arch_path, "w:gz") as arch:
            arch.add(unarch_pack_path, arcname=model_pack_name)
        shutil.rmtree(unarch_pack_path)

        self.args.model_package = arch_path
        self.args.cache = macsydata_cache
        self.args.user = False
        self.args.upgrade = False
        self.args.force = False
        self.args.target = macsydata_dest
        self.args.no_clean = False

        macsydata.Config.models_dir = lambda x: self.models_dir
        try:
            with self.catch_log(log_name='macsydata'):
                macsydata.do_install(self.args)

            self.args.force = True
            # remove README file to check if reinstall works
            os.unlink(os.path.join(self.models_dir[0], model_pack_name, 'README'))

            with self.catch_log(log_name='macsydata') as log:
                macsydata.do_install(self.args)
                msg_log = log.get_value().strip()
            expected_log = f"""Extracting {model_pack_name} ({model_pack_vers}).
Installing {model_pack_name} ({model_pack_vers}) in {self.models_dir[0]}
Cleaning.
The models {model_pack_name} ({model_pack_vers}) have been installed successfully."""
            self.assertEqual(msg_log, expected_log)
            self.assertTrue(os.path.exists(os.path.join(self.models_dir[0], model_pack_name, 'README')))
        finally:
            del macsydata.Config.models_dir


    def test_install_installed_package_corrupted(self):
        # there is no metadata file
        # the package is not installable

        model_pack_name = 'fake_pack'
        model_pack_vers = '0.0b2'
        macsydata_cache = os.path.join(self.tmpdir, 'cache')
        os.mkdir(macsydata_cache)
        macsydata_tmp = os.path.join(self.tmpdir, 'tmp')
        os.mkdir(macsydata_tmp)
        macsydata_dest = os.path.join(self.tmpdir, 'models')

        unarch_pack_path = self.create_fake_package(model_pack_name, metadata=False, dest='tmp')
        arch_path = f"{os.path.join(macsydata_tmp, model_pack_name)}-{model_pack_vers}.tar.gz"

        # create a archive of the fake pack
        with tarfile.open(arch_path, "w:gz") as arch:
            arch.add(unarch_pack_path, arcname=model_pack_name)
        shutil.rmtree(unarch_pack_path)

        self.args.model_package = arch_path
        self.args.cache = macsydata_cache
        self.args.user = False
        self.args.upgrade = False
        self.args.force = False
        self.args.target = macsydata_dest
        self.args.no_clean = False

        macsydata.Config.models_dir = lambda x: self.models_dir
        try:
            with self.catch_log(log_name='macsydata') as log:
                with self.assertRaises(MacsydataError):
                    macsydata.do_install(self.args)
                msg_log = log.get_value().strip()
                expected_log = (f"Extracting {model_pack_name} ({model_pack_vers})."
                                f"\nFailed to install '{model_pack_name}-{model_pack_vers}' : The model package has no 'metadata.yml' file."
                                f"\nPlease contact the package maintainer. (local)")
                self.assertEqual(expected_log, msg_log)
        finally:
            del macsydata.Config.models_dir


    def test_install_remote(self):
        model_pack_name = 'fake_pack'
        model_pack_vers = '0.0b2'
        macsydata_cache = os.path.join(self.tmpdir, 'cache')
        os.mkdir(macsydata_cache)
        macsydata_tmp = os.path.join(self.tmpdir, 'tmp')
        os.mkdir(macsydata_tmp)
        macsydata_dest = os.path.join(self.tmpdir, 'models')

        self.args.model_package = model_pack_name
        self.args.cache = macsydata_cache
        self.args.user = False
        self.args.upgrade = False
        self.args.force = False
        self.args.org = 'macsy-foo-bar'  # to be sure that the network function are mocked
        self.args.target = macsydata_dest
        self.args.no_clean = False

        # functions which do net operations
        # so we need to mock them
        get_remote_available_versions = macsydata._get_remote_available_versions
        macsydata._get_remote_available_versions = lambda p_nam, org: [model_pack_vers]
        remote_exists = macsydata.RemoteModelIndex.remote_exists
        macsydata.RemoteModelIndex.remote_exists = lambda x: True
        remote_download = macsydata.RemoteModelIndex.download
        macsydata.RemoteModelIndex.download = self._fake_download
        macsydata.Config.models_dir = lambda x: self.models_dir
        try:
            with self.catch_log(log_name='macsydata'):
                macsydata.do_install(self.args)
            expected_pack_path = os.path.join(self.models_dir[0], model_pack_name)
            self.assertTrue(os.path.exists(expected_pack_path))
            self.assertTrue(os.path.isdir(expected_pack_path))
            self.assertTrue(os.path.exists(os.path.join(expected_pack_path, 'metadata.yml')))
            self.assertTrue(os.path.exists(os.path.join(expected_pack_path, 'README')))
            self.assertTrue(os.path.exists(os.path.join(expected_pack_path, 'definitions')))
            self.assertTrue(os.path.exists(os.path.join(expected_pack_path, 'profiles')))
        finally:
            del macsydata.Config.models_dir
            macsydata._get_remote_available_versions = get_remote_available_versions
            macsydata.RemoteModelIndex.remote_exists = remote_exists
            macsydata.RemoteModelIndex.download = remote_download


    def test_install_remote_spec_not_found(self):
        model_pack_name = 'fake_pack'
        model_pack_vers = '0.0b2'
        macsydata_cache = os.path.join(self.tmpdir, 'cache')
        os.mkdir(macsydata_cache)
        macsydata_tmp = os.path.join(self.tmpdir, 'tmp')
        os.mkdir(macsydata_tmp)

        self.args.model_package = f"{model_pack_name}>{model_pack_vers}"
        self.args.cache = macsydata_cache
        self.args.user = False
        self.args.upgrade = False
        self.args.force = False
        self.args.org = 'macsy-foo-bar'  # to be sure that the network function are mocked
        self.args.target = None
        self.args.no_clean = False

        # functions which do net operations
        # so we need to mock them
        get_remote_available_versions = macsydata._get_remote_available_versions
        macsydata._get_remote_available_versions = lambda p_nam, org: [model_pack_vers]
        remote_exists = macsydata.RemoteModelIndex.remote_exists
        macsydata.RemoteModelIndex.remote_exists = lambda x: True
        remote_download = macsydata.RemoteModelIndex.download
        macsydata.RemoteModelIndex.download = self._fake_download
        macsydata.Config.models_dir = lambda x: self.models_dir
        try:
            with self.catch_log(log_name='macsydata') as log:
                macsydata.do_install(self.args)
                log_msg = log.get_value().strip()
            self.assertEqual(log_msg,
                             f"Could not find version that satisfied '{self.args.model_package}'")
        finally:
            del macsydata.Config.models_dir
            macsydata._get_remote_available_versions = get_remote_available_versions
            macsydata.RemoteModelIndex.remote_exists = remote_exists
            macsydata.RemoteModelIndex.download = remote_download


    def test_install_remote_already_in_local(self):
        model_pack_name = 'fake_pack'
        model_pack_vers = '0.0b2'
        macsydata_cache = os.path.join(self.tmpdir, 'cache')
        os.mkdir(macsydata_cache)
        macsydata_tmp = os.path.join(self.tmpdir, 'tmp')
        os.mkdir(macsydata_tmp)

        self.create_fake_package(model_pack_name, dest='models')

        self.args.model_package = f"{model_pack_name}>{model_pack_vers}"
        self.args.cache = macsydata_cache
        self.args.user = False
        self.args.upgrade = False
        self.args.force = False
        self.args.org = 'macsy-foo-bar'  # to be sure that the network function are mocked
        self.args.target = None
        self.args.no_clean = False

        # function which doing net operations
        # so we need to mock them
        get_remote_available_versions = macsydata._get_remote_available_versions
        macsydata._get_remote_available_versions = lambda p_nam, org: [model_pack_vers]
        remote_exists = macsydata.RemoteModelIndex.remote_exists
        macsydata.RemoteModelIndex.remote_exists = lambda x: True
        remote_download = macsydata.RemoteModelIndex.download
        macsydata.RemoteModelIndex.download = self._fake_download
        macsydata.Config.models_dir = lambda x: self.models_dir
        try:
            with self.catch_log(log_name='macsydata') as log:
                macsydata.do_install(self.args)
                log_msg = log.get_value().strip()
            self.assertEqual(log_msg,
                             f"""Requirement already satisfied: {self.args.model_package} in {os.path.join(self.models_dir[0], model_pack_name)}.
To force installation use option -f --force-reinstall.""")
        finally:
            del macsydata.Config.models_dir
            macsydata._get_remote_available_versions = get_remote_available_versions
            macsydata.RemoteModelIndex.remote_exists = remote_exists
            macsydata.RemoteModelIndex.download = remote_download


    def test_install_remote_already_in_local_force(self):
        model_pack_name = 'fake_pack'
        model_pack_vers = '0.0b2'
        macsydata_cache = os.path.join(self.tmpdir, 'cache')
        os.mkdir(macsydata_cache)
        macsydata_tmp = os.path.join(self.tmpdir, 'tmp')
        os.mkdir(macsydata_tmp)
        macsydata_dest = os.path.join(self.tmpdir, 'models')

        self.create_fake_package(model_pack_name, dest='models')

        self.args.model_package = f"{model_pack_name}>{model_pack_vers}"
        self.args.cache = macsydata_cache
        self.args.user = False
        self.args.upgrade = False
        self.args.force = True
        self.args.org = 'macsy-foo-bar'  # to be sure that the network function are mocked
        self.args.target = macsydata_dest
        self.args.no_clean = False

        # function which doing net operations
        # so we need to mock them
        get_remote_available_versions = macsydata._get_remote_available_versions
        macsydata._get_remote_available_versions = lambda p_nam, org: [model_pack_vers]
        remote_exists = macsydata.RemoteModelIndex.remote_exists
        macsydata.RemoteModelIndex.remote_exists = lambda x: True
        remote_download = macsydata.RemoteModelIndex.download
        macsydata.RemoteModelIndex.download = self._fake_download
        macsydata.Config.models_dir = lambda x: self.models_dir
        try:
            with self.catch_log(log_name='macsydata'):
                macsydata.do_install(self.args)
            expected_pack_path = os.path.join(self.models_dir[0], model_pack_name)
            self.assertTrue(os.path.exists(expected_pack_path))
            self.assertTrue(os.path.isdir(expected_pack_path))
            self.assertTrue(os.path.exists(os.path.join(expected_pack_path, 'metadata.yml')))
            self.assertTrue(os.path.exists(os.path.join(expected_pack_path, 'README')))
            self.assertTrue(os.path.exists(os.path.join(expected_pack_path, 'definitions')))
            self.assertTrue(os.path.exists(os.path.join(expected_pack_path, 'profiles')))
        finally:
            del macsydata.Config.models_dir
            macsydata._get_remote_available_versions = get_remote_available_versions
            macsydata.RemoteModelIndex.remote_exists = remote_exists
            macsydata.RemoteModelIndex.download = remote_download


    def test_install_remote_lower_in_local(self):
        model_pack_name = 'fake_pack'
        model_pack_vers = '1.0'
        macsydata_cache = os.path.join(self.tmpdir, 'cache')
        os.mkdir(macsydata_cache)
        macsydata_tmp = os.path.join(self.tmpdir, 'tmp')
        os.mkdir(macsydata_tmp)

        self.create_fake_package(model_pack_name, dest='models')

        self.args.model_package = f"{model_pack_name}=={model_pack_vers}"
        self.args.cache = macsydata_cache
        self.args.user = False
        self.args.upgrade = False
        self.args.force = False
        self.args.org = 'macsy-foo-bar'  # to be sure that the network function are mocked
        self.args.target = None
        self.args.no_clean = False
        self.args.tool_name = 'msl_data'

        # function which doing net operations
        # so we need to mock them
        get_remote_available_versions = macsydata._get_remote_available_versions
        macsydata._get_remote_available_versions = lambda p_nam, org: [model_pack_vers]
        remote_exists = macsydata.RemoteModelIndex.remote_exists
        macsydata.RemoteModelIndex.remote_exists = lambda x: True
        remote_download = macsydata.RemoteModelIndex.download
        macsydata.RemoteModelIndex.download = self._fake_download
        macsydata.Config.models_dir = lambda x: self.models_dir
        try:
            with self.catch_log(log_name='macsydata') as log:
                macsydata.do_install(self.args)
                log_msg = log.get_value().strip()
            self.assertEqual(log_msg,
                             f"""{model_pack_name} (0.0b2) is already installed but {model_pack_vers} version is available.
To install it please run '{self.args.tool_name} install --upgrade {model_pack_name}'""")
        finally:
            del macsydata.Config.models_dir
            macsydata._get_remote_available_versions = get_remote_available_versions
            macsydata.RemoteModelIndex.remote_exists = remote_exists
            macsydata.RemoteModelIndex.download = remote_download


    def test_install_remote_upper_in_local(self):
        pack_name = 'fake_pack'
        pack_vers = '0.0b1'
        macsydata_cache = os.path.join(self.tmpdir, 'cache')
        os.mkdir(macsydata_cache)
        macsydata_tmp = os.path.join(self.tmpdir, 'tmp')
        os.mkdir(macsydata_tmp)

        self.create_fake_package(pack_name, dest='models')

        self.args.model_package = f"{pack_name}>{pack_vers}"
        self.args.cache = macsydata_cache
        self.args.user = False
        self.args.upgrade = False
        self.args.force = False
        self.args.org = 'macsy-foo-bar'  # to be sure that the network function are mocked
        self.args.target = None
        self.args.no_clean = False

        # function which doing net operations
        # so we need to mock them
        get_remote_available_versions = macsydata._get_remote_available_versions
        macsydata._get_remote_available_versions = lambda p_nam, org: [pack_vers]
        remote_exists = macsydata.RemoteModelIndex.remote_exists
        macsydata.RemoteModelIndex.remote_exists = lambda x: True
        remote_download = macsydata.RemoteModelIndex.download
        macsydata.RemoteModelIndex.download = self._fake_download
        macsydata.Config.models_dir = lambda x: self.models_dir
        try:
            with self.catch_log(log_name='macsydata') as log:
                macsydata.do_install(self.args)
                log_msg = log.get_value().strip()
            self.assertEqual(log_msg,
                             f"""{pack_name} (0.0b2) is already installed.
To downgrade to 0.0b1 use option -f --force-reinstall.""")
        finally:
            del macsydata.Config.models_dir
            macsydata._get_remote_available_versions = get_remote_available_versions
            macsydata.RemoteModelIndex.remote_exists = remote_exists
            macsydata.RemoteModelIndex.download = remote_download


    @unittest.skipIf(os.getuid() == 0, 'Skip test if run as root')
    def test_install_remote_permision_error(self):
        model_pack_name = 'fake_pack'
        model_pack_vers = '0.0b2'
        macsydata_cache = os.path.join(self.tmpdir, 'cache')
        os.mkdir(macsydata_cache)
        macsydata_tmp = os.path.join(self.tmpdir, 'tmp')
        os.mkdir(macsydata_tmp)
        macsydata_dest = os.path.join(self.tmpdir, 'models')

        os.chmod(self.models_dir[0], 0o111)

        self.args.model_package = model_pack_name
        self.args.cache = macsydata_cache
        self.args.user = False
        self.args.upgrade = False
        self.args.force = False
        self.args.org = 'macsy-foo-bar'  # to be sure that the network function are mocked
        self.args.target = macsydata_dest
        self.args.no_clean = False

        # functions which do net operations
        # so we need to mock them
        get_remote_available_versions = macsydata._get_remote_available_versions
        macsydata._get_remote_available_versions = lambda p_nam, org: [model_pack_vers]
        remote_exists = macsydata.RemoteModelIndex.remote_exists
        macsydata.RemoteModelIndex.remote_exists = lambda x: True
        remote_download = macsydata.RemoteModelIndex.download
        macsydata.RemoteModelIndex.download = self._fake_download
        macsydata.Config.models_dir = lambda x: self.models_dir
        try:
            with self.catch_log(log_name='macsydata') as log:
                with self.assertRaises(ValueError):
                    macsydata.do_install(self.args)
                log_msg = log.get_value().strip()
            self.maxDiff = None
            self.assertEqual(log_msg,
                             f"""{self.models_dir[0]} is not readable: [Errno 13] Permission denied: '{self.models_dir[0]}' : skip it.
Downloading {model_pack_name} ({model_pack_vers}).
Extracting {model_pack_name} ({model_pack_vers}).
Installing {model_pack_name} ({model_pack_vers}) in {self.models_dir[0]}
{self.models_dir[0]} is not writable: [Errno 13] Permission denied: '{os.path.join(self.models_dir[0], model_pack_name)}'
Maybe you can use --user option to install in your HOME.""")
        finally:
            os.chmod(self.models_dir[0], 0o777)
            del macsydata.Config.models_dir
            macsydata._get_remote_available_versions = get_remote_available_versions
            macsydata.RemoteModelIndex.remote_exists = remote_exists
            macsydata.RemoteModelIndex.download = remote_download


    def test_uninstall(self):
        pack_name = 'fake_1'
        path = self.create_fake_package(pack_name, dest=self.models_dir[0])
        self.args.model_package = pack_name
        self.args.models_dir = None

        registry = ModelRegistry()
        for model_loc in scan_models_dir(self.models_dir[0]):
            registry.add(model_loc)

        def fake_find_all_installed_package(models_dir=None, prog_name='macsylib'):
            return registry

        def fake_find_installed_package(model_pack_name, models_dir=None, package_name='macsylib'):
            return registry[model_pack_name]

        macsydata._find_all_installed_packages = fake_find_all_installed_package

        find_local_package = macsydata._find_installed_package
        macsydata._find_installed_package = fake_find_installed_package
        try:
            with self.catch_log(log_name='macsydata') as log:
                macsydata.do_uninstall(self.args)
                log_msg = log.get_value().strip()
        finally:
            macsydata._find_installed_package = find_local_package

        expected_msg = f"models '{pack_name}' in {path} uninstalled."
        self.assertEqual(log_msg, expected_msg)
        self.assertFalse(os.path.exists(path))

        self.args.model_package = 'foo'
        find_local_package = macsydata._find_installed_package

        def fake_find_installed_package(model_pack_name, models_dir=None, package_name='macsylib'): return None

        macsydata._find_installed_package = fake_find_installed_package
        try:
            with self.catch_log(log_name='macsydata') as log:
                with self.assertRaises(ValueError):
                    macsydata.do_uninstall(self.args)
                log_msg = log.get_value().strip()
        finally:
            macsydata._find_installed_package = find_local_package
        expected_msg = f"Models '{self.args.model_package}' not found locally."
        self.assertEqual(log_msg, expected_msg)


    def test_search_in_pack_name(self):
        self.args.pattern = 'Foo'
        self.args.org = 'macsy-foo-bar'  # to be sure that the network function are mocked
        self.args.careful = False
        self.args.match_case = False
        self.args.models_dir = None
        self.args.no_clean = False

        # functions which do net operations
        # so we need to mock them
        remote_exists = macsydata.RemoteModelIndex.remote_exists
        macsydata.RemoteModelIndex.remote_exists = lambda x: True
        remote_list_packages = macsydata.RemoteModelIndex.list_packages
        macsydata.RemoteModelIndex.list_packages = lambda x: ['FOO']
        remote_list_package_vers = macsydata.RemoteModelIndex.list_package_vers
        macsydata.RemoteModelIndex.list_package_vers = lambda x, pack_nam: ['0.1']
        remote_get_metadata = macsydata.RemoteModelIndex.get_metadata
        macsydata.RemoteModelIndex.get_metadata = lambda x, pac_nam: {'vers': '0.1',
                                                                      'short_desc': 'this is a foo desc_pattern'}
        try:
            with self.catch_io(out=True):
                macsydata.do_search(self.args)
                stdout = sys.stdout.getvalue().strip()
            self.assertEqual(stdout,  'FOO (0.1)                  - this is a foo desc_pattern')
        finally:
            macsydata.RemoteModelIndex.remote_exists = remote_exists
            macsydata.RemoteModelIndex.list_packages = remote_list_packages
            macsydata.RemoteModelIndex.get_metadata = remote_get_metadata
            macsydata.RemoteModelIndex.list_package_vers = remote_list_package_vers

        # case where package is not versioned
        self.args.pattern = 'Foo'
        self.args.org = 'macsy-foo-bar'  # to be sure that the network function are mocked
        self.args.careful = False
        self.args.match_case = False
        self.args.no_clean = False

        # functions which do net operations
        # so we need to mock them
        remote_exists = macsydata.RemoteModelIndex.remote_exists
        macsydata.RemoteModelIndex.remote_exists = lambda x: True
        remote_list_packages = macsydata.RemoteModelIndex.list_packages
        macsydata.RemoteModelIndex.list_packages = lambda x: ['FOO']
        remote_list_package_vers = macsydata.RemoteModelIndex.list_package_vers
        macsydata.RemoteModelIndex.list_package_vers = lambda x, pack_nam: []
        remote_get_metadata = macsydata.RemoteModelIndex.get_metadata
        macsydata.RemoteModelIndex.get_metadata = lambda x, pac_nam: {'short_desc': 'this is a foo desc_pattern'}
        try:
            with self.catch_io(out=True):
                macsydata.do_search(self.args)
                stdout = sys.stdout.getvalue().strip()
            self.assertEqual(stdout, '')
        finally:
            macsydata.RemoteModelIndex.remote_exists = remote_exists
            macsydata.RemoteModelIndex.list_packages = remote_list_packages
            macsydata.RemoteModelIndex.get_metadata = remote_get_metadata
            macsydata.RemoteModelIndex.list_package_vers = remote_list_package_vers


    def test_search_in_pack_name_match_case(self):
        self.args.pattern = 'Foo'.lower()
        self.args.org = 'macsy-foo-bar'  # to be sure that the network function are mocked
        self.args.careful = False
        self.args.match_case = True
        self.args.no_clean = False

        # functions which do net operations
        # so we need to mock them
        remote_exists = macsydata.RemoteModelIndex.remote_exists
        macsydata.RemoteModelIndex.remote_exists = lambda x: True
        remote_list_packages = macsydata.RemoteModelIndex.list_packages
        macsydata.RemoteModelIndex.list_packages = lambda x: ['FOO']
        remote_list_package_vers = macsydata.RemoteModelIndex.list_package_vers
        macsydata.RemoteModelIndex.list_package_vers = lambda x, pack_nam: ['0.1']
        remote_get_metadata = macsydata.RemoteModelIndex.get_metadata
        macsydata.RemoteModelIndex.get_metadata = lambda x, pac_nam: {'vers': '0.1',
                                                                      'short_desc': 'this is a foo desc_pattern'}
        try:
            with self.catch_io(out=True):
                macsydata.do_search(self.args)
                stdout = sys.stdout.getvalue().strip()
            self.assertEqual(stdout,  '')
        finally:
            macsydata.RemoteModelIndex.remote_exists = remote_exists
            macsydata.RemoteModelIndex.list_packages = remote_list_packages
            macsydata.RemoteModelIndex.get_metadata = remote_get_metadata
            macsydata.RemoteModelIndex.list_package_vers = remote_list_package_vers


    def test_search_in_pack_desc(self):
        self.args.pattern = 'sc_pat'
        self.args.org = 'macsy-foo-bar'  # to be sure that the network function are mocked
        self.args.careful = True
        self.args.match_case = False
        self.args.no_clean = False

        # functions which do net operations
        # so we need to mock them
        remote_exists = macsydata.RemoteModelIndex.remote_exists
        macsydata.RemoteModelIndex.remote_exists = lambda x: True
        remote_list_packages = macsydata.RemoteModelIndex.list_packages
        macsydata.RemoteModelIndex.list_packages = lambda x: ['FOO']
        remote_list_package_vers = macsydata.RemoteModelIndex.list_package_vers
        macsydata.RemoteModelIndex.list_package_vers = lambda x, pack_nam: ['0.1']
        remote_get_metadata = macsydata.RemoteModelIndex.get_metadata
        macsydata.RemoteModelIndex.get_metadata = lambda x, pac_nam: {'vers': '0.1',
                                                                      'short_desc': 'this is a foo desc_pattern'}
        try:
            with self.catch_io(out=True):
                macsydata.do_search(self.args)
                stdout = sys.stdout.getvalue().strip()
            self.assertEqual(stdout,  'FOO (0.1)                  - this is a foo desc_pattern')
        finally:
            macsydata.RemoteModelIndex.remote_exists = remote_exists
            macsydata.RemoteModelIndex.list_packages = remote_list_packages
            macsydata.RemoteModelIndex.get_metadata = remote_get_metadata
            macsydata.RemoteModelIndex.list_package_vers = remote_list_package_vers

        # test when package is not versioned
        self.args.pattern = 'sc_pat'
        self.args.org = 'macsy-foo-bar'  # to be sure that the network function are mocked
        self.args.careful = True
        self.args.match_case = False

        # functions which do net operations
        # so we need to mock them
        remote_exists = macsydata.RemoteModelIndex.remote_exists
        macsydata.RemoteModelIndex.remote_exists = lambda x: True
        remote_list_packages = macsydata.RemoteModelIndex.list_packages
        macsydata.RemoteModelIndex.list_packages = lambda x: ['FOO']
        remote_list_package_vers = macsydata.RemoteModelIndex.list_package_vers
        macsydata.RemoteModelIndex.list_package_vers = lambda x, pack_nam: []
        remote_get_metadata = macsydata.RemoteModelIndex.get_metadata
        macsydata.RemoteModelIndex.get_metadata = lambda x, pac_nam: {'short_desc': 'this is a foo desc_pattern'}
        try:
            with self.catch_io(out=True):
                macsydata.do_search(self.args)
                stdout = sys.stdout.getvalue().strip()
            self.assertEqual(stdout, '')
        finally:
            macsydata.RemoteModelIndex.remote_exists = remote_exists
            macsydata.RemoteModelIndex.list_packages = remote_list_packages
            macsydata.RemoteModelIndex.get_metadata = remote_get_metadata
            macsydata.RemoteModelIndex.list_package_vers = remote_list_package_vers


    def test_search_in_pack_desc_match_case(self):
        self.args.pattern = 'sc_pat'.upper()
        self.args.org = 'macsy-foo-bar'  # to be sure that the network function are mocked
        self.args.careful = True
        self.args.match_case = True
        self.args.no_clean = False

        # functions which do net operations
        # so we need to mock them
        remote_exists = macsydata.RemoteModelIndex.remote_exists
        macsydata.RemoteModelIndex.remote_exists = lambda x: True
        remote_list_packages = macsydata.RemoteModelIndex.list_packages
        macsydata.RemoteModelIndex.list_packages = lambda x: ['FOO']
        remote_list_package_vers = macsydata.RemoteModelIndex.list_package_vers
        macsydata.RemoteModelIndex.list_package_vers = lambda x, pack_nam: ['0.1']
        remote_get_metadata = macsydata.RemoteModelIndex.get_metadata
        macsydata.RemoteModelIndex.get_metadata = lambda x, pac_nam: {'vers': '0.1',
                                                                      'short_desc': 'this is a foo desc_pattern'}
        try:
            with self.catch_io(out=True):
                macsydata.do_search(self.args)
                stdout = sys.stdout.getvalue().strip()
            self.assertEqual(stdout,  '')
        finally:
            macsydata.RemoteModelIndex.remote_exists = remote_exists
            macsydata.RemoteModelIndex.list_packages = remote_list_packages
            macsydata.RemoteModelIndex.get_metadata = remote_get_metadata
            macsydata.RemoteModelIndex.list_package_vers = remote_list_package_vers


    def test_search_reach_limit(self):
        self.args.pattern = 'sc_pat'.upper()
        self.args.org = 'macsy-foo-bar'  # to be sure that the network function are mocked
        self.args.careful = True
        self.args.match_case = True
        self.args.no_clean = False

        # functions which do net operations
        # so we need to mock them
        def fake_remote(self):
            raise MacsyDataLimitError('bla')

        remote_exists = macsydata.RemoteModelIndex.remote_exists
        macsydata.RemoteModelIndex.remote_exists = fake_remote
        remote_list_packages = macsydata.RemoteModelIndex.list_packages
        macsydata.RemoteModelIndex.list_packages = lambda x: ['FOO']
        remote_list_package_vers = macsydata.RemoteModelIndex.list_package_vers
        macsydata.RemoteModelIndex.list_package_vers = lambda x, pack_nam: ['0.1']
        remote_get_metadata = macsydata.RemoteModelIndex.get_metadata
        macsydata.RemoteModelIndex.get_metadata = lambda x, pac_nam: {'vers': '0.1',
                                                                      'short_desc': 'this is a foo desc_pattern'}
        try:
            with self.catch_io(out=True):
                with self.catch_log(log_name='macsydata') as log:
                    macsydata.do_search(self.args)
                    log_msg = log.get_value().strip()
                stdout = sys.stdout.getvalue().strip()
            self.assertEqual(stdout,  '')
            self.assertEqual(log_msg, 'bla')
        finally:
            macsydata.RemoteModelIndex.remote_exists = remote_exists
            macsydata.RemoteModelIndex.list_packages = remote_list_packages
            macsydata.RemoteModelIndex.get_metadata = remote_get_metadata
            macsydata.RemoteModelIndex.list_package_vers = remote_list_package_vers


    @unittest.skipIf(git is None, "GitPython is not installed")
    def test_init_package_minimal(self):
        self.args.model_package = 'minimal_pack'
        self.args.maintainer = 'John Doe'
        self.args.email = 'john.doe@domain.org'
        self.args.authors = 'Jim Doe, John Doe'
        self.args.license = None
        self.args.holders = None
        self.args.desc = None
        self.args.models_dir = self.models_dir[0]
        self.args.no_clean = False
        # see below (test_init_package_complete)
        # why a do a mock for localtime
        fake_time = namedtuple('FakeTime', ['tm_year'])
        local_time_ori = macsydata.time.localtime
        macsydata.time.localtime = lambda: fake_time(2022)
        try:
            with self.catch_log(log_name='macsydata'):
                macsydata.do_init_package(self.args)

            files = ('README.md', 'metadata.yml', 'model_conf.xml', os.path.join('definitions', 'model_example.xml'))
            for f_name in files:
                with self.subTest(file_name=f_name):
                    expected_file = self.find_data(self.args.model_package, f_name)
                    got_file = os.path.join(self.args.models_dir, self.args.model_package, f_name)
                    self.assertFileEqual(expected_file, got_file)
        finally:
            macsydata.time.localtime = local_time_ori


    @unittest.skipIf(git is None, "GitPython is not installed")
    def test_init_package_license(self):
        self.args.model_package = 'init_pack_license'
        self.args.maintainer = 'John Doe'
        self.args.email = 'john.doe@domain.org'
        self.args.authors = 'Jim Doe, John Doe'
        self.args.license = 'cc-by-nc-sa'
        self.args.holders = None
        self.args.desc = 'description in one line of this package'
        self.args.models_dir = self.models_dir[0]
        self.args.no_clean = False
        # see below (test_init_package_complete)
        # why a do a mock for localtime
        fake_time = namedtuple('FakeTime', ['tm_year'])
        local_time_ori = macsydata.time.localtime
        macsydata.time.localtime = lambda: fake_time(2022)
        try:
            with self.catch_log(log_name='macsydata'):
                macsydata.do_init_package(self.args)

            files = ('README.md', 'metadata.yml', 'model_conf.xml', os.path.join('definitions', 'model_example.xml'))
            for f_name in files:
                with self.subTest(file_name=f_name):
                    expected_file = self.find_data(self.args.model_package, f_name)
                    got_file = os.path.join(self.args.models_dir, self.args.model_package, f_name)
                    self.assertFileEqual(expected_file, got_file)
        finally:
            macsydata.time.localtime = local_time_ori


    @unittest.skipIf(git is None, "GitPython is not installed")
    def test_init_package_complete(self):
        self.args.model_package = 'init_pack'
        self.args.maintainer = 'John Doe'
        self.args.email = 'john.doe@domain.org'
        self.args.authors = 'Jim Doe, John Doe'
        self.args.license = 'cc-by-nc-sa'
        self.args.holders = 'Pasteur'
        self.args.desc = 'description in one line of this package'
        self.args.models_dir = self.models_dir[0]
        self.args.no_clean = False
        # do_init_package call localtime to get year
        # and put it in copyright filed of metadata
        # so I do monkey patching to get reliable year
        # otherwise I have to adapt the test each new year ;-(
        fake_time = namedtuple('FakeTime', ['tm_year'])
        local_time_ori = macsydata.time.localtime
        macsydata.time.localtime = lambda: fake_time(2022)
        try:
            with self.catch_log(log_name='macsydata'):
                macsydata.do_init_package(self.args)

            files = ('README.md', 'metadata.yml', 'model_conf.xml', os.path.join('definitions', 'model_example.xml'))
            for f_name in files:
                with self.subTest(file_name=f_name):
                    expected_file = self.find_data(self.args.model_package, f_name)
                    got_file = os.path.join(self.args.models_dir, self.args.model_package, f_name)
                    self.assertFileEqual(expected_file, got_file)
        finally:
            macsydata.time.localtime = local_time_ori


    @unittest.skipIf(git is None, "GitPython is not installed")
    def test_init_empty_dir_exists(self):
        self.args.model_package = 'init_pack'
        self.args.maintainer = 'John Doe'
        self.args.email = 'john.doe@domain.org'
        self.args.authors = 'Jim Doe, John Doe'
        self.args.license = 'cc-by-nc-sa'
        self.args.holders = 'Pasteur'
        self.args.desc = 'description in one line of this package'
        self.args.models_dir = self.models_dir[0]
        self.args.no_clean = False
        # see above (test_init_package_complete)
        # why a do a mock for localtime
        fake_time = namedtuple('FakeTime', ['tm_year'])
        local_time_ori = macsydata.time.localtime
        macsydata.time.localtime = lambda: fake_time(2022)
        os.makedirs(os.path.join(self.models_dir[0], self.args.model_package))
        try:
            with self.catch_log(log_name='macsydata'):
                macsydata.do_init_package(self.args)

            files = ('README.md', 'metadata.yml', 'model_conf.xml', os.path.join('definitions', 'model_example.xml'))
            for f_name in files:
                with self.subTest(file_name=f_name):
                    expected_file = self.find_data(self.args.model_package, f_name)
                    got_file = os.path.join(self.args.models_dir, self.args.model_package, f_name)
                    self.assertFileEqual(expected_file, got_file)
        finally:
            macsydata.time.localtime = local_time_ori


    @unittest.skipIf(git is None, "GitPython is not installed")
    def test_init_dir_exists_not_pack(self):
        self.args.model_package = 'init_pack'
        self.args.maintainer = 'John Doe'
        self.args.email = 'john.doe@domain.org'
        self.args.authors = 'Jim Doe, John Doe'
        self.args.license = 'cc-by-nc-sa'
        self.args.holders = 'Pasteur'
        self.args.desc = 'description in one line of this package'
        self.args.models_dir = self.models_dir[0]
        self.args.no_clean = False
        # see above (test_init_package_complete)
        # why a do a mock for localtime
        fake_time = namedtuple('FakeTime', ['tm_year'])
        local_time_ori = macsydata.time.localtime
        macsydata.time.localtime = lambda: fake_time(2022)
        pack_path = os.path.join(self.models_dir[0], self.args.model_package)
        os.makedirs(pack_path)
        os.mkdir(os.path.join(pack_path, 'nimportnaoik'))
        try:
            with self.catch_log(log_name='macsydata') as log:
                with self.assertRaises(ValueError):
                    macsydata.do_init_package(self.args)
                log_msg = log.get_value().strip()
            self.assertEqual(log_msg,
                             f"{pack_path} already exits and not look a model package:"
                             f" There is no definitions, profiles.")

        finally:
            macsydata.time.localtime = local_time_ori

    @unittest.skipIf(git is None, "GitPython is not installed")
    def test_init_dir_exists_look_pack(self):
        self.args.model_package = 'init_pack'
        self.args.maintainer = 'John Doe'
        self.args.email = 'john.doe@domain.org'
        self.args.authors = 'Jim Doe, John Doe'
        self.args.license = 'cc-by-nc-sa'
        self.args.holders = 'Pasteur'
        self.args.desc = 'description in one line of this package'
        self.args.models_dir = self.models_dir[0]
        self.args.no_clean = False
        # see above (test_init_package_complete)
        # why a do a mock for localtime
        fake_time = namedtuple('FakeTime', ['tm_year'])
        local_time_ori = macsydata.time.localtime
        macsydata.time.localtime = lambda: fake_time(2022)
        pack_path = os.path.join(self.models_dir[0], self.args.model_package)
        os.makedirs(pack_path)
        os.mkdir(os.path.join(pack_path, 'definitions'))
        os.mkdir(os.path.join(pack_path, 'profiles'))
        git.Repo.init(pack_path)
        try:
            with self.catch_log(log_name='macsydata'):
                macsydata.do_init_package(self.args)
            files = ('README.md', 'metadata.yml', 'model_conf.xml', os.path.join('definitions', 'model_example.xml'))
            for f_name in files:
                with self.subTest(file_name=f_name):
                    expected_file = self.find_data(self.args.model_package, f_name)
                    got_file = os.path.join(self.args.models_dir, self.args.model_package, f_name)
                    self.assertFileEqual(expected_file, got_file)
            repo = git.Repo(pack_path)
            tree = repo.head.commit.tree
            files_and_dirs = {entry.name for entry in tree}
            # profiles is empty so not in git
            # we list only first level so 'definitions/model_example.xml' does not appear
            self.assertEqual({'COPYRIGHT', 'LICENSE', 'README.md', 'definitions', 'metadata.yml', 'model_conf.xml'},
                             files_and_dirs)
        finally:
            macsydata.time.localtime = local_time_ori


    @unittest.skipIf(git is None, "GitPython is not installed")
    def test_init_existing_pack(self):
        self.args.model_package = 'init_pack'
        self.args.maintainer = 'John Doe'
        self.args.email = 'john.doe@domain.org'
        self.args.authors = 'Jim Doe, John Doe'
        self.args.license = 'cc-by-nc-sa'
        self.args.holders = 'Pasteur'
        self.args.desc = 'description in one line of this package'
        self.args.models_dir = self.models_dir[0]
        self.args.no_clean = False
        # see above (test_init_package_complete)
        # why a do a mock for localtime
        fake_time = namedtuple('FakeTime', ['tm_year'])
        local_time_ori = macsydata.time.localtime
        macsydata.time.localtime = lambda: fake_time(2022)
        pack_path = os.path.join(self.models_dir[0], self.args.model_package)
        with self.catch_log(log_name='macsydata'):
            macsydata.do_init_package(self.args)
        try:
            with self.catch_log(log_name='macsydata'):
                macsydata.do_init_package(self.args)
            files = ('README.md', 'metadata.yml', 'model_conf.xml', os.path.join('definitions', 'model_example.xml'))
            for f_name in files:
                with self.subTest(file_name=f_name):
                    expected_file = self.find_data(self.args.model_package, f_name)
                    got_file = os.path.join(self.args.models_dir, self.args.model_package, f_name)
                    self.assertFileEqual(expected_file, got_file)
            repo = git.Repo(pack_path)
            tree = repo.head.commit.tree
            files_and_dirs = {entry.name for entry in tree}
            # profiles is empty so not in git
            # we list only first level so 'definitions/model_example.xml' does not appear
            self.assertEqual({'COPYRIGHT', 'LICENSE', 'README.md', 'definitions', 'metadata.yml', 'model_conf.xml'},
                             files_and_dirs)
        finally:
            macsydata.time.localtime = local_time_ori


    def test_init_existing_file(self):
        self.args.model_package = 'init_pack'
        self.args.maintainer = 'John Doe'
        self.args.email = 'john.doe@domain.org'
        self.args.authors = 'Jim Doe, John Doe'
        self.args.license = 'cc-by-nc-sa'
        self.args.holders = 'Pasteur'
        self.args.desc = 'description in one line of this package'
        self.args.models_dir = self.models_dir[0]
        self.args.no_clean = False
        # see above (test_init_package_complete)
        # why a do a mock for localtime
        fake_time = namedtuple('FakeTime', ['tm_year'])
        local_time_ori = macsydata.time.localtime
        macsydata.time.localtime = lambda: fake_time(2022)
        pack_path = os.path.join(self.models_dir[0], self.args.model_package)
        open(pack_path, 'w').close()
        try:
            with self.catch_log(log_name='macsydata') as log:
                with self.assertRaises(ValueError):
                    macsydata.do_init_package(self.args)
                log_msg = log.get_value().strip()
                self.assertEqual(log_msg,
                                 f"{pack_path} already exists and is not a directory.")
        finally:
            macsydata.time.localtime = local_time_ori


    def test_build_argparser(self):
        tool_name = 'msl_data'
        cmd = f"{tool_name} install toto>1"
        version = f"{tool_name} version message"
        parser = macsydata.build_arg_parser(macsydata._cmde_line_header(), version)
        args = parser.parse_args(cmd.split()[1:])
        self.assertEqual(args.func.__name__, 'do_install')
        self.assertEqual(args.model_package, 'toto>1')
        self.assertEqual(args.org, 'macsy-models')
        self.assertFalse(args.force)
        self.assertFalse(args.upgrade)
        self.assertFalse(args.user)

        cmd = f"{tool_name} install --org foo --user --force toto>1"
        args = parser.parse_args(cmd.split()[1:])
        self.assertEqual(args.func.__name__, 'do_install')
        self.assertEqual(args.model_package, 'toto>1')
        self.assertEqual(args.org, 'foo')
        self.assertTrue(args.force)
        self.assertFalse(args.upgrade)
        self.assertTrue(args.user)

        cmd = f"{tool_name} uninstall toto"
        args = parser.parse_args(cmd.split()[1:])
        self.assertEqual(args.func.__name__, 'do_uninstall')
        self.assertEqual(args.model_package, 'toto')

        cmd = f"{tool_name} search TXSS"
        args = parser.parse_args(cmd.split()[1:])
        self.assertEqual(args.func.__name__, 'do_search')
        self.assertEqual(args.pattern, 'TXSS')
        self.assertEqual(args.org, 'macsy-models')
        self.assertFalse(args.careful)
        self.assertFalse(args.match_case)

        cmd = f"{tool_name} search -S --match-case TXSS"
        args = parser.parse_args(cmd.split()[1:])
        self.assertEqual(args.func.__name__, 'do_search')
        self.assertEqual(args.pattern, 'TXSS')
        self.assertEqual(args.org, 'macsy-models')
        self.assertTrue(args.careful)
        self.assertTrue(args.match_case)

        cmd = f"{tool_name} download foo"
        args = parser.parse_args(cmd.split()[1:])
        self.assertEqual(args.func.__name__, 'do_download')
        self.assertEqual(args.model_package, 'foo')
        self.assertEqual(args.dest, os.getcwd())
        self.assertEqual(args.org, 'macsy-models')

        cmd = f"{tool_name} available"
        args = parser.parse_args(cmd.split()[1:])
        self.assertEqual(args.func.__name__, 'do_available')

        if git is not None:
            cmd = f"{tool_name} init --model-package foo --authors 'john Doe' --maintainer 'Jim Doe' " \
                  "--email 'jim.doe@my_domain.com'"
            args = parser.parse_args(shlex.split(cmd)[1:])
            self.assertEqual(args.func.__name__, 'do_init_package')
            self.assertEqual(args.model_package, 'foo')
            self.assertEqual(args.authors, 'john Doe')
            self.assertEqual(args.maintainer, 'Jim Doe')
            self.assertEqual(args.email, 'jim.doe@my_domain.com')

    def test_cmd_name(self):
        version = "msl version message"
        parser = macsydata.build_arg_parser(macsydata._cmde_line_header(), version)
        cmd = "msl_data download foo"
        args = parser.parse_args(cmd.split()[1:])
        cmd_name = macsydata.cmd_name(args)
        self.assertEqual(cmd_name, 'msl_data download')

    def test_verbosity_to_log_level(self):
        level = macsydata.verbosity_to_log_level(1)
        self.assertEqual(level, 10)
        level = macsydata.verbosity_to_log_level(5)
        self.assertEqual(level, 1)

    def test_no_subcommand(self):
        cmd = "msl_data"
        parser = macsydata.build_arg_parser(macsydata._cmde_line_header(),
                                            'msl_data version message',
                                            package_name='macsylib', tool_name='msl_data')
        out = io.StringIO()
        parser.print_help(file=out)

        with self.catch_io(out=True):
            macsydata.main(args=cmd.split()[1:])
            stdout = sys.stdout.getvalue().strip()
        self.assertEqual(stdout,
                         out.getvalue().strip())
