# A lot of this was lifted from the official qtile repo.

# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
from unittest.mock import MagicMock


class Mock(MagicMock):
    # xcbq does a dir() on objects and pull stuff out of them and tries to sort
    # the result. MagicMock has a bunch of stuff that can't be sorted, so let's
    # like about dir().
    def __dir__(self):
        return []


MOCK_MODULES = [
    'libqtile.widget.wlan',
    'stravalib',
    'stravalib.model',
    'units',
    'qtile_extras.resources.stravadata.locations'
]
sys.modules.update((mod_name, Mock()) for mod_name in MOCK_MODULES if mod_name not in sys.modules)
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('../'))

# -- Project information -----------------------------------------------------

project = 'qtile-extras'
copyright = '2021, elParaguayo'
author = 'elParaguayo'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.autosectionlabel',
    'sphinx_qtile_extras'
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']


# A workaround for the responsive tables always having annoying scrollbars.
def setup(app):
    app.add_css_file("noscroll.css")
    app.add_css_file("admonitions.css")
