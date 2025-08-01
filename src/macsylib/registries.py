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
from __future__ import annotations  # to allow to use a Type in type hint before it's definition

import os
import colorlog

from .metadata import Metadata

"""
Manage the Models locations: Profiles and definitions
"""

_log = colorlog.getLogger(__name__)

_SEPARATOR = '/'


def split_def_name(fqn: str) -> list[str]:
    """
    :param fqn: the fully qualified de name of a DefinitionLocation object
           the follow the schema model_name/<def_name>*/def_name
           for instance CRISPR-Cas/typing/cas
    :return: the list of components of the def path
             ['CRISPR-Cas', 'typing', 'cas']
    """
    split = fqn.split(_SEPARATOR)
    if split[0] == '':  # '/foo/bar'
        split = split[1:]
    if split[-1] == '':
        split = split[:-1]  # 'foo/bar/'
    return split


def join_def_path(*args: str) -> str:
    """
    join different elements of the definition path
    :param str args: the elements of the definition path, each element must be a string
    :return: The return value is the concatenation of different elements of args with one
    separator
    """
    return _SEPARATOR.join(args)


def scan_models_dir(models_dir: str, profile_suffix: str = ".hmm", relative_path: bool = False) -> list[ModelLocation]:
    """

    :param str models_dir: The path to the directory where are stored the models
    :param profile_suffix: the suffix of the hmm profiles
    :param relative_path: True if models_dir is relative false otherwise
    :return: the list of models in models_dir
    :rtype: [:class:`macsylib.registries.ModelLocation`, ...]
    """
    models = []
    for models_type in os.listdir(models_dir):
        model_path = os.path.join(models_dir, models_type)
        if os.path.isdir(model_path):
            new_model = ModelLocation(path=model_path,
                                      profile_suffix=profile_suffix,
                                      relative_path=relative_path)
            models.append(new_model)
    return models


class ModelRegistry:
    """
    scan canonical directories to register the different models available in global <program name>
    share data location (depending on installation /usr/share/data/models) or can be
    overloaded with the location specify in the <program name | 'macsylib'> configuration (either in config file or command line)
    """

    def __init__(self) -> None:
        self._registry = {}


    def add(self, model_loc: ModelLocation) -> None:
        """
        :param model_loc: the model location to add to the registry
        """
        self._registry[model_loc.name] = model_loc


    def models(self) -> list[ModelLocation]:
        """
        :returns: the list of models
        """
        return sorted(list(self._registry.values()))  # level 0 like TXSS ou CRISPR_Cas


    def __getitem__(self, name: str) -> ModelLocation:
        """
        :param name:
        :returns: the model corresponding to name.
        :raise KeyError: if name does not match any ModelLocation registered.
        """
        if name in self._registry:
            return self._registry[name]
        else:
            raise KeyError(f"No such model definition: '{name}'")


    def __str__(self) -> str:
        rep = ''

        def model_to_str(model, pad):
            if model.subdefinitions:
                model_s = f"{' ' * pad}/{model.name}\n"
                pad = pad + len(model.name) + 1
                for submodel in sorted(model.subdefinitions.values()):
                    model_s += model_to_str(submodel, pad)
            else:
                model_s = f"{' ' * pad}/{model.name}\n"
            return model_s

        for model in sorted(self.models()):
            rep += model.name + '\n'
            pad = len(model.name) + 1
            for definition in model.get_definitions():
                rep += model_to_str(definition, pad)
        return rep


class ModelLocation:
    """
    Handle where are store Models. Models are organized in families and subfamilies.
    each family match to a ModelLocation. a ModelLocation contains the path toward the definitions
    and the paths to corresponding to the profiles.
    """

    def __init__(self, path: str = None, profile_suffix: str = '.hmm', relative_path: bool = False) -> None:
        """
        :param path: if it's an installed model, path is the absolute path to a model family.
        :param profile_suffix: the suffix of hmm files
        :param relative_path: True if you want to work with relative path, False to work with absolute path.
        """
        self._path = path
        self.name = os.path.basename(path)
        self._version = self._get_version(path)
        profile_dir = os.path.join(path, 'profiles')
        self._profiles = self._scan_profiles(profile_dir,
                                             profile_suffix=profile_suffix,
                                             relative_path=relative_path)

        self._definitions = {}
        def_dir = os.path.join(self._path, 'definitions')
        for definition in os.listdir(def_dir):
            definition_path = os.path.join(def_dir, definition)
            new_def = self._scan_definitions(def_path=definition_path)

            if new_def:  # _scan_definitions can return None if a dir is empty
                self._definitions[new_def.name] = new_def


    def _scan_definitions(self, parent_def: DefinitionLocation = None, def_path: str = None) -> DefinitionLocation:
        """
        Scan recursively the definitions tree on the file model and store
        them.

        :param parent_def: the current model definition to add new submodel location
        :param def_path: the absolute path to analyse
        :returns: a definition location
        """
        if os.path.isfile(def_path):
            base, ext = os.path.splitext(def_path)
            if ext == '.xml':
                name = os.path.basename(base)
                if parent_def is None:
                    # it's the root of definitons tree
                    fqn = f"{self.name}{_SEPARATOR}{name}"
                else:
                    fqn = f"{parent_def.fqn}{_SEPARATOR}{name}"
                new_def = DefinitionLocation(name=name,
                                             fqn=fqn,
                                             path=def_path)
                return new_def
        elif os.path.isdir(def_path):
            name = os.path.basename(def_path)
            if parent_def is None:
                # it's the root of definitons tree
                fqn = f"{self.name}{_SEPARATOR}{name}"
            else:
                fqn = f"{parent_def.fqn}{_SEPARATOR}{name}"
            new_def = DefinitionLocation(name=name,
                                         fqn=fqn,
                                         path=def_path)
            for model in os.listdir(def_path):
                subdef = self._scan_definitions(parent_def=new_def, def_path=os.path.join(new_def.path, model))
                if subdef is not None:
                    new_def.add_subdefinition(subdef)
            return new_def


    def _scan_profiles(self, path: str, profile_suffix: str = '.hmm', relative_path: bool = False) -> dict[str: str]:
        """
        Store all hmm profiles associated to the model

        :param path: the path to a directory containing hmm profiles
        :param profile_suffix: the extension of hmm profile file
        :param relative_path: True if the path is relative, False otherwise.
        :return: all profiles found in the path
        """
        all_profiles = {}
        for profile in os.listdir(path):
            profile_path = os.path.join(path, profile)
            compressed_suffix = f"{profile_suffix}.gz"
            if os.path.isfile(profile_path):
                if profile.endswith(profile_suffix):
                    base, _ = profile.rsplit('.', maxsplit=1)
                elif profile.endswith(compressed_suffix):
                    base, *_ = profile.rsplit('.', maxsplit=2)
                    # cannot use this solution for all cases because some profile have name like PF05930.13.hmm
                else:
                    continue
                all_profiles[base] = profile_path if relative_path else os.path.abspath(profile_path)
        return all_profiles


    def __lt__(self, other: ModelLocation) -> bool:
        return self.name < other.name


    def __gt__(self, other: ModelLocation) -> bool:
        return self.name > other.name


    def __eq__(self, other: ModelLocation) -> bool:
        return (self._path, self.name, self._profiles, self._definitions ==
                other.path, other.name, other._profiles, other._definitions)

    @property
    def path(self) -> str:
        return self._path


    def _get_version(self, path: str) -> str | None:
        metadata_path = os.path.join(path, "metadata.yml")
        try:
            metadata = Metadata.load(metadata_path)
            return metadata.vers
        except FileNotFoundError:
            _log.warning(f"The models package '{self.name}' is not versioned contact the package manager to fix it.")
            return None


    @property
    def version(self) -> str:
        """

        :return: The version of the models
        """
        return self._version


    def get_definition(self, fqn: str) -> DefinitionLocation:
        """
        :param fqn: the fully qualified name of the definition to retrieve.
                     it's complete path without extension.
                     for instance for a file with path like this:
                     models/TXSS/defintions/T3SS.xml
                     the name is: TXSS/T3SS
                     for
                     models/CRISPR-Cas/definitions/typing/CAS.xml:
                     the name is CRISPR-Cas/typing/CAS
        :returns: the definition corresponding to the given name.
        :raise: valueError if fqn does not match with any model definition.
        """
        name_path = [item for item in fqn.split(_SEPARATOR) if item]
        def_full_name = name_path[1:]
        defs = self._definitions
        definition = None
        for level in def_full_name:
            if level in defs:
                definition = defs[level]
                defs = definition.subdefinitions
            else:
                raise ValueError(f"{level} does not match with any definitions")
        return definition


    def get_all_definitions(self, root_def_name: str = None) -> list[DefinitionLocation]:
        """
        :name root_def_name: The name of the root definition to get sub definitions.
                        If root_def is None, return all definitions for this set of models
        :return: the list of definitions or subdefinitions if root_def is specified for this model.
        :raise ValueError: if root_def_name does not match with any definitions
        """
        if root_def_name is None:
            all_defs = [def_loc for all_loc in self._definitions.values() for def_loc in all_loc.all()]
        else:
            root_def_name = root_def_name.rstrip(_SEPARATOR)
            root_def = self.get_definition(root_def_name)
            if root_def is not None:
                all_defs = root_def.all()
            else:
                raise ValueError(f"root_def_name {root_def_name} does not match with any definitions")
        return all_defs


    def get_definitions(self) -> list[DefinitionLocation]:
        """
        :return: the list of the definitions of this modelLocation.
                 It returns the 1rst level only (not recursive).
                 For recursive explorations see :meth:`macsylib.registries.ModelLocation.get_all_definitions`
        """
        if self._definitions is not None:
            return sorted(list(self._definitions.values()))
        else:
            return []


    def get_profile(self, name: str) -> str:
        """
        :param name: the name of the profile to retrieve (without extension).
        :returns: the absolute path of the hmm profile.
        :raise: KeyError if name does not match with any profiles.
        """
        return self._profiles[name]


    def get_profiles_names(self) -> list[str]:
        """
        :return: The list of profiles name (without extension) for this model location
        """
        return list(self._profiles.keys())


    def __str__(self) -> str:
        return self.name


class MetaDefLoc(type):

    @property
    def separator(cls) -> str:
        return cls._SEPARATOR


class DefinitionLocation(dict, metaclass=MetaDefLoc):
    """
    Manage where definitions are stored. a Model is a xml definition and associated profiles.
    It has 3 attributes

    name: the fully qualified definitions name like TXSS/T3SS or CRISPR-cas/Typing/Cas
    path: the absolute path to the definitions or set of definitions
    subdefinitions: the subdefinitions if it exists
    """

    _SEPARATOR = '/'

    def __init__(self,
                 name: str | None = None,
                 fqn: str | None = None,
                 subdefinitions: DefinitionLocation | None = None,
                 path: str | None = None) -> None:
        super().__init__(name=name, fqn=fqn, subdefinitions=subdefinitions, path=path)
        self.__dict__ = self  # allow to use dot notation to access to property here name or subdefinitions ...


    @classmethod
    def split_fqn(cls, fqn: str) -> list[str]:
        """
        :param fqn: the fully qualified name of a definition
        :return: each member of the fully qn in list.
        """
        return [f for f in fqn.split(cls.separator) if f]


    @classmethod
    def root_name(cls, fqn: str) -> str:
        """
        :param str fqn: the fully qualified name of a definition
        :return: the root name of this definition (family name)
        """
        return cls.split_fqn(fqn)[0]


    @property
    def family_name(self) -> str:
        """
        :return: the models family name which is the name of the package
        """
        return self.__class__.root_name(self.fqn)


    def __hash__(self) -> int:
        return hash((self.fqn, self.path))


    def add_subdefinition(self, subdefinition: DefinitionLocation) -> None:
        """
        add new sub category of definitions to this definition

        :param subdefinition: the new definition to add as subdefinition.
        """
        if self.subdefinitions is None:
            self.subdefinitions = {}
        self.subdefinitions[subdefinition.name] = subdefinition


    def all(self) -> list[DefinitionLocation]:
        """
        :return: the definition and all recursively all subdefinitions
        """
        if not self.subdefinitions:
            return [self]
        else:
            all_leaf = []
            for definition in self.subdefinitions.values():
                for leaf in definition.all():
                    all_leaf.append(leaf)
            return all_leaf


    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: DefinitionLocation) -> bool:
        return self.fqn, self.path, self.subdefinitions == other.fqn, other.path, other.subdefinitions

    def __lt__(self, other: DefinitionLocation) -> bool:
        return self.fqn < other.fqn

    def __gt__(self, other: DefinitionLocation) -> bool:
        return self.fqn > other.fqn


_exclude = {'_exclude', 'annotations', 'os', 'colorlog', 'Metadata', '_log', '_SEPARATOR'}
__all__ = list(set(locals().keys()) - _exclude)