"""
Setup script for vedic-numerology-astrology package.

This setup script provides backward compatibility and additional configuration
for users who prefer the traditional setup.py approach.
"""

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="vedic-numerology-astrology",
    version="0.1.0",
    author="Norah Jones",
    author_email="author@example.com",
    description="Computational Integration of Vedic Numerology and Sidereal Mechanics",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/astro-fusion/numerology-white-paper",
    project_urls={
        "Bug Tracker": "https://github.com/astro-fusion/numerology-white-paper/issues",
        "Documentation": "https://numerology-white-paper.readthedocs.io/",
        "Source Code": "https://github.com/astro-fusion/numerology-white-paper",
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Astronomy",
        "Topic :: Scientific/Engineering :: Mathematics",
        "Topic :: Religion",
    ],
    keywords="numerology astrology vedic sidereal swiss-ephemeris pyswisseph lahiri-ayanamsa",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.21.0",
        "pandas>=1.3.0",
        "matplotlib>=3.4.0",
        "seaborn>=0.11.0",
        "pytz>=2021.1",
        "PyYAML>=6.0",
        "suntime>=1.2.5",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "isort>=5.10.0",
            "mypy>=1.0.0",
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.0.0",
            "jupyter>=1.0.0",
            "notebook>=6.4.0",
        ],
        "colab": [
            "plotly>=5.0.0",
            "ipywidgets>=7.6.0",
            "jupyter-widgets>=0.6.0",
        ],
        "ephemeris": [
            "pyswisseph>=2.08.00-1",
        ],
        "all": [
            "pyswisseph>=2.08.00-1",
            "plotly>=5.0.0",
            "ipywidgets>=7.6.0",
            "jupyter-widgets>=0.6.0",
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "isort>=5.10.0",
            "mypy>=1.0.0",
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.0.0",
            "jupyter>=1.0.0",
            "notebook>=6.4.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "vedic-numerology=vedic_numerology.cli:main",
        ],
    },
)