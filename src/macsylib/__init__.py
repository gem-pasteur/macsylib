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
MacSypy package contains mainly variable used in library as __version_
and functions to intialize the logger uses by entrypoints
"""
import logging
from time import strftime, localtime
import sys
import os
import subprocess

from typing import Literal


__version__ = f'{strftime("%Y%m%d", localtime())}.dev'


__citation__ = """Néron, Bertrand; Denise, Rémi; Coluzzi, Charles; Touchon, Marie; Rocha, Eduardo P.C.; Abby, Sophie S.
MacSyFinder v2: Improved modelling and search engine to identify molecular systems in genomes.
Peer Community Journal, Volume 3 (2023), article no. e28. doi : 10.24072/pcjournal.250.
https://peercommunityjournal.org/articles/10.24072/pcjournal.250/"""


def get_git_revision_short_hash() -> str:
    """
    :return: the git commit number (short version) or empty string if this not a git repository
    :rtype: str
    """
    try:
        short_hash = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'],
                                             cwd=os.path.dirname(os.path.abspath(__file__)),
                                             stderr=subprocess.DEVNULL
                                             )
        short_hash = str(short_hash, "utf-8").strip()
    except Exception:
        short_hash = ''
    return short_hash


# do not display the commit for the MSF tagged versions
__commit__ = f'{get_git_revision_short_hash()}' if 'dev' in __version__ else ''


def get_version_message(tool_name='MacSyLib') -> str:
    """
    :return: the long description of the macsylib version
    :rtype: str
    """
    msl_ver = __version__
    commit = __commit__
    vers_msg = f"""{tool_name} {msl_ver} {commit}
Python {sys.version}

MacSyLib is distributed under the terms of the GNU General Public License (GPLv3).
See the COPYING file for details.

If you use this software please cite:
{__citation__}
and don't forget to cite models used:
macsydata cite <model>
"""
    return vers_msg


def init_logger(name: str = 'macsylib', log_file: str = None, out: bool = True) -> list[logging.Handler]:
    """
    :param name: the name of the logger
    :param log_file: The path toward a file log
    :param out: True if the log are display on the screen, False otherwise.
    :return: the logger handlers
    """
    import logging
    import colorlog

    logger = colorlog.getLogger(name)
    handlers = []
    if out:
        stdout_handler = colorlog.StreamHandler(sys.stdout)
        stdout_formatter = colorlog.ColoredFormatter("%(log_color)s%(message)s",
                                                     datefmt=None,
                                                     reset=True,
                                                     log_colors={
                                                         'DEBUG':    'cyan',
                                                         'INFO':     'green',
                                                         'WARNING':  'yellow',
                                                         'ERROR':    'red',
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
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_formatter = logging.Formatter("%(levelname)-8s : %(message)s")
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        handlers.append(file_handler)
    logger.setLevel(logging.WARNING)
    return handlers


def logger_set_level(name: str = 'macsylib', level: Literal['NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] | int = 'INFO'):
    """
    Set the level and the formatter to the logger <name>

    :param name: the name of the logger
    :param level:
    :type level: str among (NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL) or a positive integer
    """
    # default value must be a string
    # cannot be logging.WARNING for instance
    # because setup import __init__ to get __version__
    # so logger_set_level is defined
    # if level is logging.WARNING
    # that mean that colorlog must be already installed
    # otherwise an error occured during pip install
    #  NameError: name 'colorlog' is not defined
    import logging
    import colorlog

    levels = {'NOTSET': logging.NOTSET,
              'DEBUG': logging.DEBUG,
              'INFO': logging.INFO,
              'WARNING': logging.WARNING,
              'ERROR': logging.ERROR,
              'CRITICAL': logging.CRITICAL,
              }
    if level in levels:
        level = levels[level]
    elif not isinstance(level, int) or level < 0:
        raise ValueError(f"Level must be {', '.join(levels.keys())} or a positive integer")

    logger = colorlog.getLogger(name)
    if level <= logging.DEBUG:
        stdout_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(levelname)-8s : %(module)s: L %(lineno)d :%(reset)s %(message)s",
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
        stdout_handler = logger.handlers[0]
        stdout_handler.setFormatter(stdout_formatter)

        if len(logger.handlers) > 1:
            file_formatter = logging.Formatter("%(levelname)-8s : %(module)s: L %(lineno)d : %(message)s")
            file_handler = logger.handlers[1]
            file_handler.setFormatter(file_formatter)

    logger.setLevel(level)
