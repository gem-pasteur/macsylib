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
import urllib.request
import urllib.error
import json
import io
import shutil
import tarfile
import glob
import yaml
import colorlog
from unittest.mock import patch

import macsylib
from macsylib import model_package
from macsylib.metadata import Maintainer
from macsylib import model_conf_parser
from macsylib.error import MacsydataError, MacsyDataLimitError

from tests import MacsyTest


class TestPackageFunc(MacsyTest):

    def test_parse_arch_path(self):
        self.assertTupleEqual(model_package.parse_arch_path("pack-3.0.tar.gz"),
                              ('pack', '3.0'))
        self.assertTupleEqual(model_package.parse_arch_path("pack-3.0.tgz"),
                              ('pack', '3.0'))

        pack = "pack-3.0.foo"
        with self.assertRaises(ValueError) as ctx:
            model_package.parse_arch_path(pack)
        self.assertEqual(str(ctx.exception),
                         f"{pack} does not seem to be a package (a tarball).")
        pack = "pack.tar.gz"
        with self.assertRaises(ValueError) as ctx:
            model_package.parse_arch_path(pack)
        self.assertEqual(str(ctx.exception),
                         f"{pack} does not seem to not be versioned.")


    def test_init(self):
        with self.assertRaises(TypeError):
            model_package.AbstractModelIndex()


class TestLocalModelIndex(MacsyTest):

    def test_init(self):
        lmi = model_package.LocalModelIndex()
        self.assertEqual(lmi.org_name, 'local')
        expected_cache = os.path.join(tempfile.gettempdir(), 'tmp-macsy-cache')
        self.assertEqual(lmi.cache, expected_cache)

    def test_repos_url(self):
        lmi = model_package.LocalModelIndex()
        self.assertEqual(lmi.repos_url, 'local')


class TestRemoteModelIndex(MacsyTest):

    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory(prefix='test_msf_package_')
        self.tmpdir = self._tmp_dir.name


    def tearDown(self) -> None:
        self._tmp_dir.cleanup()


    def mocked_requests_get(url: str, context:None=None):
        # cannot type the return value the class is defined inside de method

        class MockResponse:
            def __init__(self, data, status_code):
                self.data = io.BytesIO(bytes(data.encode("utf-8")))
                self.status_code = status_code

            def read(self, length=-1):
                return self.data.read(length)

            def __enter__(self):
                return self

            def __exit__(self, type, value, traceback):
                return False

        if url == 'https://test_url_json/':
            resp = {'fake': ['json', 'response']}
            return MockResponse(json.dumps(resp), 200)
        elif url == 'https://test_url_json/limit':
            raise urllib.error.HTTPError(url, 403, 'forbidden', None, None)
        elif url == 'https://api.github.com/orgs/remote_exists_true':
            resp = {'type': 'Organization'}
            return MockResponse(json.dumps(resp), 200)
        elif url == 'https://api.github.com/orgs/remote_exists_false':
            raise urllib.error.HTTPError(url, 404, 'not found', None, None)
        elif url == 'https://api.github.com/orgs/remote_exists_server_error':
            raise urllib.error.HTTPError(url, 500, 'Server Error', None, None)
        elif url == 'https://api.github.com/orgs/remote_exists_unexpected_error':
            raise urllib.error.HTTPError(url, 204, 'No Content', None, None)
        elif url == 'https://api.github.com/orgs/list_packages/repos':
            resp = [{'name': 'model_1'}, {'name': 'model_2'}, {'name':'.github'}]
            return MockResponse(json.dumps(resp), 200)
        elif url == 'https://api.github.com/repos/list_package_vers/model_1/tags':
            resp = [{'name': 'v_1'}, {'name': 'v_2'}]
            return MockResponse(json.dumps(resp), 200)
        elif url == 'https://api.github.com/repos/list_package_vers/model_2/tags':
            raise urllib.error.HTTPError(url, 404, 'not found', None, None)
        elif url == 'https://api.github.com/repos/list_package_vers/model_3/tags':
            raise urllib.error.HTTPError(url, 500, 'Server Error', None, None)
        elif 'https://api.github.com/repos/package_download/fake/tarball/1.0' in url:
            return MockResponse('fake data ' * 2, 200)
        elif url == 'https://api.github.com/repos/package_download/bad_pack/tarball/0.2':
            raise urllib.error.HTTPError(url, 404, 'not found', None, None)
        elif url == 'https://raw.githubusercontent.com/get_metadata/foo/0.0/metadata.yml':
            data = yaml.dump({"maintainer": {"name": "moi"}})
            return MockResponse(data, 200)
        else:
            raise RuntimeError("test non prevu", url)


    def test_init(self):
        rem_exists = model_package.RemoteModelIndex.remote_exists
        model_package.RemoteModelIndex.remote_exists = lambda x: True
        try:
            remote = model_package.RemoteModelIndex()
            remote.cache = self.tmpdir
        finally:
            model_package.RemoteModelIndex.remote_exists = rem_exists
        self.assertEqual(remote.org_name, 'macsy-models')
        self.assertEqual(remote.base_url, 'https://api.github.com')
        self.assertEqual(remote.cache, self.tmpdir)

        model_package.RemoteModelIndex.remote_exists = lambda x: True
        try:
            remote = model_package.RemoteModelIndex(org='foo')
            remote.cache = self.tmpdir
        finally:
            model_package.RemoteModelIndex.remote_exists = rem_exists
        self.assertEqual(remote.org_name, 'foo')

        model_package.RemoteModelIndex.remote_exists = lambda x: False
        try:
            with self.assertRaises(ValueError) as ctx:
                model_package.RemoteModelIndex(org='foo')
        finally:
            model_package.RemoteModelIndex.remote_exists = rem_exists
        self.assertEqual(str(ctx.exception), "the 'foo' organization does not exist.")


    def test_repos_url(self):
        rem_exists = model_package.RemoteModelIndex.remote_exists
        model_package.RemoteModelIndex.remote_exists = lambda x: True
        try:
            org = "package_repos_url"
            remote = model_package.RemoteModelIndex(org=org)
            self.assertEqual(remote.repos_url, f"https://github.com/{org}")
        finally:
            rem_exists

    @patch('urllib.request.urlopen', side_effect=mocked_requests_get)
    def test_url_json(self, mock_urlopen):
        rem_exists = model_package.RemoteModelIndex.remote_exists
        model_package.RemoteModelIndex.remote_exists = lambda x: True
        remote = model_package.RemoteModelIndex(org="nimportnaoik")
        remote.cache = self.tmpdir
        try:
            j = remote._url_json("https://test_url_json/")
            self.assertDictEqual(j, {'fake': ['json', 'response']})
        finally:
            model_package.RemoteModelIndex.remote_exists = rem_exists


    @patch('urllib.request.urlopen', side_effect=mocked_requests_get)
    def test_url_json_reach_limit(self, mock_urlopen):
        rem_exists = model_package.RemoteModelIndex.remote_exists
        model_package.RemoteModelIndex.remote_exists = lambda x: True
        remote = model_package.RemoteModelIndex(org="nimportnaoik")
        remote.cache = self.tmpdir
        try:
            with self.assertRaises(MacsyDataLimitError) as ctx:
                remote._url_json("https://test_url_json/limit")
            self.assertEqual(str(ctx.exception),
                             """You reach the maximum number of request per hour to github.
Please wait before to try again.""")
        finally:
            model_package.RemoteModelIndex.remote_exists = rem_exists


    @patch('urllib.request.urlopen', side_effect=mocked_requests_get)
    def test_remote_exists(self, mock_urlopen):
        remote = model_package.RemoteModelIndex(org="remote_exists_true")
        remote.cache = self.tmpdir
        exists = remote.remote_exists()
        self.assertTrue(exists)

        remote.org_name = "remote_exists_false"
        exists = remote.remote_exists()
        self.assertFalse(exists)

        remote.org_name = "remote_exists_server_error"
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            remote.remote_exists()
        self.assertEqual(str(ctx.exception),
                         "HTTP Error 500: Server Error")

        remote.org_name = "remote_exists_unexpected_error"
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            remote.remote_exists()
        self.assertEqual(str(ctx.exception),
                         "HTTP Error 204: No Content")

    @patch('urllib.request.urlopen', side_effect=mocked_requests_get)
    def test_get_metadata(self, mock_urlopen):
        rem_exists = model_package.RemoteModelIndex.remote_exists
        list_package_vers = model_package.RemoteModelIndex.list_package_vers
        try:
            vers = '0.0'
            pack_name = 'foo'
            model_package.RemoteModelIndex.remote_exists = lambda x: True
            model_package.RemoteModelIndex.list_package_vers = lambda x, pack_name: [vers]
            remote = model_package.RemoteModelIndex(org="get_metadata")
            remote.cache = self.tmpdir
            metadata = remote.get_metadata(pack_name)
            self.assertDictEqual(metadata, {"maintainer": {"name": "moi"}})
        finally:
            model_package.RemoteModelIndex.remote_exists = rem_exists
            model_package.RemoteModelIndex.list_package_vers = list_package_vers

        #################################################
        # The remote package is not versioned (tagged)  #
        #################################################
        try:
            model_package.RemoteModelIndex.remote_exists = lambda x: True
            model_package.RemoteModelIndex.list_package_vers = lambda x, pack_name: []
            remote = model_package.RemoteModelIndex(org="get_metadata")
            with self.assertRaises(MacsydataError) as ctx:
                remote.get_metadata(pack_name)
            self.assertEqual(str(ctx.exception),
                             "No official version available for model 'foo'")
        finally:
            model_package.RemoteModelIndex.remote_exists = rem_exists
            model_package.RemoteModelIndex.list_package_vers = list_package_vers

        #####################################
        # The pack version is not available #
        #####################################
        try:
            model_package.RemoteModelIndex.remote_exists = lambda x: True
            model_package.RemoteModelIndex.list_package_vers = lambda x, pack_name: ["12"]
            remote = model_package.RemoteModelIndex(org="get_metadata")
            with self.assertRaises(RuntimeError) as ctx:
                remote.get_metadata(pack_name, vers="1.1")
            self.assertEqual(str(ctx.exception),
                             "The version '1.1' does not exists for model foo.")
        finally:
            model_package.RemoteModelIndex.remote_exists = rem_exists
            model_package.RemoteModelIndex.list_package_vers = list_package_vers


    @patch('urllib.request.urlopen', side_effect=mocked_requests_get)
    def test_list_packages(self, mock_urlopen):
        rem_exists = model_package.RemoteModelIndex.remote_exists
        try:
            model_package.RemoteModelIndex.remote_exists = lambda x: True
            remote = model_package.RemoteModelIndex(org="list_packages")
            remote.cache = self.tmpdir
            self.assertListEqual(remote.list_packages(), ['model_1', 'model_2'])
        finally:
            model_package.RemoteModelIndex.remote_exists = rem_exists


    @patch('urllib.request.urlopen', side_effect=mocked_requests_get)
    def test_list_package_vers(self, mock_urlopen):
        rem_exists = model_package.RemoteModelIndex.remote_exists
        try:
            model_package.RemoteModelIndex.remote_exists = lambda x: True
            remote = model_package.RemoteModelIndex(org="list_package_vers")
            remote.cache = self.tmpdir
        finally:
            model_package.RemoteModelIndex.remote_exists = rem_exists

        self.assertListEqual(remote.list_package_vers('model_1'), ['v_1', 'v_2'])

        with self.assertRaises(ValueError) as ctx:
            _ = remote.list_package_vers('model_2')
        self.assertEqual(str(ctx.exception), "package 'model_2' does not exists on repos 'list_package_vers'")

        with self.assertRaises(urllib.error.HTTPError) as ctx:
            _ = remote.list_package_vers('model_3')
        self.assertEqual(str(ctx.exception), "HTTP Error 500: Server Error")


    @patch('urllib.request.urlopen', side_effect=mocked_requests_get)
    def test_download(self, mock_urlopen):
        rem_exists = model_package.RemoteModelIndex.remote_exists
        try:
            model_package.RemoteModelIndex.remote_exists = lambda x: True
            remote = model_package.RemoteModelIndex(org="package_download")
            remote.cache = self.tmpdir
            pack_name = "fake"
            pack_vers = "1.0"
            # ensure that remote.cache does not exists
            if os.path.exists(remote.cache):
                if os.path.isdir(remote.cache):
                    shutil.rmtree(remote.cache)
                elif os.path.isfile(remote.cache) or os.path.islink(remote.cache):
                    os.unlink(remote.cache)

            arch_path = remote.download(pack_name, pack_vers)
            self.assertEqual(os.path.join(remote.cache, remote.org_name, f"{pack_name}-{pack_vers}.tar.gz"),
                             arch_path)
            self.assertFileEqual(arch_path, io.StringIO('fake data ' * 2))

            # download again with existing remote.cache and replace old archive
            os.unlink(arch_path)
            arch_path = remote.download(pack_name, pack_vers)
            self.assertFileEqual(arch_path, io.StringIO('fake data ' * 2))

            # download again with existing remote.cache and replace old archive
            os.unlink(arch_path)
            dest = os.path.join(self.tmpdir, 'dest')
            os.makedirs(dest)
            arch_path = remote.download(pack_name, pack_vers, dest=dest)
            self.assertEqual(os.path.join(dest, f'{pack_name}-{pack_vers}.tar.gz'), arch_path)

            # remote cache exist and is a file
            shutil.rmtree(remote.cache)
            open(remote.cache, 'w').close()
            try:
                with self.assertRaises(NotADirectoryError) as ctx:
                    remote.download(pack_name, pack_vers)
                self.assertEqual(str(ctx.exception),
                                 f"The tmp cache '{remote.cache}' already exists")
            finally:
                os.unlink(remote.cache)

            with self.assertRaises(ValueError) as ctx:
                _ = remote.download("bad_pack", "0.2")
            self.assertEqual(str(ctx.exception),
                             "package 'bad_pack-0.2' does not exists on repos 'package_download'")
        finally:
            model_package.RemoteModelIndex.remote_exists = rem_exists


    def test_unarchive(self):

        def create_pack(dir_, repo, name, vers, key):
            pack_name = f"{name}-{vers}"
            tar_path = os.path.join(dir_, f"{pack_name}.tar.gz")
            with tarfile.open(tar_path, "w:gz") as tar:
                tmp_pack = os.path.join(dir_, f"{repo}-{name}-{key}")
                os.mkdir(tmp_pack)
                for i in range(3):
                    name = f"file_{i}"
                    tmp_file = os.path.join(tmp_pack, name)
                    with open(tmp_file, 'w') as f:
                        f.write(f"Content of file {i}\n")
                tar.add(tmp_pack, arcname=os.path.basename(tmp_pack))
            shutil.rmtree(tmp_pack)
            return tar_path

        pack_name = 'model-toto'
        pack_vers = '2.0'

        rem_exists = model_package.RemoteModelIndex.remote_exists
        model_package.RemoteModelIndex.remote_exists = lambda x: True
        try:
            remote = model_package.RemoteModelIndex(org="package_unarchive")
            arch = create_pack(self.tmpdir, remote.org_name, pack_name, pack_vers, 'e020300')
            remote.cache = self.tmpdir

            model_path = remote.unarchive_package(arch)
            unpacked_path = os.path.join(self.tmpdir, remote.org_name, pack_name, pack_vers, pack_name)
            self.assertEqual(model_path, unpacked_path)
            self.assertTrue(os.path.exists(unpacked_path))
            self.assertTrue(os.path.isdir(unpacked_path))
            self.assertListEqual(sorted(glob.glob(f"{unpacked_path}/*")),
                                 sorted([os.path.join(unpacked_path, f"file_{i}") for i in range(3)])
                                 )
            # test package is remove before to unarchive a new one
            open(os.path.join(unpacked_path, "file_must_be_removed"), 'w').close()
            model_path = remote.unarchive_package(arch)
            self.assertListEqual(sorted(glob.glob(f"{unpacked_path}/*")),
                                 sorted([os.path.join(unpacked_path, f"file_{i}") for i in range(3)])
                                 )
        finally:
            model_package.RemoteModelIndex.remote_exists = rem_exists


class TestModelPackage(MacsyTest):

    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory(prefix='test_msf_package_')
        self.tmpdir = self._tmp_dir.name

        macsylib.init_logger()
        macsylib.logger_set_level(level=30)
        logger = colorlog.getLogger('macsylib.package')
        model_package._log = logger
        logger = colorlog.getLogger('macsylib.model_conf_parser')
        model_conf_parser._log = logger
        maintainer = Maintainer("auth_name", "auth_name@mondomain.fr")
        self.metadata = model_package.Metadata(maintainer,
                                         "this is a short description of the repos")
        self.metadata.vers = "0.0b2"
        self.metadata.cite = ["bla bla",
                                  "link to publication",
                                  """ligne 1
ligne 2
ligne 3 et bbbbb
"""]
        self.metadata.doc = "http://link/to/the/documentation"
        self.metadata.license = "CC BY-NC-SA 4.0 (https://creativecommons.org/licenses/by-nc-sa/4.0/)"
        self.metadata.copyright_date = "2019"
        self.metadata.copyright_holder = "Institut Pasteur, CNRS"


    def tearDown(self) -> None:
        self._tmp_dir.cleanup()


    def create_fake_package(self, model,
                            definitions=True,
                            bad_definitions=False,
                            profiles=True,
                            skip_hmm=None,
                            metadata='good_metadata.yml',
                            readme=True,
                            license=True,
                            conf=True,
                            vers=True,
                            bad_conf=False):
        pack_path = os.path.join(self.tmpdir, model)
        os.mkdir(pack_path)
        if definitions:
            def_dir = os.path.join(pack_path, 'definitions')
            os.mkdir(def_dir)
            with open(os.path.join(def_dir, "model_1.xml"), 'w') as f:
                f.write("""<model inter_gene_max_space="20" min_mandatory_genes_required="1" min_genes_required="2" vers="2.0">
    <gene name="flgB" presence="mandatory"/>
    <gene name="flgC" presence="mandatory" inter_gene_max_space="2"/>
</model>""")
            with open(os.path.join(def_dir, "model_2.xml"), 'w') as f:
                f.write("""<model inter_gene_max_space="20" min_mandatory_genes_required="1" min_genes_required="2" vers="2.0">
    <gene name="fliE" presence="mandatory" multi_system="True"/>
    <gene name="tadZ" presence="accessory" loner="True"/>
    <gene name="sctC" presence="forbidden"/>
</model>""")
        if bad_definitions:
            with open(os.path.join(def_dir, "model_3.xml"), 'w') as f:
                f.write("""<model inter_gene_max_space="20" min_mandatory_genes_required="2" min_genes_required="1" vers="2.0">
    <gene name="flgB" presence="mandatory"/>
    <gene name="flgC" presence="mandatory" inter_gene_max_space="2"/>
</model>""")
        if profiles:
            profile_dir = os.path.join(pack_path, 'profiles')
            os.mkdir(profile_dir)
            for name in ('flgB', 'flgC', 'fliE', 'tadZ', 'sctC'):
                if skip_hmm and name in skip_hmm:
                    continue
                shutil.copyfile(self.find_data('models', 'foo', 'profiles', f'{name}.hmm'),
                                os.path.join(profile_dir, f"{name}.hmm")
                                )
        if metadata:
            meta_path = self.find_data('pack_metadata', metadata)
            meta_dest = os.path.join(pack_path, model_package.Metadata.name)
            with open(meta_path) as meta_file:
                meta = yaml.safe_load(meta_file)
            if not vers:
                meta['vers'] = None
            with open(meta_dest, 'w') as meta_file:
                yaml.dump(meta, meta_file,allow_unicode=True, indent=2)
        if readme:
            with open(os.path.join(pack_path, "README"), 'w') as f:
                f.write("# This a README\n")
        if license:
            with open(os.path.join(pack_path, "LICENSE"), 'w') as f:
                f.write("# This the License\n")
        if conf:
            with open(os.path.join(pack_path, "model_conf.xml"), 'w') as f:
                conf = """<model_config>
    <weights>
        <itself>11</itself>
        <exchangeable>12</exchangeable>
        <mandatory>13</mandatory>
        <accessory>14</accessory>
        <neutral>0</neutral>
        <out_of_cluster>10</out_of_cluster>
    </weights>
    <filtering>
        <e_value_search>0.12</e_value_search>
        <i_evalue_sel>0.012</i_evalue_sel>
        <coverage_profile>0.55</coverage_profile>
        <cut_ga>False</cut_ga>
    </filtering>
</model_config>
"""
                f.write(conf)
        elif bad_conf:
            with open(os.path.join(pack_path, "model_conf.xml"), 'w') as f:
                conf = """<model_config>
    <weights>
        <itself>FOO</itself>
        <exchangeable>BAR</exchangeable>
    </weights>
</model_config>
"""
                f.write(conf)

        return pack_path


    def test_init(self):
        fake_pack_path = self.create_fake_package('fake_model')
        pack = model_package.ModelPackage(fake_pack_path)
        self.assertEqual(pack.path, fake_pack_path)
        self.assertEqual(pack.readme, os.path.join(fake_pack_path, 'README'))
        self.assertEqual(pack.name, 'fake_model')
        self.assertEqual(pack.metadata_path, os.path.join(fake_pack_path, 'metadata.yml'))


    def test_metadata(self):
        fake_pack_path = self.create_fake_package('fake_model')
        pack = model_package.ModelPackage(fake_pack_path)
        self.assertEqual(pack.metadata.maintainer, self.metadata.maintainer)
        self.assertEqual(pack.metadata.short_desc, self.metadata.short_desc)
        self.assertEqual(pack.metadata.license, self.metadata.license)
        self.assertEqual(pack.metadata.copyright, self.metadata.copyright)
        self.assertEqual(pack.metadata.doc, self.metadata.doc)
        self.assertEqual(pack.metadata.cite, self.metadata.cite)

    def test_find_readme(self):
        fake_pack_path = self.create_fake_package('fake_model')
        pack = model_package.ModelPackage(fake_pack_path)
        for ext in ('', '.rst', '.md'):
            readme_path = os.path.join(pack.path, 'README' + ext)
            os.rename(pack.readme, readme_path)
            pack.readme = readme_path
            self.assertEqual(pack._find_readme(), readme_path)
        readme_path = os.path.join(pack.path, 'README.foo')
        os.rename(pack.readme, readme_path)
        self.assertIsNone(pack._find_readme())

    def test_check_model_conf(self):
        fake_pack_path = self.create_fake_package('fake_model')
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_model_conf()
        self.assertListEqual(errors, [])
        self.assertListEqual(warnings, [])

    def test_check_model_conf_no_conf(self):
        fake_pack_path = self.create_fake_package('fake_model', conf=False)
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_model_conf()
        self.assertListEqual(errors, [])
        self.assertListEqual(warnings, [])

    def test_check_model_conf_bad_conf(self):
        fake_pack_path = self.create_fake_package('fake_model', conf=False, bad_conf=True)
        pack = model_package.ModelPackage(fake_pack_path)
        with self.catch_log(log_name='macsylib'):
            errors, warnings = pack._check_model_conf()
        self.maxDiff =None
        self.assertListEqual(errors, [f"The model configuration file '{fake_pack_path}/model_conf.xml' "
                                      f"cannot be parsed: could not convert string to float: 'FOO'"])
        self.assertListEqual(warnings, [])

    def test_check_structure(self):
        fake_pack_path = self.create_fake_package('fake_model')
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_structure()
        self.assertListEqual(errors, [])
        self.assertListEqual(warnings, [])


    def test_check_structure_bad_path(self):
        foobar = os.path.join(self.tmpdir, "foobar")
        pack = model_package.ModelPackage(foobar)
        errors, warnings = pack._check_structure()
        self.assertListEqual(errors, ["The model package 'foobar' does not exists."])
        self.assertListEqual(warnings, [])

        open(foobar, 'w').close()
        errors, warnings = pack._check_structure()
        self.assertListEqual(errors, ["The model package 'foobar' is not a directory "])
        self.assertListEqual(warnings, [])


    def test_check_structure_no_def(self):
        fake_pack_path = self.create_fake_package('fake_model', definitions=False)
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_structure()

        self.assertListEqual(errors, ["The model package 'fake_model' have no 'definitions' directory."])
        self.assertListEqual(warnings, [])

        open(os.path.join(pack.path, 'definitions'), 'w').close()
        errors, warnings = pack._check_structure()
        self.assertListEqual(errors, [f"'{os.path.join(self.tmpdir, 'fake_model', 'definitions')}' is not a directory."])
        self.assertListEqual(warnings, [])


    def test_check_structure_no_profiles(self):
        fake_pack_path = self.create_fake_package('fake_model', profiles=False)
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_structure()

        self.assertListEqual(errors, ["The model package 'fake_model' have no 'profiles' directory."])
        self.assertListEqual(warnings, [])

        open(os.path.join(pack.path, 'profiles'), 'w').close()
        errors, warnings = pack._check_structure()
        self.assertListEqual(errors, [f"'{os.path.join(self.tmpdir, 'fake_model', 'profiles')}' is not a directory."])
        self.assertListEqual(warnings, [])


    def test_check_structure_no_metadata(self):
        fake_pack_path = self.create_fake_package('fake_model', metadata='')
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_structure()

        self.assertListEqual(errors, ["The model package 'fake_model' have no 'metadata.yml'."])
        self.assertListEqual(warnings, [])


    def test_check_structure_no_readme(self):
        fake_pack_path = self.create_fake_package('fake_model', readme=False)
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_structure()

        self.assertEqual(errors, [])
        self.assertEqual(warnings, ["The model package 'fake_model' have not any README file."])


    def test_check_structure_no_license(self):
        fake_pack_path = self.create_fake_package('fake_model', license=False)
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_structure()

        self.assertEqual(errors, [])
        self.assertEqual(warnings, ["The model package 'fake_model' have not any LICENSE file. "
                                    "May be you have not right to use it."])


    def test_check_model_consistency(self):
        fake_pack_path = self.create_fake_package('fake_model')
        pack = model_package.ModelPackage(fake_pack_path)
        with self.catch_log(log_name='macsylib'):
            errors, warnings = pack._check_model_consistency()

        self.assertEqual(warnings, [])
        self.assertEqual(errors, [])


    def test_check_model_consistency_extra_profile(self):
        fake_pack_path = self.create_fake_package('fake_model')
        pack = model_package.ModelPackage(fake_pack_path)
        open(os.path.join(fake_pack_path, 'profiles', 'extra_profile.hmm'), 'w').close()
        with self.catch_log(log_name='macsylib'):
            errors, warnings = pack._check_model_consistency()

        self.assertEqual(warnings, ['The extra_profile profiles are not referenced in any definitions.'])
        self.assertEqual(errors, [])


    def test_check_model_consistency_lack_one_profile(self):
        fake_pack_path = self.create_fake_package('fake_model', skip_hmm=['flgB', 'fliE'])
        pack = model_package.ModelPackage(fake_pack_path)
        with self.catch_log(log_name='macsylib'):
            errors, warnings = pack._check_model_consistency()

        self.assertEqual(warnings, [])
        self.assertSetEqual(set(errors),
                            set(["'fake_model/flgB': No such profile",
                                 "'fake_model/fliE': No such profile"])
                            )


    def test_check_model_consistency_bad_definitions(self):
        fake_pack_path = self.create_fake_package('fake_model', bad_definitions=True)
        pack = model_package.ModelPackage(fake_pack_path)
        with self.catch_log(log_name='macsylib'):
            errors, warnings = pack._check_model_consistency()
        self.assertEqual(warnings, [])
        self.assertEqual(errors, ["fake_model/model_3: min_genes_required '1' must be greater or equal than "
                                  "min_mandatory_genes_required '2'"])


    def test_check_no_readme_n_no_license(self):
        fake_pack_path = self.create_fake_package('fake_model', readme=False, license=False, vers=False)
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_structure()

        self.assertEqual(errors, [])
        self.assertEqual(warnings, ["The model package 'fake_model' have not any LICENSE file. "
                                    "May be you have not right to use it.",
                                    "The model package 'fake_model' have not any README file."])

    def test_check_metadata(self):
        fake_pack_path = self.create_fake_package('fake_model', vers=False)
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_metadata()
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_check_metadata_no_maintainer(self):
        fake_pack_path = self.create_fake_package('fake_model', metadata='metadata_no_maintainer.yml', vers=False)
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_metadata()
        self.assertListEqual(errors, [f"- The metadata file '{fake_pack_path}/metadata.yml' is not valid: "
                                      f"the element 'maintainer' is required."])
        self.assertListEqual(warnings, [])

    def test_check_metadata_no_name(self):
        fake_pack_path = self.create_fake_package('fake_model', metadata='metadata_no_name.yml', vers=False)
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_metadata()
        self.assertListEqual(errors, [f"- The metadata file '{fake_pack_path}/metadata.yml' is not valid: "
                                                "the element 'maintainer' must have fields 'name' and 'email'."])
        self.assertListEqual(warnings, [])

    def test_check_metadata_no_email(self):
        fake_pack_path = self.create_fake_package('fake_model', metadata='metadata_no_email.yml', vers=False)
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_metadata()
        self.assertListEqual(errors, [f"- The metadata file '{fake_pack_path}/metadata.yml' is not valid: "
                                                "the element 'maintainer' must have fields 'name' and 'email'."])
        self.assertListEqual(warnings, [])

    def test_check_metadata_no_desc(self):
        fake_pack_path = self.create_fake_package('fake_model', metadata='metadata_no_desc.yml', vers=False)
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_metadata()
        self.assertEqual(errors, [f"- The metadata file '{fake_pack_path}/metadata.yml' is not valid: "
                                  f"the element 'short_desc' is required."])
        self.assertEqual(warnings, [])


    def test_check_metadata_no_vers(self):
        fake_pack_path = self.create_fake_package('fake_model', metadata='metadata_no_vers.yml')
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_metadata()
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_check_metadata_with_vers(self):
        fake_pack_path = self.create_fake_package('fake_model')
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_metadata()
        self.assertEqual(errors, [])
        self.assertEqual(warnings, ["The field 'vers' is not required anymore."
                                    "\n  It will be ignored and set by macsydata during installation phase according"
                                    " to the git tag."])

    def test_check_metadata_no_cite(self):
        fake_pack_path = self.create_fake_package('fake_model', metadata='metadata_no_cite.yml', vers=False)
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_metadata()
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [f"It's better if the field 'cite' is setup in '{fake_pack_path}/metadata.yml' file."])


    def test_check_metadata_no_doc(self):
        fake_pack_path = self.create_fake_package('fake_model', metadata='metadata_no_doc.yml', vers=False)
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_metadata()
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [f"It's better if the field 'doc' is setup in '{fake_pack_path}/metadata.yml' file."])

    def test_check_metadata_no_license(self):
        fake_pack_path = self.create_fake_package('fake_model', metadata='metadata_no_license.yml', vers=False)
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_metadata()
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [f"It's better if the field 'license' is setup in '{fake_pack_path}/metadata.yml' file."])

    def test_check_metadata_no_copyright(self):
        fake_pack_path = self.create_fake_package('fake_model', metadata='metadata_no_copyright.yml', vers=False)
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_metadata()
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [f"It's better if the field 'copyright' is setup in '{fake_pack_path}/metadata.yml' file."])


    def test_check(self):
        fake_pack_path = self.create_fake_package('fake_model', metadata='good_metadata.yml', vers=False)
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack.check()
        self.assertListEqual(warnings, [])
        self.assertListEqual(errors, [])

    def test_check_bad_metadata(self):
        fake_pack_path = self.create_fake_package('fake_model', metadata='bad_metadata.yml')
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack.check()

        self.assertListEqual(warnings, [])
        self.assertListEqual(errors, [f"- The metadata file '{fake_pack_path}/metadata.yml' is not valid: "
                                      f"the element 'short_desc' is required.",
                                      f"- The metadata file '{fake_pack_path}/metadata.yml' is not valid: "
                                      f"the element 'maintainer' is required."])

    def test_check_poor_quality_metadata(self):
        fake_pack_path = self.create_fake_package('fake_model', metadata='metadata_poor_quality.yml')
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack.check()
        self.assertListEqual(errors, [])
        self.assertListEqual(warnings,
                             [f"It's better if the field 'cite' is setup in '{fake_pack_path}/metadata.yml' file.",
                              f"It's better if the field 'doc' is setup in '{fake_pack_path}/metadata.yml' file.",
                              f"It's better if the field 'license' is setup in '{fake_pack_path}/metadata.yml' file.",
                              f"It's better if the field 'copyright' is setup in '{fake_pack_path}/metadata.yml' file."])

    def test_check_several_profile_per_file(self):
        fake_pack_path = self.create_fake_package('fake_model', profiles=False)
        profiles_dir = os.path.join(fake_pack_path, 'profiles')
        os.mkdir(profiles_dir)
        shutil.copyfile(self.find_data('hmm', 'one_profile.hmm'), os.path.join(profiles_dir, 'one_profile.hmm'))
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_profiles()
        self.assertListEqual(errors, [])
        self.assertListEqual(warnings, [])

        shutil.copyfile(self.find_data('hmm', 'several_profiles.hmm'), os.path.join(profiles_dir, 'several_profiles.hmm'))
        errors, warnings = pack._check_profiles()
        self.assertListEqual(errors, [
            '\nThere are several profiles RM_Type_II__Type_II_REases___Type_II_REase01\n'
            ' - RM_Type_II__Type_II_REases___Type_II_REase02\n'
            f"in {os.path.join(self.tmpdir, 'fake_model', 'profiles', 'several_profiles')}.hmm:\n"
            ' Split this file to have one profile per file.'
        ])
        self.assertListEqual(warnings, [])


    def test_check_empty_profile(self):
        fake_pack_path = self.create_fake_package('fake_model', profiles=False)
        profiles_dir = os.path.join(fake_pack_path, 'profiles')
        os.mkdir(profiles_dir)
        fake_profile = os.path.join(profiles_dir, 'flgB.hmm')
        open(fake_profile, 'w').close()
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_profiles()
        self.assertListEqual(errors, [f"Profile {fake_profile} seems empty: Check this file."])
        self.assertListEqual(warnings, [])


    def test_check_old_profile(self):
        fake_pack_path = self.create_fake_package('fake_model', profiles=False)
        profiles_dir = os.path.join(fake_pack_path, 'profiles')
        os.mkdir(profiles_dir)
        old_profile = os.path.join(profiles_dir, 'old_profile.hmm')
        shutil.copyfile(self.find_data('hmm', 'old_profile.hmm'), old_profile)
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_profiles()
        self.assertListEqual(errors, [f"The file {old_profile} does not seems to be HMMER 3 profile: "
                                      f"check it or remove it."])
        self.assertListEqual(warnings, [])


    def test_check_dir_in_profile(self):
        fake_pack_path = self.create_fake_package('fake_model')
        profiles_dir = os.path.join(fake_pack_path, 'profiles')
        dir_in_profiles = os.path.join(profiles_dir, 'nimportnaoik')
        os.makedirs(dir_in_profiles)
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_profiles()
        self.assertListEqual(errors, [])
        self.assertListEqual(warnings,
                             [f"found directory '{dir_in_profiles}' in profiles dir: subdirectories are not supported in profiles. "
                              f"This directory will be IGNORED."])

    def test_profile_with_bad_ext(self):
        fake_pack_path = self.create_fake_package('fake_model')
        profiles_dir = os.path.join(fake_pack_path, 'profiles')
        bad_profile = os.path.join(profiles_dir, 'flgB.bad_ext')
        open(bad_profile, 'w').close()
        pack = model_package.ModelPackage(fake_pack_path)
        errors, warnings = pack._check_profiles()
        self.assertListEqual(errors, [])
        self.assertListEqual(warnings,
                             [f"The file '{bad_profile}' does not ends with '.hmm'. Skip it."])

    def test_help(self):
        fake_pack_path = self.create_fake_package('fake_model', license=False)
        pack = model_package.ModelPackage(fake_pack_path)

        receive_help = pack.help()
        self.assertEqual(receive_help, "# This a README\n")

        os.unlink(os.path.join(fake_pack_path, 'README'))
        pack = model_package.ModelPackage(fake_pack_path)
        receive_help = pack.help()
        self.assertEqual(receive_help, "No help available for package 'fake_model'.")


    def test_info(self):
        fake_pack_path = self.create_fake_package('fake_model', license=False)
        pack = model_package.ModelPackage(fake_pack_path)

        info = pack.info()

        expected_info = """
fake_model (0.0b2)

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
copyright: 2019, Institut Pasteur, CNRS
"""
        self.assertEqual(info, expected_info)

    def test_info_no_citation(self):
        fake_pack_path = self.create_fake_package('fake_model', metadata='metadata_no_cite.yml', license=False)
        pack = model_package.ModelPackage(fake_pack_path)

        info = pack.info()

        expected_info = """
fake_model (0.0b2)

maintainer: auth_name <auth_name@mondomain.fr>

this is a short description of the repos

how to cite:
\t- No citation available

documentation
\thttp://link/to/the/documentation

This data are released under CC BY-NC-SA 4.0 (https://creativecommons.org/licenses/by-nc-sa/4.0/)
copyright: 2019, Institut Pasteur, CNRS
"""
        self.assertEqual(info, expected_info)

    def test_info_no_doc(self):
        fake_pack_path = self.create_fake_package('fake_model', metadata='metadata_no_doc.yml', license=False)
        pack = model_package.ModelPackage(fake_pack_path)

        info = pack.info()
        expected_info = """
fake_model (0.0b2)

maintainer: auth_name <auth_name@mondomain.fr>

this is a short description of the repos

how to cite:
\t- bla bla
\t- link to publication
\t- ligne 1
\t  ligne 2
\t  ligne 3 et bbbbb

documentation
\tNo documentation available

This data are released under CC BY-NC-SA 4.0 (https://creativecommons.org/licenses/by-nc-sa/4.0/)
copyright: 2019, Institut Pasteur, CNRS
"""
        self.assertEqual(info, expected_info)


    def test_info_no_license(self):
        fake_pack_path = self.create_fake_package('fake_model', metadata='metadata_no_license.yml', license=False)
        pack = model_package.ModelPackage(fake_pack_path)

        info = pack.info()
        expected_info = """
fake_model (0.0b2)

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

This data are released under No license available
copyright: 2019, Institut Pasteur, CNRS
"""
        self.assertEqual(info, expected_info)
