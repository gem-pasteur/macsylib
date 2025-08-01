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


import sys
import os
import glob
import argparse
from itertools import groupby
from dataclasses import dataclass
from textwrap import dedent
import logging
import typing

import colorlog

import macsylib
from macsylib.config import MacsyDefaults, Config
from macsylib.database import Indexes
from macsylib.hit import get_best_hits, CoreHit
from macsylib.registries import split_def_name
from macsylib.utils import get_replicon_names
from macsylib.metadata import Metadata

# _log is set in main func
_log = None


def get_version_message(tool_name:str = 'msl_profile', data_mgr: str = 'msl_data') -> str:
    """
    :param tool_name: The name of the high level tool
    :return: the long description of the macsylib version
    """
    version = macsylib.__version__
    commit = macsylib.__commit__
    vers_msg = f"""{tool_name} {version} {commit}
Python {sys.version}

MacSyLib is distributed under the terms of the GNU General Public License (GPLv3).
See the COPYING file for details.

If you use this software please cite:
{macsylib.__citation__}
and don't forget to cite models used:
{data_mgr} cite <model>
"""
    return vers_msg


def get_profile_len(path: str) -> int:
    """
    Parse the HMM profile to extract the length and the presence of GA bit threshold

    :param path: The path to the hmm profile used to produce the hmm search output to analyse
    :return: the length, presence of ga bit threshold
    """
    with open(path) as file:
        for line in file:
            if line.startswith("LENG"):
                length = int(line.split()[1])
                break
    return length


def get_gene_name(path: str, suffix: str) -> str:
    """

    :param path: The path to the hmm output to analyse
    :param suffix: the suffix of the hmm output file
    :return: the name of the analysed gene
    """
    file_name = os.path.basename(path)
    gene_name = file_name.replace(suffix, '')
    return gene_name


@dataclass
class LightHit:
    """
    Handle hmm hits
    """

    gene_name: str
    id: str
    seq_length: int
    replicon_name: str
    position: int
    i_eval: float
    score: float
    profile_coverage: float
    sequence_coverage: float
    begin_match: int
    end_match: int


    def __str__(self) -> str:
        return f"{self.id}\t{self.replicon_name}\t{self.position:d}\t{self.seq_length:d}\t{self.gene_name}\t" \
               f"{self.i_eval:.3e}\t{self.score:.3f}\t{self.profile_coverage:.3f}\t" \
               f"{self.sequence_coverage:.3f}\t{self.begin_match:d}\t{self.end_match:d}"


class HmmProfile:
    """
    Handle the HMM output files
    """

    def __init__(self, gene_name: str, gene_profile_lg: int, hmmer_output: str, cfg: Config):
        """
        :param gene_name: the name of the gene corresponding to the profile search reported here
        :param hmmer_output: The path to the raw Hmmer output file
        :param cfg: the configuration object
        """
        self.gene_name = gene_name
        self._hmmer_raw_out = hmmer_output
        self.gene_profile_lg = gene_profile_lg
        self.cfg = cfg


    def parse(self) -> list[LightHit]:
        """
        parse a hmm output file and extract all hits and do some basic computation (coverage profile)

        :return: The list of extracted hits
        """
        all_hits = []
        my_db = self._build_my_db(self._hmmer_raw_out)
        self._fill_my_db(my_db)

        with open(self._hmmer_raw_out, 'r') as hmm_out:
            i_evalue_sel = self.cfg.i_evalue_sel()
            coverage_threshold = self.cfg.coverage_profile()
            hmm_hits = (x[1] for x in groupby(hmm_out, self._hit_start))
            # drop summary
            next(hmm_hits)
            for hmm_hit in hmm_hits:
                hit_id = self._parse_hmm_header(hmm_hit)
                seq_lg, position_hit = my_db[hit_id]

                replicon_name = self._get_replicon_name(hit_id)
                body = next(hmm_hits)
                l_hit = self._parse_hmm_body(hit_id, self.gene_profile_lg, seq_lg,
                                             coverage_threshold, replicon_name,
                                             position_hit, i_evalue_sel, body)
                all_hits += l_hit
            hits = sorted(all_hits, key=lambda h: - h.score)
        return hits


    def _build_my_db(self, hmm_output: str) -> dict[str: None]:
        """
        Build the keys of a dictionary object to store sequence identifiers of hits.

        :param hmm_output: the path to the hmmsearch output to parse.
        :return: a dictionary containing a key for each sequence id of the hits
        """
        db = {}
        with open(hmm_output) as hmm_file:
            hits = (x[1] for x in groupby(hmm_file, self._hit_start) if x[0])
            for hit in hits:
                db[self._parse_hmm_header(hit)] = None
        return db


    def _fill_my_db(self, db: dict[str: tuple[int, int]]) -> None:
        """
        Fill the dictionary with information on the matched sequences

        :param db: the database containing all sequence id of the hits.
        """
        idx = Indexes(self.cfg)
        idx.build()
        for seqid, length, rank in idx:
            if seqid in db:
                db[seqid] = (length, rank)


    def _get_replicon_name(self, hit_id: str) -> str:
        db_type = self.cfg.db_type()
        if db_type == 'gembase':
            *replicon_name, seq_name = hit_id.split('_')
            replicon_name = "_".join(replicon_name)
        else:
            replicon_name = get_replicon_names(self.cfg.sequence_db(), db_type)[0]
        return replicon_name


    def _hit_start(self, line: str) -> bool:
        """
        :param line: the line to parse
        :return: True if it's the beginning of a new hit in Hmmer raw output files.
         False otherwise
        """
        return line.startswith(">>")


    def _parse_hmm_header(self, h_grp: str) -> str:
        """
        :param h_grp: the sequence of string return by groupby function representing the header of a hit
        :returns: the sequence identifier from a set of lines that corresponds to a single hit
        """
        for line in h_grp:
            hit_id = line.split()[1]
        return hit_id


    def _parse_hmm_body(self, hit_id: str, gene_profile_lg: int, seq_lg: int,
                        coverage_threshold:float, replicon_name: str,
                        position_hit: int, i_evalue_sel: float, b_grp: list[list[str]]) -> list[CoreHit]:
        """
        Parse the raw Hmmer output to extract the hits, and filter them with threshold criteria selected
        ("coverage_profile" and "i_evalue_select" command-line parameters)

        :param hit_id: the sequence identifier
        :param gene_profile_lg: the length of the profile matched
        :param seq_lg: the length of the sequence
        :param coverage_threshold: the minimal coverage of the profile to be reached in the Hmmer alignment
                                        for hit selection.
        :param replicon_name: the identifier of the replicon
        :param position_hit: the rank of the sequence matched in the input dataset file
        :param i_evalue_sel: the maximal i-evalue (independent evalue) for hit selection
        :param b_grp: the Hmmer output lines to deal with (grouped by hit)
        :returns: a sequence of hits
        """
        first_line = next(b_grp)
        if not first_line.startswith('   #    score'):
            return []
        else:
            hits = []
            for line in b_grp:
                if line[0] == '\n':
                    return hits
                elif line.startswith(" ---   ------ ----- --------"):
                    pass
                else:
                    fields = line.split()
                    try:
                        # fields[2] = score
                        # fields[5] = i_evalue
                        # fields[6] = hmmfrom
                        # fields[7] = hmm to
                        # fields[9] = alifrom
                        # fields[10] = ali to
                        if len(fields) > 1:
                            _, _, score, _, _, i_evalue, hmm_from, hmm_to, _, ali_from, ali_to, *_ = fields
                            score = float(score)
                            i_evalue = float(i_evalue)
                            hmm_from = int(hmm_from)
                            hmm_to = int(hmm_to)
                            ali_from = int(ali_from)
                            ali_to = int(ali_to)
                            if i_evalue <= i_evalue_sel:
                                _log.debug(f"{hit_id} i_evalue {i_evalue} <= {i_evalue_sel} i_evalue_sel")
                                cov_profile = (hmm_to - hmm_from + 1) / gene_profile_lg
                                begin = int(fields[9])
                                end = int(fields[10])
                                cov_gene = (end - begin + 1) / seq_lg  # To be added in Gene: sequence_length
                                if cov_profile >= coverage_threshold:
                                    hits.append(LightHit(self.gene_name, hit_id, seq_lg, replicon_name, position_hit,
                                                         i_evalue, score, cov_profile, cov_gene, ali_from, ali_to))
                                    _log.debug(f"{hit_id} cov_profile {cov_profile} >= {coverage_threshold} "
                                               f"coverage_threshold: add hit")

                                else:
                                    _log.debug(f"{hit_id} cov_profile {cov_profile} < {coverage_threshold} "
                                               f"coverage_threshold: skip hit")
                            else:
                                _log.debug(f"{hit_id} i_evalue {i_evalue} > {i_evalue_sel} i_evalue_sel : skip hit")
                    except ValueError as err:
                        msg = f"Invalid line to parse :{line}:{err}"
                        _log.debug(msg)
                        raise ValueError(msg) from err


def result_header(cmd: list[str], model: str, model_vers: str, tool_name='msl_profile') -> str:
    """

    :param cmd: the command use dto launch this analyse
    :model: The name of model family
    :model_vers: The version of the model
    :return: The header of the result file
    """
    header = f"""# {tool_name} {macsylib.__version__}
# models: {model}-{model_vers}
# {tool_name} {' '.join(cmd)}
hit_id\treplicon_name\tposition_hit\thit_sequence_length\tgene_name\ti_eval\tscore\tprofile_coverage\tsequence_coverage\tbegin\tend"""
    return header


def init_logger(level: typing.Literal['NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'] | int ='INFO',
                out: bool = True):
    """

    :param level: The logger threshold could be a positive int or string
                  among: 'CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'
    :param out: if the log message must be displayed
    :return: logger
    """
    logger = colorlog.getLogger('macsyprofile')
    if isinstance(level, str):
        level = getattr(logging, level)
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
    else:
        null_handler = logging.NullHandler()
        logger.addHandler(null_handler)
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

def _cmde_line_header():
    return dedent(r'''
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
    ''')


def parse_args(header:str, args: list[str], package_name='macsylib', tool_name: str = 'msl_profile') -> argparse.Namespace:
    """
    Build argument parser.

    :param header: the header of console scriot
    :param args: The arguments provided on the command line
    :param package_name: the name of the higher package that embed the macsylib (eg 'macsyfinder')
    :param tool_name: the name of this tool as it appear in pyproject.toml
    :return: The arguments parsed
    """
    msl_def = MacsyDefaults(pack_name=package_name)
    parser = argparse.ArgumentParser(
        epilog="For more details, visit the MacSyLib website and see the MacSyLib documentation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=header)

    parser.add_argument('previous_run',
                        action='store',
                        help=f'The path to a {package_name} results directory.'
                        )
    parser.add_argument('--coverage-profile',
                        action='store',
                        default=-1.,
                        type=float,
                        help="""Minimal profile coverage required for the hit alignment  with the profile to allow
the hit selection for systems detection. (default no threshold)"""
                        )
    parser.add_argument('--i-evalue-sel',
                        action='store',
                        type=float,
                        default=1.0e9,
                        help="""Maximal independent e-value for Hmmer hits to be selected for systems detection.
(default: no selection based on i-evalue)""")
    parser.add_argument('--best-hits',
                        choices=['score', 'i_eval', 'profile_coverage'],
                        action='store',
                        default=None,
                        help="If several hits match the same replicon, same gene. "
                             "Select only the best one (based on best 'score' or 'i_evalue' or 'profile_coverage')")
    parser.add_argument('-p', '--pattern',
                        action='store',
                        default='*',
                        help="pattern to filter the hmm files to analyse."
                        )
    parser.add_argument('-o', '--out',
                        action='store',
                        default=None,
                        help="the path to a file to write results.")
    parser.add_argument('--index-dir',
                        action='store',
                        default=None,
                        help="Specifies the path to a directory to store/read the sequence index when "
                             "the sequence-db dir is not writable.")

    parser.add_argument('-f', '--force',
                        action='store_true',
                        default=False,
                        help='force to write output even the file already exists (overwrite it).')
    parser.add_argument('-V', "--version",
                        action="version",
                        version=get_version_message())
    parser.add_argument("-v", "--verbosity",
                        action="count",
                        default=0,
                        help="""Increases the verbosity level. There are 4 levels:
Error messages (default), Warning (-v), Info (-vv) and Debug.(-vvv)""")
    parser.add_argument("--mute",
                        action="store_true",
                        default=False,
                        help=f"""Mute the log on stdout.
(continue to log on {package_name}.log)
(default: {msl_def['mute']})""")

    parsed_args = parser.parse_args(args)

    return parsed_args


def main(args: list[str] | None = None,
         header: str = _cmde_line_header(),
         package_name: str ='macsylib',
         tool_name: str = 'msl_profile',
         log_level: str | int | None = None) -> None:
    """
    main entry point

    :param args: the arguments passed on the command line without the program name
    :param package_name: the name of the higher package that embed the macsylib (eg 'macsyfinder')
    :param tool_name: the name of this tool as it appear in pyproject.toml
    :param log_level: the output verbosity
    """
    global _log
    args = sys.argv[1:] if args is None else args
    parsed_args = parse_args(header, args, package_name=package_name, tool_name=tool_name)

    if log_level is None:
        log_level = verbosity_to_log_level(parsed_args.verbosity)
    _log = init_logger(log_level, out=(not parsed_args.mute))

    if not os.path.exists(parsed_args.previous_run):
        _log.critical(f"{parsed_args.previous_run}: No such directory.")
        sys.tracebacklimit = 0
        raise FileNotFoundError() from None
    elif not os.path.isdir(parsed_args.previous_run):
        _log.critical(f"{parsed_args.previous_run} is not a directory.")
        sys.tracebacklimit = 0
        raise ValueError() from None

    defaults = MacsyDefaults(i_evalue_sel=1.0e9, coverage_profile=-1.0, pack_name=package_name)
    cfg = Config(defaults, parsed_args)

    msf_run_path = cfg.previous_run()
    hmmer_results = os.path.join(msf_run_path, cfg.hmmer_dir())
    hmm_suffix = cfg.res_search_suffix()
    profile_suffix = cfg.profile_suffix()
    if parsed_args.out:
        profile_report_path = os.path.normpath(parsed_args.out)
        dirname = os.path.normpath(os.path.dirname(parsed_args.out))
        if not os.path.exists(dirname):
            _log.critical(f"The {dirname} directory is not writable")
            sys.tracebacklimit = 0
            raise ValueError() from None
    else:
        profile_report_path = os.path.join(cfg.previous_run(), 'hmm_coverage.tsv')

    if os.path.exists(profile_report_path) and not parsed_args.force:
        _log.critical(f"The file {profile_report_path} already exists. "
                      f"Remove it or specify a new output name --out or use --force option")
        sys.tracebacklimit = 0
        raise ValueError() from None

    hmmer_files = sorted(glob.glob(os.path.join(hmmer_results, f"{parsed_args.pattern}{hmm_suffix}")))
    try:
        # models can be a path like TXSScan/bacteria/diderm
        model_familly_name = split_def_name(cfg.models()[0])[0]
        model_dir = [p for p in [os.path.join(p, model_familly_name) for p in cfg.models_dir()] if os.path.exists(p)][-1]

        metadata_path = os.path.join(model_dir, Metadata.name)
        metadata = Metadata.load(metadata_path)
        model_vers = metadata.vers
        profiles_dir = os.path.join(model_dir, 'profiles')
    except IndexError:
        _log.critical(f"Cannot find models in conf file {msf_run_path}. "
                      f"May be these results have been generated with an old version of {tool_name}.")
        sys.tracebacklimit = 10
        raise ValueError() from None

    _log.debug(f"hmmer_files: {hmmer_files}")
    all_hits = []
    with open(profile_report_path, 'w') as prof_out:
        print(result_header(args, model_familly_name, model_vers, tool_name=tool_name), file=prof_out)
        for hmmer_out_path in hmmer_files:
            _log.info(f"parsing {hmmer_out_path}")
            gene_name = get_gene_name(hmmer_out_path, hmm_suffix)
            profile_path = os.path.join(profiles_dir, f"{gene_name}{profile_suffix}")
            gene_profile_len = get_profile_len(profile_path)
            hmm = HmmProfile(gene_name, gene_profile_len, hmmer_out_path, cfg)
            hits = hmm.parse()
            all_hits += hits
        if len(all_hits) > 0:
            if parsed_args.best_hits:
                # It's important to keep this sorting to have in last all_hits version
                # the hits with the same replicon_name and position sorted by score
                # the best score in first
                hits_by_replicon = {}
                for hit in all_hits:
                    if hit.replicon_name in hits_by_replicon:
                        hits_by_replicon[hit.replicon_name].append(hit)
                    else:
                        hits_by_replicon[hit.replicon_name] = [hit]
                all_hits = []
                for rep_name in hits_by_replicon:
                    hits_by_replicon[rep_name] = get_best_hits(hits_by_replicon[rep_name], key=parsed_args.best_hits)
                    all_hits += sorted(hits_by_replicon[rep_name], key=lambda h: h.position)

            all_hits = sorted(all_hits, key=lambda h: (h.gene_name, h.replicon_name, h.position, h.score))
            _log.info(f"found {len(all_hits)} hits")
            for hit in all_hits:
                print(hit, file=prof_out)
            _log.info(f"result is in '{profile_report_path}'")
        else:
            _log.info("No hit found")


if __name__ == '__main__':
    main()
