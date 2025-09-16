#!/usr/bin/env python3
"""
Setup script for BbCadam - A FreeCAD-based scripting framework for parametric CAD design.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Read version from __init__.py (will be created later)
def get_version():
    try:
        with open("bbcadam/__init__.py", "r") as f:
            for line in f:
                if line.startswith("__version__"):
                    return line.split("=")[1].strip().strip('"').strip("'")
    except FileNotFoundError:
        pass
    return "0.1.0"

setup(
    name="bbcadam",
    version=get_version(),
    author="BbCadam Contributors",
    author_email="",
    description="A FreeCAD-based scripting framework for parametric CAD design",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/gotchoices/bbcadam",
    project_urls={
        "Bug Reports": "https://github.com/gotchoices/bbcadam/issues",
        "Source": "https://github.com/gotchoices/bbcadam",
        "Documentation": "https://github.com/gotchoices/bbcadam/blob/main/docs/",
    },
    packages=["bbcadam", "bbcadam.cli"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Manufacturing",
        "Topic :: Scientific/Engineering",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        # FreeCAD is user-provided, not packaged
        # Add other dependencies as needed
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov",
            "pytest-mock",
            "black",
            "flake8",
        ],
        "docs": [
            "sphinx",
            "sphinx-rtd-theme",
        ],
    },
    entry_points={
        "console_scripts": [
            "bbcadam-launch=bbcadam.cli.launch:main",
            "bbcadam-build=bbcadam.cli.build:main",
            "bbcadam-py=bbcadam.cli.py_runner:main",
            "bbcadam-dump=bbcadam.cli.dump:main",
        ],
    },
    include_package_data=True,
    package_data={
        "bbcadam": [
            "*.md",
            "docs/*",
            "examples/*",
        ],
    },
    zip_safe=False,
    keywords="cad, freecad, parametric, modeling, 3d, manufacturing",
)
