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


"""
This is the entrypoint to the macsydata command
macsydata allow the user to manage the MacSyFinder models
"""

import sys
import os
import argparse
import shutil
import textwrap
import time
import pathlib
import logging
import xml.etree.ElementTree as ET
import typing
from functools import partialmethod
from importlib import resources as impresources

import colorlog
from packaging import requirements, specifiers, version

import macsylib
from macsylib import get_version_message
from macsylib.error import MacsydataError, MacsyDataLimitError
from macsylib.config import MacsyDefaults, Config
from macsylib.registries import ModelRegistry, ModelLocation, scan_models_dir
from macsylib.model_package import RemoteModelIndex, LocalModelIndex, ModelPackage, parse_arch_path
from macsylib.metadata import Metadata, Maintainer
from macsylib import licenses

# _log is set in main func
_log = None


##################
# Remote actions #
##################


def do_available(args: argparse.Namespace) -> None:
    """
    List Models available on macsy-models
    :param args: the arguments passed on the command line
    :return: None
    """
    remote = RemoteModelIndex(org=args.org)
    models_packages = remote.list_packages()
    for m_pack in models_packages:
        all_versions = remote.list_package_vers(m_pack)
        if all_versions:
            last_vers = all_versions[0]
            metadata = remote.get_metadata(m_pack, vers=last_vers)
            pack_vers = f"{m_pack} ({last_vers})"
            # 26 = length of field
            # 25 = number of displayed chars
            print(f"{pack_vers:26.25} - {metadata['short_desc']}")


def do_search(args: argparse.Namespace) -> None:
    """
    Search macsy-models for Model in a remote index.
    by default search in package name,
    if option -S is set search also in description
    by default the search is case-insensitive except if
    option --match-case is set.

    :param args: the arguments passed on the command line
    """
    try:
        remote = RemoteModelIndex(org=args.org)
        packages = remote.list_packages()
        if args.careful:
            results = _search_in_desc(args.pattern, remote, packages, match_case=args.match_case)
        else:
            results = _search_in_pack_name(args.pattern, remote, packages, match_case=args.match_case)
        for m_pack, last_vers, desc in results:
            pack_vers = f"{m_pack} ({last_vers})"
            print(f"{pack_vers:26.25} - {desc}")
    except MacsyDataLimitError as err:
        _log.critical(str(err))


def _search_in_pack_name(pattern: str,
                         remote: RemoteModelIndex,
                         m_packages: list[str],
                         match_case: bool = False) -> list[tuple[str, str, dict]]:
    """

    :param pattern: the substring to search packages names
    :param remote: the uri of the macsy-models index
    :param m_packages: list of model packages to search in
    :param match_case: True if the search is case-sensitive, False otherwise
    :return:
    """
    results = []
    for pack_name in m_packages:
        if not match_case:
            pack = pack_name.lower()
            pattern = pattern.lower()
        else:
            pack = pack_name

        if pattern in pack:
            all_versions = remote.list_package_vers(pack_name)
            if all_versions:
                metadata = remote.get_metadata(pack_name)
                last_vers = all_versions[0]
                results.append((pack_name, last_vers, metadata['short_desc']))
    return results


def _search_in_desc(pattern: str,
                    remote: RemoteModelIndex,
                    m_packages: list[str],
                    match_case: bool = False) -> tuple[str, str, str]:
    """

    :param pattern: the substring to search packages descriptions
    :param remote: the uri of the macsy-models index
    :param m_packages: list of model packages to search in
    :param match_case: True if the search is case-sensitive, False otherwise
    :return:
    """
    results = []
    for pack_name in m_packages:
        all_versions = remote.list_package_vers(pack_name)
        if all_versions:
            metadata = remote.get_metadata(pack_name)
            desc = metadata['short_desc']
            if not match_case:
                pack = pack_name.lower()
                desc = desc.lower()
                pattern = pattern.lower()
            else:
                pack = pack_name

            if pattern in pack or pattern in desc:
                last_vers = all_versions[0]
                results.append((pack_name, last_vers, metadata['short_desc']))
    return results


def do_download(args: argparse.Namespace) -> str | None:
    """
    Download tarball from remote models' repository.

    :param args: the arguments passed on the command line
    :type args: :class:`argparse.Namespace` object
    """
    try:
        remote = RemoteModelIndex(org=args.org)
        req = requirements.Requirement(args.package)
        model_pack_name = req.name
        specifier = req.specifier
        all_versions = remote.list_package_vers(model_pack_name)
        if all_versions:
            compatible_version = list(specifier.filter(all_versions))
            if compatible_version:
                vers = compatible_version[0]
                _log.info(f"Downloading {model_pack_name} {vers}")
                arch_path = remote.download(model_pack_name, vers, dest=args.dest)
                _log.info(f"Successfully downloaded models {model_pack_name} in {arch_path}")
                return arch_path
            else:
                _log.error(f"No version that satisfy requirements '{specifier}' for '{model_pack_name}'.")
                _log.warning(f"Available versions: {','.join(all_versions)}")
        return None
    except MacsyDataLimitError as err:
        _log.critical(str(err))
        return None

def _find_all_installed_packages(models_dir: list[str] | None = None, package_name: str = 'macsylib') -> ModelRegistry:
    """

    :param models_dir: list of path where package can be find.
    :param package_name: the name of the high level tool that embed macsylib
    :return: all models installed
    """
    defaults = MacsyDefaults(package_name=package_name)
    args = argparse.Namespace()
    if models_dir is not None:
        args.models_dir = models_dir
    config = Config(defaults, args)
    model_dirs = config.models_dir()
    registry = ModelRegistry()
    for model_dir in model_dirs:
        try:
            for model_loc in scan_models_dir(model_dir, profile_suffix=config.profile_suffix()):
                registry.add(model_loc)
        except PermissionError as err:
            _log.warning(f"{model_dir} is not readable: {err} : skip it.")
    return registry


def _find_installed_package(model_pack_name: str,
                            models_dir: list[str] | None = None,
                            package_name: str = 'macsylib') -> ModelLocation | None:
    """
    search if a package names *pack_name* is already installed

    :param model_pack_name: the name of the family model to search
    :param models_dir: list of path where package can be find.
    :param package_name: the name of the high level tool that embed macsylib, for instance: 'macsyfinder'
    :return: The model location corresponding to the `pack_name`
    """
    registry = _find_all_installed_packages(models_dir, package_name=package_name)
    try:
        return registry[model_pack_name]
    except KeyError:
        return None


def do_install(args: argparse.Namespace) -> None:
    """
    Install new models in macsyfinder local models repository.

    :param args: the arguments passed on the command line
    :raise RuntimeError: if there is problem is installed package
    :raise ValueError: if the package and/or version is not found
    """
    def clean_cache(model_index):
        if args.no_clean:
            _log.debug(f"skip cleaning {model_index.cache}")
            return
        try:
            shutil.rmtree(model_index.cache)
        except Exception as err:
            _log.warning(f"Cannot clean cache '{model_index.cache}': {err}")

    def create_dir(path):
        if not os.path.exists(path):
            os.makedirs(path)
        elif os.path.exists(path) and not os.path.isdir(path):
            clean_cache(model_index)
            raise RuntimeError(f"'{path}' already exist and is not a directory.")
        return path

    if os.path.exists(args.model_package):
        remote = False
        pack_name, inst_vers = parse_arch_path(args.model_package)
        user_req = requirements.Requirement(f"{pack_name}=={inst_vers}")
    else:
        remote = True
        user_req = requirements.Requirement(args.model_package)

    if args.target:
        dest = os.path.realpath(args.target)
        if not os.path.exists(dest):
            os.makedirs(dest)
        elif os.path.exists(dest) and not os.path.isdir(dest):
            raise RuntimeError(f"'{dest}' already exist and is not a directory.")

    model_pack_name = user_req.name
    inst_pack_loc = _find_installed_package(model_pack_name, models_dir=args.target, package_name=args.package_name)
    if inst_pack_loc:
        m_pack = ModelPackage(inst_pack_loc.path)
        try:
            local_vers = version.Version(m_pack.metadata.vers)
        except FileNotFoundError:
            _log.error(f"{model_pack_name} locally installed is corrupted.")
            _log.warning(f"You can fix it by removing '{inst_pack_loc.path}'.")
            sys.tracebacklimit = 0
            raise RuntimeError() from None
    else:
        local_vers = None
    user_specifier = user_req.specifier
    if not user_specifier and inst_pack_loc:
        # the user do not request for a specific version
        # and there already a version installed locally
        user_specifier = specifiers.SpecifierSet(f">{local_vers}")

    if remote:
        try:
            all_available_versions = _get_remote_available_versions(model_pack_name, args.org)
        except (ValueError, MacsyDataLimitError) as err:
            _log.error(str(err))
            sys.tracebacklimit = 0
            raise ValueError from None
    else:
        all_available_versions = [inst_vers]

    compatible_version = list(user_specifier.filter(all_available_versions))
    if not compatible_version and local_vers:
        target_vers = version.Version(all_available_versions[0])
        if target_vers == local_vers and not args.force:
            _log.warning(f"Requirement already satisfied: {model_pack_name}{user_specifier} in {m_pack.path}.\n"
                         f"To force installation use option -f --force-reinstall.")
            return None
        elif target_vers < local_vers and not args.force:
            _log.warning(f"{model_pack_name} ({local_vers}) is already installed.\n"
                         f"To downgrade to {target_vers} use option -f --force-reinstall.")
            return None
        else:
            # target_vers == local_vers and args.force:
            # target_vers < local_vers and args.force:
            pass
    elif not compatible_version:
        # No compatible version and not local version
        _log.warning(f"Could not find version that satisfied '{model_pack_name}{user_specifier}'")
        return None
    else:
        # it exists at least one compatible version
        target_vers = version.Version(compatible_version[0])
        if inst_pack_loc:
            if target_vers > local_vers and not args.upgrade:
                _log.warning(f"{model_pack_name} ({local_vers}) is already installed but {target_vers} version is available.\n"
                             f"To install it please run '{args.tool_name} install --upgrade {model_pack_name}'")
                return None
            elif target_vers == local_vers and not args.force:
                _log.warning(f"Requirement already satisfied: {model_pack_name}{user_specifier} in {m_pack.path}.\n"
                             f"To force installation use option -f --force-reinstall.")
                return None
            else:
                # target_vers > local_vers and args.upgrade:
                # I have to install a new package
                pass

    # if i'm here it's mean I have to install a new package
    if remote:
        _log.info(f"Downloading {model_pack_name} ({target_vers}).")
        model_index = RemoteModelIndex(org=args.org, cache=args.cache)
        _log.debug(f"call download with pack_name={model_pack_name}, vers={target_vers}")
        arch_path = model_index.download(model_pack_name, str(target_vers))
    else:
        model_index = LocalModelIndex(cache=args.cache)
        arch_path = args.model_package

    _log.info(f"Extracting {model_pack_name} ({target_vers}).")
    cached_pack = model_index.unarchive_package(arch_path)

    _log.debug(f"package is cached at: {cached_pack}")
    # we do not rely on vers in metadat any longer
    # but we inject the version from the version specify in package name
    # the package name is set by github according to the tag
    _log.debug("injecting version in metadata")
    metadata_path = os.path.join(cached_pack, Metadata.name)
    if not os.path.exists(metadata_path):
        maintainer_loc = f" ({model_index.repos_url})"
        clean_cache(model_index)

        _log.error(f"Failed to install '{model_pack_name}-{target_vers}' : The model package has no 'metadata.yml' file.")
        _log.warning(f"Please contact the package maintainer.{maintainer_loc}")
        sys.tracebacklimit = 0
        raise MacsydataError() from None

    metadata = Metadata.load(metadata_path)
    metadata.vers = target_vers
    metadata.save(metadata_path)

    if args.user:
        dest = os.path.realpath(os.path.join(os.path.expanduser('~'), f'.{args.package_name}', 'models'))
        create_dir(dest)
    elif args.target:
        dest = args.target
    elif 'VIRTUAL_ENV' in os.environ:
        dest = os.path.join(os.environ['VIRTUAL_ENV'], 'share', args.package_name, 'models')
        create_dir(dest)
    else:
        defaults = MacsyDefaults(package_name=args.package_name)
        config = Config(defaults, argparse.Namespace())
        models_dirs = config.models_dir()
        if not models_dirs:
            clean_cache(model_index)
            msg = f"""There is no canonical directories to store models:
You can create one in your HOME to enable the models for the user
       {args.tool_name} install --user <PACK_NAME>
or for a project
       {args.tool_name} install --models <PACK_NAME>
In this latter case you have to specify --models-dir <path_to_models_dir> on the macsyfinder command line
for the system wide models installation please refer to the documentation.
"""
            _log.error(msg)
            sys.tracebacklimit = 0
            raise ValueError() from None
        dest = config.models_dir()[0]

    if inst_pack_loc:
        old_pack_path = f"{inst_pack_loc.path}.old"
        shutil.move(inst_pack_loc.path, old_pack_path)

    _log.info(f"Installing {model_pack_name} ({target_vers}) in {dest}")
    try:
        _log.debug(f"move {cached_pack} -> {dest}")
        shutil.move(cached_pack, dest)
    except PermissionError as err:
        clean_cache(model_index)
        _log.error(f"{dest} is not writable: {err}")
        _log.warning("Maybe you can use --user option to install in your HOME.")
        sys.tracebacklimit = 0
        raise ValueError() from None

    _log.info("Cleaning.")
    shutil.rmtree(pathlib.Path(cached_pack).parent)
    if inst_pack_loc:
        shutil.rmtree(old_pack_path)
    _log.info(f"The models {model_pack_name} ({target_vers}) have been installed successfully.")
    clean_cache(model_index)


def _get_remote_available_versions(model_pack_name: str, org: str) -> list[str]:
    """
    Ask the organization org the available version for the package pack_name
    :param model_pack_name: the name of the models package
    :param org: The remote organization to query
    :return: list of available version for the package
    """
    remote = RemoteModelIndex(org=org)
    all_versions = remote.list_package_vers(model_pack_name)
    return all_versions

#################
# Local actions #
#################


def do_uninstall(args: argparse.Namespace) -> None:
    """
    Remove models from macsyfinder local models repository.

    :param args: the arguments passed on the command line
    :raise ValueError: if the package is not found locally
    """
    model_pack_name = args.model_package
    inst_pack_loc = _find_installed_package(model_pack_name,
                                            models_dir=args.models_dir,
                                            package_name=args.package_name)
    if inst_pack_loc:
        pack = ModelPackage(inst_pack_loc.path)
        shutil.rmtree(pack.path)
        _log.info(f"models '{model_pack_name}' in {pack.path} uninstalled.")
    else:
        _log.error(f"Models '{model_pack_name}' not found locally.")
        sys.tracebacklimit = 0
        raise ValueError()


def do_info(args: argparse.Namespace) -> None:
    """
    Show information about installed model.

    :param args: the arguments passed on the command line
    :raise ValueError: if the package is not found locally
    """
    model_pack_name = args.model_package
    inst_pack_loc = _find_installed_package(model_pack_name,
                                            models_dir=args.models_dir,
                                            package_name=args.package_name)

    if inst_pack_loc:
        pack = ModelPackage(inst_pack_loc.path)
        print(pack.info())
    else:
        _log.error(f"Models '{model_pack_name}' not found locally.")
        sys.tracebacklimit = 0
        raise ValueError()


def do_list(args: argparse.Namespace) -> None:
    """
    List installed models.

    :param args: the arguments passed on the command line
    """
    registry = _find_all_installed_packages(models_dir=args.models_dir,
                                            package_name=args.package_name)
    for model_loc in registry.models():
        try:
            pack = ModelPackage(model_loc.path)
            pack_vers = pack.metadata.vers
            model_path = f"   ({model_loc.path})" if args.long else ""
            if args.outdated or args.uptodate:
                remote = RemoteModelIndex(org=args.org)
                all_versions = remote.list_package_vers(pack.name)
                specifier = specifiers.SpecifierSet(f">{pack_vers}")
                update_vers = list(specifier.filter(all_versions))
                if args.outdated and update_vers:
                    print(f"{model_loc.name}-{update_vers[0]} [{pack_vers}]{model_path}")
                if args.uptodate and not update_vers:
                    print(f"{model_loc.name}-{pack_vers}{model_path}")
            else:
                print(f"{model_loc.name}-{pack_vers}{model_path}")
        except Exception as err:
            if args.verbose > 1:
                _log.warning(str(err))


def do_freeze(args: argparse.Namespace) -> None:
    """
    display all models installed with their respective version, in requirement format.

    :param args: the arguments passed on the command line
    """
    registry = _find_all_installed_packages(package_name=args.package_name)
    for model_loc in sorted(registry.models(), key=lambda ml: ml.name.lower()):
        try:
            pack = ModelPackage(model_loc.path)
            pack_vers = pack.metadata.vers
            print(f"{model_loc.name}=={pack_vers}")
        except Exception:
            pass


def do_cite(args: argparse.Namespace) -> None:
    """
    How to cite an installed model.

    :param args: the arguments passed on the command line
    """
    model_pack_name = args.model_package
    inst_pack_loc = _find_installed_package(model_pack_name,
                                            models_dir=args.models_dir,
                                            package_name=args.package_name)
    if inst_pack_loc:
        pack = ModelPackage(inst_pack_loc.path)
        pack_citations = pack.metadata.cite
        pack_citations = [cite.replace('\n', '\n  ') for cite in pack_citations]
        pack_citations = '\n- '.join(pack_citations)
        pack_citations = '_ ' + pack_citations.rstrip()
        macsy_cite = macsylib.__citation__
        macsy_cite = macsy_cite.replace('\n', '\n  ')
        macsy_cite = '- ' + macsy_cite
        print(f"""To cite {model_pack_name}:

{pack_citations}

To cite MacSyLib:

{macsy_cite}
""")
    else:
        _log.error(f"Models '{model_pack_name}' not found locally.")
        sys.tracebacklimit = 0
        raise ValueError()


def do_help(args: argparse.Namespace) -> None:
    """
    Display on stdout the content of readme file
    if the readme file does not exist display a message to the user see :meth:`macsylib.package.help`

    :param args: the arguments passed on the command line (the package name)
    :return: None
    :raise ValueError: if the package name is not known.
    """
    model_pack_name = args.model_package
    inst_pack_loc = _find_installed_package(model_pack_name,
                                            models_dir=args.models_dir,
                                            package_name=args.package_name)
    if inst_pack_loc:
        pack = ModelPackage(inst_pack_loc.path)
        print(pack.help())
    else:
        _log.error(f"Models '{model_pack_name}' not found locally.")
        sys.tracebacklimit = 0
        raise ValueError()


def do_check(args: argparse.Namespace) -> None:
    """

    :param args: the arguments passed on the command line
    :rtype: None
    """
    model_pack = ModelPackage(args.path)
    errors, warnings = model_pack.check()
    if errors:
        for error in errors:
            _log.error(error)
        _log.error("Please fix issues above, before publishing these models.")
        sys.tracebacklimit = 0
        raise ValueError()
    if warnings:
        for warning in warnings:
            _log.warning(warning)
        _log.warning(f"""
{args.tool_name} says: You're only giving me a partial QA payment?
I'll take it this time, but I'm not happy.
I'll be really happy, if you fix warnings above, before to publish these models.""")

    if not warnings:
        _log.info("If everyone were like you, I'd be out of business")
        _log.info("To push the models in organization:")
        if os.path.realpath(os.getcwd()) != model_pack.path:
            # I use level 25 just to remove color
            _log.log(25, f"\tcd {model_pack.path}")
        if not os.path.exists(os.path.join(model_pack.path, '.git')):
            _log.info("Transform the models into a git repository")
            _log.log(25, "\tgit init .")
            _log.log(25, "\tgit add .")
            _log.log(25, "\tgit commit -m 'initial commit'")
            _log.info("add a remote repository to host the models")
            _log.info("for instance if you want to add the models to 'macsy-models'")
            _log.log(25, "\tgit remote add origin https://github.com/macsy-models/")

        _log.log(25, "\tgit tag -a <tag vers>  # check "
                     "https://macsylib.readthedocs.io/en/latest/modeler_guide/publish_package.html#sharing-your-models")
        _log.log(25, "\tgit push origin <tag vers>")


def do_show_definition(args: argparse.Namespace) -> None:
    """
    display on stdout the definition if only a package or sub-package is specified
    display all model definitions in the corresponding package or subpackage

    for instance

    `TXSS+/bacterial T6SSii T6SSiii`

    display models *TXSS+/bacterial/T6SSii* and *TXSS+/bacterial/T6SSiii*

    `TXSS+/bacterial all` or `TXSS+/bacterial`

    display all models contains in *TXSS+/bacterial subpackage*

    :param args: the arguments passed on the command line
    """
    def display_definition(path):
        with open(path, 'r', encoding='utf8') as def_file:
            def_txt = def_file.read()
        return def_txt

    model_family, *models = args.model
    model_pack_name, *sub_family = model_family.split('/')

    inst_pack_loc = _find_installed_package(model_pack_name,
                                            models_dir=args.models_dir,
                                            package_name=args.package_name)

    if inst_pack_loc:
        if not models or 'all' in models:
            root_def_name = model_family if sub_family else None
            try:
                path_2_display = sorted(
                    [(p.fqn, p.path) for p in inst_pack_loc.get_all_definitions(root_def_name=root_def_name)]
                )
            except ValueError:
                _log.error(f"'{'/'.join(sub_family)}' not found in package '{model_pack_name}'.")
                sys.tracebacklimit = 0
                raise ValueError() from None

            for fqn, def_path in path_2_display:
                print(f"""<!-- {fqn} {def_path} -->
{display_definition(def_path)}
""", file=sys.stdout)
        else:
            fqn_to_get = [f'{model_family}/{m}' for m in models]
            for fqn in fqn_to_get:
                try:
                    def_path = inst_pack_loc.get_definition(fqn).path
                    print(f"""<!-- {fqn} {def_path} -->
{display_definition(def_path)}
""", file=sys.stdout)
                except ValueError:
                    _log.error(f"Model '{fqn}' not found.")
                    continue
    else:
        _log.error(f"Model Package '{model_pack_name}' not found.")
        sys.tracebacklimit = 0
        raise ValueError() from None


def do_init_package(args: argparse.Namespace) -> None:
    """
    Create a template for data package

        - skeleton for metadata.yml
        - definitions directory with a skeleton of models.xml
        - profiles directory
        - skeleton for README.md file
        - COPYRIGHT file (if holders option is set)
        - LICENSE file (if model_license option is set)

    :param args: The parsed commandline subcommand arguments
    :return: None
    """
    try:
        import git  # pylint: disable=import-outside-toplevel
    except ModuleNotFoundError:
        import warnings # pylint: disable=import-outside-toplevel
        warnings.warn(f"GitPython is not installed, `{args.tool_name} init` is disabled.\n"
                      "To turn this feature ON:\n"
                      "  - install git\n"
                      f"  - then run `python -m pip install {args.package_name}[model]` in your activated environment.")
        sys.exit(1)

    def add_metadata(pack_dir: str, maintainer: str, email: str,
                     desc: str | None = None, model_license: str | None = None,
                     c_date: str | None = None, c_holders: str | None = None) -> None:
        """

        :param pack_dir: the package directory path
        :param maintainer: the maintainer name
        :param email: the maintainer email
        :param desc: a One line description of the package
        :param model_license: the model_license chosen
        :param c_date: the date of the copyright
        :param c_holders: the holders of the copyright
        """
        meta_path = os.path.join(pack_dir, Metadata.name)
        if os.path.exists(meta_path):
            metadata = Metadata.load(meta_path)
            metadata.vers = None
        else:
            desc = desc if desc else "description in one line of this package"
            metadata = Metadata(Maintainer(maintainer, email), desc)
            metadata.cite = ['Place here how to cite this package, it can hold several citation',
                             'citation 2 (optional)']
            metadata.doc = 'where to find documentation about this package'
        if c_date:
            metadata.copyright_date = c_date
        else:
            metadata.copyright_date = str(time.localtime().tm_year)
        if c_holders:
            metadata.copyright_holder = c_holders
        else:
            metadata.copyright_holder = "copyright holders <My institution>"
        if model_license:
            metadata.license = licenses.name_2_url(model_license)

        metadata.save(meta_path)


    def add_def_skeleton(model_license: str | None = None) -> None:
        """
        Create an example of model definition

        :param model_license: the text of the model_license
        """
        model = ET.Element('model',
                           attrib={'inter_gene_max_space': "5",
                                   'min_mandatory_genes_required': "2",
                                   'min_genes_required': "3",
                                   'vers': "2.0"
                                   }
        )
        comment = ET.Comment('GENE_1 is a mandatory gene. GENE_1.hmm must exist in profiles directory')
        model.append(comment)
        # add mandatory gene
        ET.SubElement(model, 'gene',
                      attrib={'name': 'GENE_1',
                              'presence': 'mandatory'})
        comment = ET.Comment("GENE_2 is accessory and can be exchanged with GENE_3 which play a similar role in model.\n"
                             "Both GENE_2.hmm and GENE_3.hmm must exist in profiles_directory")
        model.append(comment)
        accessory = ET.SubElement(model, 'gene',
                                  attrib={'name': 'GENE_2',
                                          'presence': 'accessory',
                                          })
        exchangeables = ET.SubElement(accessory, 'exchangeables')
        ET.SubElement(exchangeables, 'gene',
                      attrib={'name': 'GENE_3'})
        comment = ET.Comment("GENE_4 can be anywhere in the genome and not clusterized with some other model genes")
        model.append(comment)
        ET.SubElement(model, 'gene',
                      attrib={'name': 'GENE_4',
                              'presence': 'accessory',
                              'loner': 'true'}
                              )
        comment = ET.Comment("GENE_5 can be shared by several systems instance from different models.")
        model.append(comment)
        ET.SubElement(model, 'gene',
                      attrib={'name': 'GENE_5',
                      'presence': 'accessory',
                      'multi_model': 'true'}
                      )
        comment = ET.Comment("GENE_6 have specific clusterisation rule")
        model.append(comment)
        ET.SubElement(model, 'gene',
                      attrib={'name': 'GENE_6',
                              'presence': 'accessory',
                              'inter_gene_max_space': '10'}
                              )
        comment = ET.Comment("\nFor exhaustive documentation about grammar visit \n"
                             "https://macsylib.readthedocs.io/en/latest/modeler_guide/package.html\n")
        model.append(comment)
        tree = ET.ElementTree(model)
        ET.indent(model)
        def_path = os.path.join(pack_dir, 'definitions', 'model_example.xml')
        tree.write(def_path,
                   encoding='UTF-8',
                   xml_declaration=True)

        if model_license:
            # Elementtree API does not allow to insert comment outside the tree (before root node)
            # this is the reason of this workaround
            # write the xml, read it as text, insert the comment, and write it again :-(
            with open(def_path, 'r', encoding='utf8') as def_file:
                definition = def_file.readlines()
            license_note = f"""<!--
{model_license}-->
"""
            definition.insert(1, license_note)
            with open(def_path, 'w', encoding='utf8') as def_path:
                def_path.writelines(definition)

    def add_license(pack_dir: str, license_text: str):
        """
        Create a model_license file

        :param pack_dir: the package directory path
        :param license_text: the text of the model_license
        """
        with open(os.path.join(pack_dir, 'LICENSE'), 'w', encoding='utf8') as license_file:
            license_file.write(license_text)

    def add_copyright(pack_dir: str, pack_name: str, date: str, holders: str, desc: str):
        """
        :param pack_dir: The path of package directory
        :param pack_name: The name of the package
        :param date: The date (year) of package creation
        :param holders: The copyright holders
        :param desc: One line description of the package
        """
        desc = desc if desc is not None else ''
        head = textwrap.fill(f"{pack_name} - {desc}")
        text = f"""{head}

Copyright (c) {date} {holders}
"""
        with open(os.path.join(pack_dir, 'COPYRIGHT'), 'w', encoding='utf8') as copyright_file:
            copyright_file.write(text)

    def add_readme(pack_dir: str, model_pack_name: str, desc: str):
        """
        :param pack_dir: The path of package directory
        :param model_pack_name: The name of the package
        :param desc: One line description of the package
        """
        desc = ' ' + desc if desc is not None else ''
        text = f"""
# {model_pack_name}:{desc}

Place here information about {model_pack_name}

- how to use it
- how to cite it
- ...

using markdown syntax
https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax
"""
        with open(os.path.join(pack_dir, 'README.md'), 'w', encoding='utf8') as readme_file:
            readme_file.write(text)

    def create_model_conf(pack_dir: str, model_license: str = None) -> None:
        """

        :param pack_dir: The path of the package directory
        :param model_license: The text of the chosen license
        """
        msf_defaults = MacsyDefaults()
        model_conf = ET.Element('model_config')

        weights = ET.SubElement(model_conf, 'weights')
        mandatory = ET.SubElement(weights, 'mandatory')
        mandatory.text = str(msf_defaults['mandatory_weight'])
        accessory = ET.SubElement(weights, 'accessory')
        accessory.text = str(msf_defaults['accessory_weight'])
        exchangeable = ET.SubElement(weights, 'exchangeable')
        exchangeable.text = str(msf_defaults['exchangeable_weight'])
        redundancy_penalty = ET.SubElement(weights, 'redundancy_penalty')
        redundancy_penalty.text = str(msf_defaults['redundancy_penalty'])
        out_of_cluster = ET.SubElement(weights, 'out_of_cluster')
        out_of_cluster.text = str(msf_defaults['out_of_cluster_weight'])

        filtering = ET.SubElement(model_conf, 'filtering')
        e_value_search = ET.SubElement(filtering, 'e_value_search')
        e_value_search.text = str(msf_defaults['e_value_search'])
        i_evalue_sel = ET.SubElement(filtering, 'i_evalue_sel')
        i_evalue_sel.text = str(msf_defaults['i_evalue_sel'])
        coverage_profile = ET.SubElement(filtering, 'coverage_profile')
        coverage_profile.text = str(msf_defaults['coverage_profile'])
        cut_ga = ET.SubElement(filtering, 'cut_ga')
        cut_ga.text = str(msf_defaults['cut_ga'])

        tree = ET.ElementTree(model_conf)
        conf_path = os.path.join(pack_dir, 'model_conf.xml')

        ET.indent(model_conf)
        tree.write(conf_path,
                   encoding='UTF-8',
                   xml_declaration=True)
        if model_license:
            # Elementtree API does not allow to insert comment outside the tree (before root node)
            # this is the reason of this workaround
            # write the xml, read it as text, insert the comment, and write it again :-(

            with open(conf_path, 'r', encoding='utf8') as conf_file:
                conf = conf_file.readlines()
            model_license = f"""<!--
{model_license}-->
"""
            conf.insert(1, model_license)
            with open(conf_path, 'w', encoding='utf8') as conf_file:
                conf_file.writelines(conf)

    def create_repo(model_package_name: str, models_dir: str | None = None) -> str:
        pack_path = model_package_name if not models_dir else os.path.join(models_dir, model_package_name)
        if os.path.exists(pack_path):
            if os.path.isdir(pack_path):
                content = os.listdir(pack_path)
                if content:
                    # The directory is not empty
                    lacks = []
                    for item in 'definitions', 'profiles':
                        if item not in content:
                            lacks.append(item)
                    if lacks:
                        _log.error(f"{pack_path} already exits and not look a model package:"
                                   f" There is no {', '.join(lacks)}.")
                        sys.tracebacklimit = 0
                        raise ValueError()
                    _log.info(f"{pack_path} already exits and look a model package:"
                              " Transform it in git repository.")
                    repo = git.Repo.init(pack_path)
                else:
                    # the dir pack_name is empty
                    repo = git.Repo.init(pack_path)
            else:
                _log.critical(f"{pack_path} already exists and is not a directory.")
                sys.tracebacklimit = 0
                raise ValueError()
        else:
            os.makedirs(pack_path)
            repo = git.Repo.init(pack_path)
        return repo

    ######################
    # Initialize ModelPackage #
    ######################
    c_date = str(time.localtime().tm_year)
    repo = create_repo(args.model_package, models_dir=args.models_dir)
    pack_dir = repo.working_dir
    def_dir = os.path.join(pack_dir, 'definitions')
    profiles_dir = os.path.join(pack_dir, 'profiles')
    if os.path.exists(profiles_dir):
        _log.warning("The 'profiles' directory already exists.")
    else:
        os.mkdir(profiles_dir)

    if args.holders:
        add_copyright(pack_dir, args.package_name, c_date, args.holders, args.desc)
    else:
        if not os.path.exists(os.path.join(pack_dir, 'COPYRIGHT')):
            _log.warning("Consider to add copyright to protect your rights.")

    if args.license:
        try:
            license_text = licenses.license(args.license,
                                            args.model_package,
                                            args.authors,
                                            c_date, args.holders,
                                            args.desc)
            add_license(pack_dir, license_text)
        except KeyError:
            _log.error(f"The model_license {args.license} is not managed by init (see macsydata init help). "
                       f"You will have to put the model_license by hand in package.")
            license_text=None
    else:
        licence_path = os.path.exists(os.path.join(pack_dir, 'LICENSE'))
        if not licence_path:
            _log.warning(f"Consider licensing {args.package_name} to give the end-user the right to use your package,"
                         f"and protect your rights. https://data.europa.eu/elearning/en/module4/#/id/co-01")
            license_text = None
        else:
            with open(licence_path, encoding='utf8') as licencse_file:
                license_text = ''.join(licencse_file.readlines())

    if os.path.exists(def_dir):
        _log.warning("The 'defintions' directory already exists.")
        if os.listdir(def_dir):
            # def_dir is not empty
            _log.warning("Do not forget to add model_license in each xml definition file \n"
                         "https://macsyfinder.readthedocs.io/en/latest/modeler_guide/package.html")
        else:
            add_def_skeleton(model_license=license_text)
    else:
        os.mkdir(def_dir)
        add_def_skeleton(model_license=license_text)
    if not os.path.exists(os.path.join(pack_dir, 'model_conf.xml')):
        create_model_conf(pack_dir, model_license=license_text)
    if not (os.path.exists(os.path.join(pack_dir, 'README')) or os.path.exists(os.path.join(pack_dir, 'README.md'))):
        add_readme(pack_dir, args.model_package, args.desc)

    add_metadata(pack_dir, args.maintainer, args.email, desc=args.desc, model_license=args.license,
                 c_date=c_date, c_holders=args.holders)

    # add files to repository
    untracked_files = repo.untracked_files
    for file in untracked_files:
        repo.index.add(file)
    untracked_str = '- ' + '\n- '.join(untracked_files)
    repo.index.commit(f"""initial commit

add files:
{untracked_str}
""")

    pre_push_path = impresources.files('macsylib') / 'data' / 'pre-push'
    dest = os.path.join(repo.git_dir, 'hooks', 'pre-push')
    if os.path.exists(dest):
        _log.warning(f"A git hook '{pre_push_path}' already exists cannot install macsydata prepush hook.")
        _log.warning("Do it manually, check documentation: ")
    else:
        shutil.copy(pre_push_path, dest)
        os.chmod(dest, 0o755)
    _log.info(f"""The skeleton of {args.model_package} is ready.
The package is located at {pack_dir}

- Edit metadata.yml and fill how to cite your package and where to find documentation about it.
- Add hmm profiles in {pack_dir}/profiles directory
- A skeleton of model definitions has been added in {pack_dir}/definitions.
  For complete documentation about model grammar read https://macsyfinder.readthedocs.io/en/latest/modeler_guide/modeling.html
- A configuration file has been added (model_conf.xml) with default value tweak this file if needed.
  (https://macsyfinder.readthedocs.io/en/latest/modeler_guide/package.html#model-configuration)

Before to publish your package you can use `macsydata check` to verify it's integrity.
"""
              )
    _log.warning("To share your models with the MacSyModels community.")
    _log.info("Consider to ask for a repository to macsy-models organization (https://github.com/macsy-models)")
    _log.info("then add this new repo to your local package. git remote add <remote name> <remote url>")
    _log.warning(f"\nRead {args.package_name} modeler guide for further details: "
                 "https://macsylib.readthedocs.io/en/latest/modeler_guide/index.html")

##################################
# parsing command line arguments #
##################################

def _cmde_line_header():
    return textwrap.dedent(r'''

         *            *               *              
    *           *               *   *   *  *    **   
      **     *    *   *  *     *        *           
                *      _      *   _   *   _      *  
      *  _ __ ___  ___| |      __| | __ _| |_ __ _ 
        | '_ ` _ \/ __| |     / _` |/ _` | __/ _` |
        | | | | | \__ \ |    | (_| | (_| | || (_| |
        |_| |_| |_|___/_|_____\__,_|\__,_|\__\__,_|
               *        |_____|          *  
     *      *   * *     *   **         *   *  *     
      *      *         *        *    *              
    *                           *  *           *   


    msl_data - Model Management Tool
    ''')


def build_arg_parser(header:str, version:str,
                     package_name:str = 'macsylib', tool_name:str = 'msl_data') -> argparse.ArgumentParser:
    """
    Build argument parser.

    :param header: the header of console scriot
    :param args: The arguments provided on the command line
    :param package_name: the name of the higher package that embed the macsylib (eg 'macsyfinder')
    :param tool_name: the name of this tool as it appear in pyproject.toml
    :return: The arguments parsed
    """

    parser = argparse.ArgumentParser(
        epilog="For more details, visit the MacSyFinder website and see the MacSyFinder documentation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=header)

    # -- general options -- #

    parser.add_argument("-v", "--verbose",
                        action="count",
                        default=0,
                        help="Give more output.")
    parser.add_argument("--version",
                        action="version",
                        version=version)
    # -- subparser options -- #
    # inject  package_name=package_name, tool_name=tool_name in ArgumentParser.set_defaults method by default)
    argparse.ArgumentParser.set_defaults = partialmethod(argparse.ArgumentParser.set_defaults,
                                                         package_name=package_name, tool_name=tool_name)

    subparsers = parser.add_subparsers(help=None)
    #############
    # available #
    #############
    available_subparser = subparsers.add_parser('available',
                                                help='List Models available on macsy-models')
    available_subparser.add_argument('--org',
                                     default="macsy-models",
                                     help="The name of Model organization"
                                          "(default 'macsy-models'))"
                                     )
    available_subparser.set_defaults(func=do_available)
    ############
    # download #
    ############
    download_subparser = subparsers.add_parser('download',
                                               help='Download model packages.')

    download_subparser.set_defaults(func=do_download)
    download_subparser.add_argument('-d', '--dest',
                                    default=os.getcwd(),
                                    help='Download model packages into <dir>.')
    download_subparser.add_argument('--cache',
                                    help=argparse.SUPPRESS)
    download_subparser.add_argument('--org',
                                    default="macsy-models",
                                    help="The name of Model organization"
                                         "(default 'macsy-models'))"
                                    )
    download_subparser.add_argument('model_package', help='Model package name.')
    ###########
    # Install #
    ###########
    install_subparser = subparsers.add_parser('install', help='Install Model packages.')
    install_subparser.set_defaults(func=do_install)
    install_subparser.add_argument('-f', '--force',
                                   action='store_true',
                                   default=False,
                                   help='Reinstall Model package even if it is already up-to-date.')
    install_subparser.add_argument('--org',
                                   default="macsy-models",
                                   help="The name of Model orgagnization"
                                        "(default 'macsy-models'))"
                                   )
    install_dest = install_subparser.add_mutually_exclusive_group()
    install_dest.add_argument('-u', '--user',
                              action='store_true',
                              default=False,
                              help='Install to the MacSYFinder user install directory for your platform. '
                                   f'Typically ~/.{package_name}/data')
    install_dest.add_argument('-t', '--target', '--models-dir',
                              dest='target',
                              help='Install packages into <TARGET> dir instead in canonical location')

    install_subparser.add_argument('-U', '--upgrade',
                                   action='store_true',
                                   default=False,
                                   help='Upgrade specified package to the newest available version.')
    install_subparser.add_argument('model_package',
                                   help='Model Package name.')
    install_subparser.add_argument('--cache',
                                   help=argparse.SUPPRESS)
    install_subparser.add_argument('--no-clean',
                                   action='store_true',
                                   default=False,
                                   # do not clean cache for debugging purpose ONLY
                                   help=argparse.SUPPRESS)
    #############
    # Uninstall #
    #############
    uninstall_subparser = subparsers.add_parser('uninstall',
                                                help='Uninstall packages.')
    uninstall_subparser.set_defaults(func=do_uninstall)
    uninstall_subparser.add_argument('model_package',
                                     help='ModelPackage name.')
    uninstall_subparser.add_argument('--target, --models-dir',
                                     dest='models_dir',
                                     help='the path of the alternative root directory containing package instead used '
                                     'canonical locations')
    ##########
    # search #
    ##########
    search_subparser = subparsers.add_parser('search',
                                             help='Discover new packages.')
    search_subparser.set_defaults(func=do_search)
    search_subparser.add_argument('--org',
                                  default="macsy-models",
                                  help="The name of Model organization"
                                       "(default macsy-models))"
                                  )
    search_subparser.add_argument('-S', '--careful',
                                  default=False,
                                  action='store_true',
                                  help='')
    search_subparser.add_argument('--match-case',
                                  default=False,
                                  action='store_true',
                                  help='')
    search_subparser.add_argument('pattern',
                                  help='Searches for packages matching the pattern.')
    ########
    # info #
    ########
    info_subparser = subparsers.add_parser('info',
                                           help='Show information about packages.')
    info_subparser.add_argument('model_package',
                                help='Model Package name.')
    info_subparser.set_defaults(func=do_info)
    info_subparser.add_argument('--models-dir',
                                help='the path of the alternative root directory containing package instead used '
                                     'canonical locations')
    ########
    # list #
    ########
    list_subparser = subparsers.add_parser('list',
                                           help='List installed packages.')
    list_subparser.set_defaults(func=do_list)
    list_subparser.add_argument('-o', '--outdated',
                                action='store_true',
                                default=False,
                                help='List outdated packages.')
    list_subparser.add_argument('-u', '--uptodate',
                                action='store_true',
                                default=False,
                                help='List uptodate packages')
    list_subparser.add_argument('--org',
                                default="macsy-models",
                                help="The name of Model organization"
                                     "(default macsy-models))"
                                )
    list_subparser.add_argument('--models-dir',
                                help='the path of the alternative root directory containing package instead used '
                                     'canonical locations')
    list_subparser.add_argument('--long', '-l',
                                action='store_true',
                                default=False,
                                help="in addition displays the path where is store each package"
                                )
    list_subparser.add_argument('-v',
                                dest='long',
                                action='store_true',
                                default=False,
                                help="alias for -l/--long option"
                                )
    ##########
    # freeze #
    ##########
    freeze_subparser = subparsers.add_parser('freeze',
                                             help='List installed models in requirements format.')
    freeze_subparser.add_argument('--models-dir',
                                   help='the path of the alternative root directory containing package instead used '
                                        'canonical locations')
    freeze_subparser.set_defaults(func=do_freeze)
    ########
    # cite #
    ########
    cite_subparser = subparsers.add_parser('cite',
                                           help='How to cite a package.')
    cite_subparser.set_defaults(func=do_cite)
    cite_subparser.add_argument('--models-dir',
                                help='the path of the alternative root directory containing package instead used '
                                     'canonical locations')
    cite_subparser.add_argument('package',
                                help='ModelPackage name.')
    ########
    # help #
    ########
    help_subparser = subparsers.add_parser('help',
                                           help='get online documentation.')
    help_subparser.set_defaults(func=do_help)
    help_subparser.add_argument('model_package',
                                help='ModelPackage name.')
    help_subparser.add_argument('--models-dir',
                                help='the path of the alternative root directory containing package instead used '
                                     'canonical locations')
    #########
    # check #
    #########
    check_subparser = subparsers.add_parser('check',
                                            help='check if the directory is ready to be publish as data package')
    check_subparser.set_defaults(func=do_check)
    check_subparser.add_argument('path',
                                 nargs='?',
                                 default=os.getcwd(),
                                 help='the path to root directory models to check')

    ##############
    # definition #
    ##############
    def_subparser = subparsers.add_parser('definition',
                                            help='show a model definition ')
    def_subparser.set_defaults(func=do_show_definition)
    def_subparser.add_argument('model',
                               nargs='+',
                               help='the family and name(s) of a model(s) eg: TXSS T6SS T4SS or TFF/bacterial T2SS')
    def_subparser.add_argument('--models-dir',
                               help='the path to the alternative root directory containing packages instead to the '
                                    'canonical locations')
    ########
    # init #
    ########
    init_subparser = subparsers.add_parser('init',
                                           help='Create a template for a new data package '
                                                '(REQUIRE git/GitPython installation)')
    init_subparser.set_defaults(func=do_init_package)
    init_subparser.add_argument('--model-package',
                                required=True,
                                help='The name of the model data package.')
    init_subparser.add_argument('--maintainer',
                                required=True,
                                help='The name of the model package maintainer.')
    init_subparser.add_argument('--email',
                                required=True,
                                help='The email of the model package maintainer.')
    init_subparser.add_argument('--authors',
                                required=True,
                                help="The authors of the model package. Could be different that the maintainer."
                                     "Could be several persons. Surround the names by quotes 'John Doe, Richard Miles'")
    init_subparser.add_argument('--license',
                                choices=['cc-by', 'cc-by-sa', 'cc-by-nc', 'cc-by-nc-sa', 'cc-by-nc-nd'],
                                help="""The license under this work will be released.
if the license you choice is not in the list, you can do it manually
by adding the license file in package and add suitable headers in model definitions.""")
    init_subparser.add_argument('--holders',
                                help="The holders of the copyright")
    init_subparser.add_argument('--desc',
                                help="A short description (one line) of the package")
    init_subparser.add_argument('--models-dir',
                                help='The path of an alternative models directory '
                                     'by default the package will be created here.' )

    return parser


def cmd_name(args: argparse.Namespace) -> str:
    """
    Return the name of the command being executed
    (scriptname + operation).

    Example
        msl_data uninstall

    :param args: the arguments passed on the command line
    """
    assert 'func' in args
    func_name = args.func.__name__.replace('do_', '')
    return f"{args.tool_name} {func_name}"


def init_logger(level: typing.Literal['NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] | int = 'INFO',
                out: bool = True) -> logging.Logger:
    """

    :param level: The logger threshold could be a positive int or string
                  among: 'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'
    :param out: if the log message must be displayed
    :return: logger
    """

    logger = colorlog.getLogger('macsydata')
    handlers = []
    if out:
        stdout_handler = colorlog.StreamHandler(sys.stderr)
        if level <= logging.DEBUG:
            msg_formatter = "%(log_color)s%(levelname)-8s : %(module)s: L %(lineno)d :%(reset)s %(message)s"
        else:
            msg_formatter = "%(log_color)s%(message)s"
        stdout_formatter = colorlog.ColoredFormatter(msg_formatter,
                                                     datefmt=None,
                                                     reset=True,
                                                     log_colors={
                                                         'DEBUG': 'cyan',
                                                         'INFO': 'green',
                                                         'WARNING': 'yellow',
                                                         'ERROR': 'red',
                                                         'CRITICAL': 'bold_red',
                                                     },
                                                     secondary_log_colors={},
                                                     style='%'
                                                     )
        stdout_handler.setFormatter(stdout_formatter)
        logger.addHandler(stdout_handler)
        handlers.append(stdout_handler)
    else:
        null_handler = logging.NullHandler()
        logger.addHandler(null_handler)
        handlers.append(null_handler)
    if isinstance(level, str):
        level = getattr(logging, level)
    logger.setLevel(level)
    return logger


def verbosity_to_log_level(verbosity: int) -> int:
    """
    transform the number of -v option in loglevel
    :param verbosity: number of -v option on the command line
    :return: an int corresponding to a logging level
    """
    level = max((logging.INFO - (10 * verbosity), 1))
    return level


def main(args: list[str] = None,
         header:str = _cmde_line_header(),
         version=get_version_message(tool_name='msl_data'),
         package_name:str = 'macsylib',
         tool_name='msl_data') -> None:
    """
    Main entry point.

    :param args: the arguments passed on the command line (before parsing)
    :param header: the header of console scriot
    :param package_name: the name of the higher package that embed the macsylib (eg 'macsyfinder')
    :param tool_name: the name of this tool as it appear in pyproject.toml
    """
    global _log
    args = sys.argv[1:] if args is None else args
    parser = build_arg_parser(header, version, package_name=package_name, tool_name=tool_name)
    parsed_args = parser.parse_args(args)
    log_level = verbosity_to_log_level(parsed_args.verbose)
    # set logger for module 'package'
    macsylib.init_logger()
    macsylib.logger_set_level(level=log_level)
    # set logger for this script
    _log = init_logger(log_level)

    if 'func' in parsed_args:
        parsed_args.func(parsed_args)
        _log.debug(f"'{cmd_name(parsed_args)}' command completed successfully.")
    else:
        # macsydata command is run without any subcommand
        parser.print_help()


if __name__ == "__main__":
    main()
