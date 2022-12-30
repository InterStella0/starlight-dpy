# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
import os
import sys

project = 'starlight-dpy'
copyright = '2022, Sarah'
author = 'Sarah'
release = '0.0.1'


sys.path.insert(0, os.path.abspath('..'))
sys.path.append(os.path.abspath('extensions'))


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon'
]

autodoc_typehints = 'none'
templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

intersphinx_mapping = {
    'py': ('https://docs.python.org/3', None),
    'dpy': ('https://discordpy.readthedocs.io/en/stable', None),
}

# required for discord.py's docs.
rst_prolog = """
.. |coro| replace:: This function is a |coroutine_link|_.
.. |maybecoro| replace:: This function *could be a* |coroutine_link|_.
.. |coroutine_link| replace:: *coroutine*
.. _coroutine_link: https://docs.python.org/3/library/asyncio-task.html#coroutine
"""

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ['_static']
html_theme_options = {
    'display_version': True,
    'style_nav_header_background': '#ffcccb',
    'collapse_navigation': True,
    'sticky_navigation': True,
    'navigation_depth': 4,
}

