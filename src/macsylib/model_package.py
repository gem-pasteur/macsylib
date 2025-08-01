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

import os
import abc
import ssl
import tempfile
import urllib.request
import urllib.parse
import json
import shutil
import tarfile

import certifi
import yaml
import colorlog

from .config import NoneConfig
from .registries import ModelLocation, ModelRegistry
from .profile import ProfileFactory
from .definition_parser import DefinitionParser
from .model import ModelBank
from .gene import GeneBank
from .model_conf_parser import ModelConfParser
from .metadata import Metadata
from .error import MacsydataError, MacsyDataLimitError, MacsylibError

"""
This module allow to manage Packages of MacSyLib models
"""


_log = colorlog.getLogger(__name__)


class AbstractModelIndex(metaclass=abc.ABCMeta):
    """
    This the base class for ModelIndex.
    This class cannot be implemented, it must be subclassed
    """

    def __init__(self, cache: str | None = None) -> None:
        """

        """
        self.org_name: str | None = None
        if cache:
            self.cache: str = cache
        else:
            self.cache = os.path.join(tempfile.gettempdir(), 'tmp-macsy-cache')


    @property
    @abc.abstractmethod
    def repos_url(self) -> str:
        raise NotImplementedError()


    def unarchive_package(self, path: str) -> str:
        """
        Unarchive and uncompress a package under
        `<remote cache>/<organization name>/<package name>/<vers>/<package name>`

        :param str path:
        :return: The path to the package
        """
        name, vers = parse_arch_path(path)
        dest_dir = os.path.join(self.cache, self.org_name, name, vers)
        dest_unarchive_path = os.path.join(dest_dir, name)
        if os.path.exists(dest_unarchive_path):
            _log.info(f"Removing old models {dest_unarchive_path}")
            shutil.rmtree(dest_unarchive_path)

        with tarfile.open(path, 'r:gz') as tar:
            tar_dir_name = tar.next().name

            def is_within_directory(directory: str, target: str) -> bool:
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
                prefix = os.path.commonprefix([abs_directory, abs_target])
                return prefix == abs_directory

            def safe_extract(tar: tarfile.TarFile, path: str = ".", members=None, *, numeric_owner=False):
                for member in tar.getmembers():
                    member_path = os.path.join(path, member.name)
                    if not is_within_directory(path, member_path):
                        raise Exception("Attempted Path Traversal in Tar File")
                tar.extractall(path, members, numeric_owner=numeric_owner, filter='data')

            safe_extract(tar, path=dest_dir)

        # github prefix the archive root directory with the organization name
        # add suffix with a random suffix
        # for instance for TXSS models
        # the unarchive will named macsy-models-TXSS-64889bd
        unarchive_pack = os.path.join(dest_dir, tar_dir_name)
        if unarchive_pack != dest_unarchive_path:
            os.rename(unarchive_pack, dest_unarchive_path)
        return dest_unarchive_path


class LocalModelIndex(AbstractModelIndex):
    """
    It allow to manage installation from a local package (tarball)
    """

    def __init__(self, cache: str | None = None) -> None:
        """

        """
        super().__init__(cache=cache)
        self.org_name: str = 'local'

    @property
    def repos_url(self) -> str:
        return "local"


class RemoteModelIndex(AbstractModelIndex):
    """
    This class allow to interact with ModelIndex on github
    """

    def __init__(self, org: str = "macsy-models", cache: str | None = None) -> None:
        """

        :param org: The name of the organization on github where are stored the models
        """
        super().__init__(cache=cache)
        self.org_name = urllib.parse.quote(org)
        self.base_url: str = "https://api.github.com"
        self._context = ssl.create_default_context(cafile=certifi.where())
        if not self.remote_exists():
            raise ValueError(f"the '{self.org_name}' organization does not exist.")


    def _url_json(self, url: str) -> dict:
        """
        Get the url, deserialize the data as json

        :param str url: the url to download
        :return: the json corresponding to the response url
        """
        try:
            req = urllib.request.urlopen(url, context=self._context).read()
        except urllib.error.HTTPError as err:
            if err.code == 403:
                raise MacsyDataLimitError("You reach the maximum number of request per hour to github.\n"
                                          "Please wait before to try again.") from None
            else:
                raise err
        data = json.loads(req.decode('utf-8'))
        return data

    @property
    def repos_url(self) -> str:
        return f"{self.base_url.replace('api.', '', 1)}/{self.org_name}"


    def remote_exists(self) -> bool:
        """
        check if the remote exists and is an organization

        :return: True if the Remote url point to a GitHub Organization, False otherwise
        """
        try:
            url = f"{self.base_url}/orgs/{self.org_name}"
            _log.debug(f"get {url}")
            remote = self._url_json(url)
            return remote["type"] == 'Organization'
        except urllib.error.HTTPError as err:
            if 400 <= err.code < 500:
                return False
            elif err.code >= 500:
                raise err from None
            else:
                raise err from None


    def get_metadata(self, pack_name: str, vers: str = 'latest') -> dict:
        """
        Fetch the metadata_path from a remote package

        :param str pack_name: The package name
        :param str vers: The package version
        :return: the metadata_path corresponding to this package/version
        :rtype: dictionary corresponding of the yaml parsing of the metadata_path file.
        """
        versions = self.list_package_vers(pack_name)
        if not versions:
            raise MacsydataError(f"No official version available for model '{pack_name}'")
        elif vers == 'latest':
            vers = versions[0]
        else:
            if vers not in versions:
                raise RuntimeError(f"The version '{vers}' does not exists for model {pack_name}.")
        pack_name = urllib.parse.quote(pack_name)
        vers = urllib.parse.quote(vers)
        metadata_url = f"https://raw.githubusercontent.com/{self.org_name}/{pack_name}/{vers}/metadata.yml"
        try:
            with urllib.request.urlopen(metadata_url, context=self._context) as response:
                metadata = response.read().decode("utf-8")
        except urllib.error.HTTPError as err:
            if 400 < err.code < 500:
                raise MacsydataError(f"cannot fetch '{metadata_url}' check '{pack_name}'")
            elif err.code >= 500:
                raise err from None
            else:
                raise err from None
        metadata = yaml.safe_load(metadata)
        return metadata


    def list_packages(self) -> list[str]:
        """
        list all model packages available on a model repos

        :return: The list of package names.
        """
        url = f"{self.base_url}/orgs/{self.org_name}/repos"
        _log.debug(f"get {url}")
        packages = self._url_json(url)
        return [p['name'] for p in packages if p['name'] != '.github']


    def list_package_vers(self, pack_name: str) -> list[str]:
        """
        List all available versions from GitHub model repos for a given package

        :param str pack_name: the name of the package
        :return: the list of the versions
        """
        pack_name = urllib.parse.quote(pack_name)
        url = f"{self.base_url}/repos/{self.org_name}/{pack_name}/tags"
        _log.debug(f"get {url}")
        try:
            tags = self._url_json(url)
        except urllib.error.HTTPError as err:
            if 400 <= err.code < 500:
                raise ValueError(f"package '{pack_name}' does not exists on repos '{self.org_name}'") from None
            else:
                raise err from None
        return [v['name'] for v in tags]


    def download(self, pack_name: str, vers: str, dest: str | None = None) -> str:
        """
        Download a package from a GitHub repos and save it as
        <remote cache>/<organization name>/<package name>/<vers>.tar.gz

        :param str pack_name: the name of the package to download
        :param str vers: the version of the package to download
        :param str dest: The path to the directory where save the package
                         This directory must exist
                         If dest is None, the macsylib cache will be used
        :return: The package archive path.
        """
        _log.debug(f"call download with pack_name={pack_name}, vers={vers}, dest={dest}")
        safe_pack_name = urllib.parse.quote(pack_name)
        safe_vers = urllib.parse.quote(vers)
        url = f"{self.base_url}/repos/{self.org_name}/{safe_pack_name}/tarball/{safe_vers}"
        if not dest:
            package_cache = os.path.join(self.cache, self.org_name)
            if os.path.exists(self.cache) and not os.path.isdir(self.cache):
                raise NotADirectoryError(f"The tmp cache '{self.cache}' already exists")
            elif not os.path.exists(package_cache):
                os.makedirs(package_cache)
            tmp_archive_path = os.path.join(package_cache, f"{pack_name}-{vers}.tar.gz")
        else:
            tmp_archive_path = os.path.join(dest, f"{pack_name}-{vers}.tar.gz")
        try:
            with (urllib.request.urlopen(url, context=self._context) as response,
                  open(tmp_archive_path, 'wb') as out_file):
                shutil.copyfileobj(response, out_file)
        except urllib.error.HTTPError as err:
            if 400 <= err.code < 500:
                raise ValueError(f"package '{pack_name}-{vers}' does not exists on repos '{self.org_name}'") \
                    from None
            else:
                raise err from None
        return tmp_archive_path


class ModelPackage:
    """
    This class Modelize a package of Models
    a package is a directory with the name of the models family
    it must contain at least
    - a subdirectory definitions
    - a subdirectory profiles
    - a file metadata.yml
    it is also recommended to add a file
    for licensing and copyright and a README.
    for further explanation see documentation: modeler guide > package

    """

    def __init__(self, path: str) -> None:
        """

        :param str path: The of the package root directory
        """
        self.path: str = os.path.realpath(path)  # the path of the package root directory
        self.metadata_path: str = os.path.join(self.path, Metadata.name)
        self._metadata: Metadata | None = None
        self.name: str = os.path.basename(self.path)
        self.readme: str = self._find_readme()


    def _find_readme(self) -> str | None:
        """
        find the README file

        :return: The path to the README file or None if there is no file.
        """
        for ext in ('', '.md', '.rst'):
            path = os.path.join(self.path, f"README{ext}")
            if os.path.exists(path) and os.path.isfile(path):
                return path
        return None

    @property
    def metadata(self) -> dict[str: str]:
        """

        :return: The parsed metadata as a dict
        """
        if not self._metadata:
            self._metadata = self._load_metadata()
        return self._metadata


    def _load_metadata(self) -> dict[str: str]:
        """
        Open the metadata_path file and de-serialize it's content
        :return:
        """
        metadata = Metadata.load(self.metadata_path)
        return metadata


    def check(self) -> tuple[list[str], list[str]]:
        """
        Check the QA of this package
        """
        all_warnings = []
        all_errors = []
        for meth in (self._check_structure, self._check_metadata, self._check_model_consistency,
                     self._check_profiles, self._check_model_conf):
            errors, warnings = meth()
            all_errors.extend(errors)
            all_warnings.extend(warnings)
            if all_errors:
                break
        return all_errors, all_warnings


    def _check_structure(self) -> tuple[list[str], list[str]]:
        """
        Check the QA structure of the package

        :return: errors and warnings
        :rtype: tuple of 2 lists ([str error_1, ...], [str warning_1, ...])
        """
        _log.info(f"Checking '{self.name}' package structure")
        errors = []
        warnings = []
        msg = f"The model package '{self.name}' "
        if not os.path.exists(self.path):
            errors.append(msg + "does not exists.")
        elif not os.path.isdir(self.path):
            errors.append(msg + "is not a directory ")
        elif not os.path.exists(os.path.join(self.path, 'metadata.yml')):
            errors.append(msg + "have no 'metadata.yml'.")
        if not errors:
            # check several criteria and don't stop at the first problem.
            # this is why I use several If and not one set of if/elif
            if not os.path.exists(os.path.join(self.path, 'definitions')):
                errors.append(msg + "have no 'definitions' directory.")
            elif not os.path.isdir(os.path.join(self.path, 'definitions')):
                errors.append(f"'{os.path.join(self.path, 'definitions')}' is not a directory.")

            if not os.path.exists(os.path.join(self.path, 'profiles')):
                errors.append(msg + "have no 'profiles' directory.")
            elif not os.path.isdir(os.path.join(self.path, 'profiles')):
                errors.append(f"'{os.path.join(self.path, 'profiles')}' is not a directory.")

            if not os.path.exists(os.path.join(self.path, 'LICENSE')):
                warnings.append(msg + "have not any LICENSE file. "
                                "May be you have not right to use it.")
            if not self.readme:
                warnings.append(msg + "have not any README file.")
        return errors, warnings


    def _check_model_consistency(self) -> tuple[list, list]:
        """
        check if each xml seems well write, each genes have an associated profile, etc.

        :return:
        """
        _log.info(f"Checking '{self.name}' Model definitions")
        errors = []
        warnings = []
        model_loc = ModelLocation(path=self.path)
        all_def = model_loc.get_all_definitions()
        model_bank = ModelBank()
        gene_bank = GeneBank()

        config = NoneConfig()
        config.models_dir = lambda: self.path
        try:
            profile_factory = ProfileFactory(config)
            model_registry = ModelRegistry()
            model_registry.add(model_loc)
            parser = DefinitionParser(config, model_bank, gene_bank, model_registry, profile_factory)
            for one_def in all_def:
                try:
                    parser.parse([one_def])
                except MacsylibError as err:
                    errors.append(str(err))

            if not errors:
                # if some def cannot be parsed
                # I skip testing profile not in def
                # may be there are in the unparsable def
                genes_in_def = {fqn.split('/')[-1] for fqn in gene_bank.genes_fqn()}
                profiles_fqn = set(model_loc.get_profiles_names())
                profiles_not_in_def = profiles_fqn - genes_in_def
                if profiles_not_in_def:
                    warnings.append(
                        f"The {', '.join(profiles_not_in_def)} profiles are not referenced in any definitions.")
        finally:
            del config.models_dir
        _log.info("Definitions are consistent")
        # to respect same api as _check_metadata and _check_structure
        return errors, warnings

    def _check_profiles(self, profile_suffix='.hmm'):
        """
        check if there is only one profile per hmm file

        :return:
        :rtype:
        """
        _log.info(f"Checking '{self.name}' Profiles")
        errors = []
        warnings = []

        profiles_dir = os.path.join(self.path, 'profiles')
        for item in os.listdir(profiles_dir):
            path = os.path.realpath(os.path.join(profiles_dir, item))
            if os.path.isfile(path):
                _log.debug(f"Check profile {path}")
                if path.endswith(profile_suffix):
                    if os.path.getsize(path) == 0:
                        errors.append(f"Profile {path} seems empty: Check this file.")
                    else:
                        with open(path) as hmm_file:
                            profiles_name = []
                            header = next(hmm_file)
                            if header.startswith('HMMER3'):
                                for line in hmm_file:
                                    if line.startswith('NAME '):
                                        profiles_name.append(line.split()[-1])
                                if len(profiles_name) > 1:
                                    profiles_name = '\n - '.join(profiles_name)
                                    errors.append(f"\nThere are several profiles {profiles_name}\nin {path}:\n "
                                                  f"Split this file to have one profile per file.")
                            else:
                                errors.append(f"The file {path} does not seems to be HMMER 3 profile:"
                                              f" check it or remove it.")
                else:
                    warnings.append(f"The file '{path}' does not ends with '{profile_suffix}'. Skip it.")
            elif os.path.isdir(path):
                warnings.append(f"found directory '{path}' in profiles dir: subdirectories are not supported in profiles. "
                                f"This directory will be IGNORED.")

        return errors, warnings


    def _check_model_conf(self) -> tuple[list[str], list[str]]:
        """
        check if a model configuration file is present in the package (model_conf.xml)
        if the syntax of this file is good.

        :return:
        """
        _log.info(f"Checking '{self.name}' model configuration")
        errors = []
        warnings = []
        conf_file = os.path.join(self.path, 'model_conf.xml')
        if os.path.exists(conf_file):
            mcp = ModelConfParser(conf_file)
            try:
                mcp.parse()
            except (ValueError, MacsylibError) as err:
                errors.append(str(err))
        else:
            _log.info(f"There is no model configuration for package {self.name}.")
        return errors, warnings


    def _check_metadata(self) -> tuple[list[str], list[str]]:
        """
        Check the QA of package metadata_path

        :return: errors and warnings
        :rtype: tuple of 2 lists ([str error_1, ...], [str warning_1, ...])
        """
        _log.info(f"Checking '{self.name}' {self.metadata_path}")
        errors = []
        warnings = []
        try:
            data = self._load_metadata()
        except ValueError as err:
            errors.extend([msg for msg in err.args[0].split('\n') if msg])
            return errors, warnings

        nice_to_have = ("cite", "doc", "license", "copyright")
        for item in nice_to_have:
            if not getattr(data, item):
                warnings.append(f"It's better if the field '{item}' is setup in '{self.metadata_path}' file.")

        if data.vers:
            warnings.append("The field 'vers' is not required anymore.\n"
                            "  It will be ignored and set by macsydata during installation phase according "
                            "to the git tag.")
        return errors, warnings


    def help(self) -> str:
        """
        return the content of the README file
        """
        if self.readme:
            with open(self.readme) as readme:
                pack_help = ''.join(readme.readlines())
        else:
            pack_help = f"No help available for package '{self.name}'."
        return pack_help


    def info(self) -> str:
        """
        :return: some information about the package
        """
        metadata = self._load_metadata()
        if metadata.cite:
            cite = '\n'.join([f"\t- {c}".replace('\n', '\n\t  ') for c in metadata.cite]).rstrip()
        else:
            cite = "\t- No citation available"
        doc = metadata.doc if metadata.doc else "No documentation available"
        license = metadata.license if metadata.license else "No license available"
        copyrights = f"copyright: {metadata.copyright_date}, {metadata.copyright_holder}" \
            if metadata.copyright else ''
        pack_name = self.name

        info = f"""
{pack_name} ({metadata.vers})

maintainer: {metadata.maintainer.name} <{metadata.maintainer.email}>

{metadata.short_desc}

how to cite:
{cite}

documentation
\t{doc}

This data are released under {license}
{copyrights}
"""
        return info


def parse_arch_path(path: str) -> tuple[str, str]:
    """

    :param str path: the path to the archive
    :return: the name of the package and it's version
    :rtype: tuple
    :raise ValueError: if the extension of the package is neither '.tar.gz' nor '.tgz'
                       or if the package does not seem to include version 'pack_name-<vers>.ext'
    """
    pack_vers_name = os.path.basename(path)
    if pack_vers_name.endswith('.tar.gz'):
        pack_vers_name = pack_vers_name[:-7]
    elif pack_vers_name.endswith('.tgz'):
        pack_vers_name = pack_vers_name[:-4]
    else:
        raise ValueError(f"{path} does not seem to be a package (a tarball).")
    *pack_name, vers = pack_vers_name.split('-')
    if not pack_name:
        raise ValueError(f"{path} does not seem to not be versioned.")
    pack_name = '-'.join(pack_name)
    return pack_name, vers
