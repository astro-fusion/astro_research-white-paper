# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Vedic Numerology-Astrology Integration System'
copyright = '2025, Bishal Ghimire'
author = 'Bishal Ghimire'
release = '0.1.0'

# -- Root document ------------------------------------------------------------
root_doc = 'index'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',      # Core autodoc functionality
    'sphinx.ext.autosummary',  # Generate autosummary tables
    'sphinx.ext.viewcode',     # Add source code links
    'sphinx.ext.napoleon',     # Support for NumPy/Google style docstrings
    'sphinx.ext.intersphinx',  # Link to external documentation
    'sphinx.ext.todo',         # Support for todo items
    'sphinx.ext.coverage',     # Check documentation coverage
    'sphinx.ext.mathjax',      # Math rendering
    'sphinx_rtd_theme',        # Read the Docs theme
    'myst_parser',             # Markdown support
    'sphinx.ext.autodoc.typehints',  # Type hints in signatures
]

# Autodoc settings
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__weakref__'
}

# Autosummary settings
autosummary_generate = True
autosummary_imported_members = True

# Napoleon settings (for Google/NumPy style docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_type_aliases = None

# MyST settings
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "dollarmath",
    "fieldlist",
    "html_admonition",
    "html_image",
    "replacements",
    "smartquotes",
    "strikethrough",
    "substitution",
    "tasklist",
]

myst_heading_anchors = 3

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'pandas': ('https://pandas.pydata.org/docs/', None),
    'matplotlib': ('https://matplotlib.org/stable/', None),
    'plotly': ('https://plotly.com/python-api-reference/', None),
}

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

# Theme options
html_theme_options = {
    'canonical_url': '',
    'analytics_id': '',
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    # Toc options
    'collapse_navigation': True,
    'sticky_navigation': True,
    'navigation_depth': 4,
    'includehidden': True,
    'titles_only': False
}

# -- Options for LaTeX output ------------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    'papersize': 'a4paper',

    # The font size ('10pt', '11pt' or '12pt').
    'pointsize': '11pt',

    # Additional stuff for the LaTeX preamble.
    'preamble': r'''
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{newunicodechar}
\newunicodechar{°}{\degree}
''',

    # Latex figure (float) alignment
    'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (root_doc, 'VedicNumerologyAstrology.tex', 'Vedic Numerology-Astrology Integration System Documentation',
     'Bishal Ghimire', 'manual'),
]

# -- Options for manual page output ------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (root_doc, 'vedicnumerologyastrology', 'Vedic Numerology-Astrology Integration System Documentation',
     [author], 1)
]

# -- Options for Texinfo output ----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (root_doc, 'VedicNumerologyAstrology', 'Vedic Numerology-Astrology Integration System Documentation',
     author, 'VedicNumerologyAstrology', 'Computational integration of Vedic numerology with sidereal astrology.',
     'Miscellaneous'),
]

# -- Extension configuration --------------------------------------------------

# -- Options for todo extension ----------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/todo.html

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True

# -- Path setup ---------------------------------------------------------------
import os
import sys

# Add the project root to the path so we can import modules
sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('../src'))

# -- Custom event handlers ----------------------------------------------------

def autodoc_skip_member(app, what, name, obj, skip, options):
    """Skip certain members from autodoc."""
    # Skip private members that start with single underscore
    if name.startswith('_') and not name.startswith('__'):
        return True

    # Skip dunder methods except __init__
    if name.startswith('__') and name != '__init__':
        return True

    return skip

def setup(app):
    """Setup function for Sphinx extensions."""
    app.connect('autodoc-skip-member', autodoc_skip_member)

    # Add custom CSS
    app.add_css_file('custom.css')

# -- Custom CSS (will be copied to _static) -----------------------------------
html_css_files = [
    'custom.css',
]

# -- Source suffix configuration ---------------------------------------------
source_suffix = {
    '.rst': None,
}

# -- Suppress warnings --------------------------------------------------------
suppress_warnings = [
    'ref.python',  # Suppress warnings about Python references
]

# -- Coverage configuration ---------------------------------------------------
coverage_modules = [
    'vedic_numerology',
    'vedic_numerology.astrology',
    'vedic_numerology.numerology',
    'vedic_numerology.dignity',
    'vedic_numerology.visualization',
]

coverage_ignore_modules = [
    'tests',
    'test_*',
    'conftest',
]

coverage_ignore_functions = [
    'main',
    'setup',
]

# -- Version information ------------------------------------------------------
version = release