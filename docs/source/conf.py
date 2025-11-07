# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys
import inspect
import importlib
from pathlib import Path

sys.path.insert(0, os.path.abspath('../../src'))

project = 'ESGVOC'
copyright = '2025, CNRS (IPSL/ESPRI)'
author = 'S. Gardoll, G. Levavasseur, L. Troussellier.'
BASE_URL = 'https://github.com/ESGF/esgf-vocab'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinxcontrib.autodoc_pydantic',
    'sphinx.ext.autosummary',
    'sphinx.ext.linkcode',
    'sphinx.ext.intersphinx',
    'myst_nb',
    'sphinx_tabs.tabs',
    'sphinx_copybutton'
]

def linkcode_resolve(domain, info):
    if domain != "py":
        return None
    if not info["module"]:
        return None

    # Try to import the module and get the actual source file
    try:
        module = importlib.import_module(info["module"])

        # If we have a specific object (class, function, etc.), try to get it
        if info.get("fullname"):
            obj = module
            for part in info["fullname"].split("."):
                obj = getattr(obj, part)

            # Get the source file for this object
            source_file = inspect.getsourcefile(obj)
        else:
            # Just get the module's source file
            source_file = inspect.getsourcefile(module)

        if source_file:
            # Convert absolute path to relative path from repository root
            source_path = Path(source_file)

            # Find the 'src' directory in the path
            parts = source_path.parts
            if 'src' in parts:
                src_index = parts.index('src')
                relative_path = '/'.join(parts[src_index:])
                return f"{BASE_URL}/tree/main/{relative_path}"
    except Exception:
        # If anything fails, fall back to the old behavior
        pass

    # Fallback to the original simple behavior
    filename = info["module"].replace(".", "/")
    return f"{BASE_URL}/tree/main/src/{filename}.py"

templates_path = ['_templates']
exclude_patterns = []

autosummary_generate = True

autodoc_default_options = {
    "show-inheritance": True,
}

# Autodoc pydantic plugin configuration
# https://autodoc-pydantic.readthedocs.io/en/stable/users/configuration.html
autodoc_pydantic_model_show_config_summary = False
autodoc_pydantic_model_show_field_summary = False
autodoc_pydantic_model_hide_paramlist = True
autodoc_pydantic_model_signature_prefix = 'Pydantic model'

# Intersphinx configuration
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'pydantic': ('https://docs.pydantic.dev/latest', None)
}

# MyST NB configuration.
nb_execution_mode = 'off'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_book_theme'


html_theme_options = {
    "repository_url": BASE_URL,
    "use_repository_button": True,
    "use_issues_button": True,
    "use_download_button": True,
    "home_page_in_toc": False,
    "show_toc_level": 2,
}