""" Setup the package.

    Install this module in development mode to get the tests to work:
      pip install --editable .[dev]
"""

import os
from setuptools import setup, find_packages

# ---------------------------------------------------------------------

# NOTE: We break the requirements out into separate files so that we can load them early
# into a Docker image, where they can be cached, instead of having to re-install them every time.

def parse_requirements( fname ):
    """Parse a requirements file."""
    lines = []
    fname = os.path.join( os.path.dirname(__file__), fname )
    for line in open(fname,"r"):
        line = line.strip()
        if line == "" or line.startswith("#"):
            continue
        lines.append( line )
    return lines

# ---------------------------------------------------------------------

setup(
    name = "asl_rulebook2",
    version = "0.1",
    description = "Search engine for the eASLRB.",
    license = "AGPLv3",
    url = "https://github.com/pacman-ghost/asl-rulebook2",
    packages = find_packages(),
    install_requires = parse_requirements( "requirements.txt" ),
    extras_require = {
        "dev": parse_requirements( "requirements-dev.txt" ),
    },
    include_package_data = True,
    data_files = [
        ( "asl-rulebook2", ["LICENSE.txt"] ),
    ],
    entry_points = {
        "console_scripts": "dump-pdf = bin.dump_pdf:main",
    }
)
