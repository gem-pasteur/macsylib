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

import subprocess
from tests import MacsyTest


class Test_msl_data(MacsyTest):

    def test_help(self):

        expected_output = r"""usage: msl_data [-h] [-v] [--version]
                {available,download,install,uninstall,search,info,list,freeze,cite,help,check,show,definition,init} ...

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

positional arguments:
  {available,download,install,uninstall,search,info,list,freeze,cite,help,check,show,definition,init}
    available           List Models available on macsy-models
    download            Download model packages.
    install             Install Model packages.
    uninstall           Uninstall packages.
    search              Discover new packages.
    info                Show information about packages.
    list                List installed packages.
    freeze              List installed models in requirements format.
    cite                How to cite a package.
    help                get online documentation.
    check               check if the directory is ready to be publish as data
                        package
    show                show the structure of model package
    definition          show a model definition
    init                Create a template for a new data package (REQUIRE
                        git/GitPython installation)

options:
  -h, --help            show this help message and exit
  -v, --verbose         Give more output.
  --version             show program's version number and exit

For more details, visit the MacSyLib website and see the MacSyLib documentation.
"""

        p = subprocess.run("msl_data --help", shell=True, check=True, capture_output=True, text=True, encoding='utf8')
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stdout, expected_output)


class Test_msl_profile(MacsyTest):

    def test_help(self):

        expected_output = r"""usage: msl_profile [-h] [--coverage-profile COVERAGE_PROFILE]
                   [--i-evalue-sel I_EVALUE_SEL]
                   [--best-hits {score,i_eval,profile_coverage}] [-p PATTERN]
                   [-o OUT] [--index-dir INDEX_DIR] [-f] [-V] [-v] [--mute]
                   previous_run

     *            *               *                   * *
            *               *   *   *  *    **           
  **     *    *   *  *     *                    *        
            *       _   *             **    __ _ _     *         
      _ __ ___  ___| |     _ __  _ __ ___  / _(_) | ___          
     | '_ ` _ \/ __| |    | '_ \| '__/ _ \| |_| | |/ _ \       
     | | | | | \__ \ |    | |_) | | | (_) |  _| | |  __/
     |_| |_| |_|___/_|____| .__/|_|  \___/|_| |_|_|\___|
           *         |_____|_|        *                  *
        *   * *     *   **         *   *  *           *
  *      *         *        *    *              *        
             *                           *  *           * 

msl_profile - MacSyLib profile helper tool

positional arguments:
  previous_run          The path to a macsylib results directory.

options:
  -h, --help            show this help message and exit
  --coverage-profile COVERAGE_PROFILE
                        Minimal profile coverage required for the hit
                        alignment with the profile to allow the hit selection
                        for systems detection. (default no threshold)
  --i-evalue-sel I_EVALUE_SEL
                        Maximal independent e-value for Hmmer hits to be
                        selected for systems detection. (default: no selection
                        based on i-evalue)
  --best-hits {score,i_eval,profile_coverage}
                        If several hits match the same replicon, same gene.
                        Select only the best one (based on best 'score' or
                        'i_evalue' or 'profile_coverage')
  -p, --pattern PATTERN
                        pattern to filter the hmm files to analyse.
  -o, --out OUT         the path to a file to write results.
  --index-dir INDEX_DIR
                        Specifies the path to a directory to store/read the
                        sequence index when the sequence-db dir is not
                        writable.
  -f, --force           force to write output even the file already exists
                        (overwrite it).
  -V, --version         show program's version number and exit
  -v, --verbosity       Increases the verbosity level. There are 4 levels:
                        Error messages (default), Warning (-v), Info (-vv) and
                        Debug.(-vvv)
  --mute                Mute the log on stdout. (continue to log on
                        macsylib.log) (default: False)

For more details, visit the MacSyLib website and see the MacSyLib documentation.
"""
        p = subprocess.run("msl_profile --help", shell=True, check=True, capture_output=True, text=True, encoding='utf8')
        self.assertEqual(p.returncode, 0)
        self.assertEqual(p.stdout, expected_output)
