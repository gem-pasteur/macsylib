# MacSyLib

MacSyLib is a package to model and detect macromolecular systems, genetic pathways… by similarity search in prokaryotes datasets.

[![Open Source License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://opensource.org/licenses/GPL-3.0)
[![FAIR checklist badge](https://fairsoftwarechecklist.net/badge.svg)](https://fairsoftwarechecklist.net/v0.2?f=31&a=32113&i=32321&r=133)

## Citations

MacSyFinder v2:
Néron, Bertrand; Denise, Rémi; Coluzzi, Charles; Touchon, Marie; Rocha, Eduardo P.C.; Abby, Sophie S.
MacSyFinder v2: Improved modelling and search engine to identify molecular systems in genomes.
Peer Community Journal, Volume 3 (2023), article no. e28. doi : 10.24072/pcjournal.250.
https://peercommunityjournal.org/articles/10.24072/pcjournal.250/

## Licence:

MacSyPy is developed and released under [![Open Source License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://opensource.org/licenses/GPL-3.0)

## Installation

> [!IMPORTANT]
> MacSyFinder requires hmmer >= 3.1 (http://hmmer.org/).
> You need to install hmmer by yourself (except if you install macsyfinder via *conda/mamba*).
> If you are a modeler, you will need also `git`
> The other dependencies are managed by the python package manager *pip*.

### Installation from distribution

We encourage to install macsyfinder in a [virtualenv](https://virtualenv.pypa.io/en/latest/)

After creating a virtualenv dedicated to macsyfinder and activating it

    python3 -m venv my_project
    cd my_project
    source bin/activate

you can install macsylib as described below:

## Models installation

Models are no longer shipped along macsyfinder package. To install Models you can use `macsydata`.
*macsydata* allow to manage models stored in [macsy-models](https://github.com/macsy-models).
Below some most useful commands.

  * available: List Models available on macsy-models.
  * search: Discover new packages.
  * install: Install or upgarde packages.
  * uninstall: Uninstall packages.
  * cite: How to cite a package.
  * ...

For complete documentation see
[macsydata section on readthedoc](https://macsyfinder.readthedocs.io/en/latest/user_guide/installation.html#models-installation-with-macsydata)

For models not stored in macsy-models the commands *available*, *search*, *installation from remote* or *upgrade from remote*
are **NOT** available.

For models **Not** stored in *macsy-models*, you have to manage them semi-manually.
Download the archive (do not unarchive it), then use *macsydata* for the installation.

## Use MacSyLib

    import macsypy


## Contributing

We encourage contributions, bug report, enhancement ...

But before to do that, we encourage to read [the contributing guide](CONTRIBUTING.md).

## Contributors

[List of all people who participated in the macsyfinder project](CONTRIBUTORS.md).

## Note

The `setsid` binary in *utils* directory is used only for functional tests on macosx.
The binary has been build using the [setsid-macosx](https://github.com/tzvetkoff/setsid-macosx) project.
