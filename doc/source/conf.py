# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join('..', '..')))

from  macsylib import __version__ as msl_version

project = 'MacSyLib'
copyright = '2014-2025, Bertrand Néron, Sophie Abby'
author = 'Bertrand Néron, Sopphie Abby'
release = msl_version

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx.ext.autodoc',
              'sphinx.ext.doctest',
              'sphinx.ext.todo',
              'sphinx.ext.coverage',
              'sphinx.ext.ifconfig',
              'sphinx.ext.viewcode',
              'sphinx.ext.inheritance_diagram',
              'sphinx.ext.graphviz',]

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_show_sourcelink = False
# html_theme = 'alabaster'


html_static_path = ['_static']
html_context = {
    'github_user': 'gem-pasteur',
    'github_repo': 'macsylib'
}

# These paths are either relative to html_static_path
# or fully qualified paths (eg. https://...)
html_css_files = ['_css/custom.css']

