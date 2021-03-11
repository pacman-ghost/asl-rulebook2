""" pytest support functions. """

import pytest

_pytest_options = None

# ---------------------------------------------------------------------

def pytest_addoption( parser ):
    """Configure pytest options."""

    # NOTE: This file needs to be in the project root for this to work :-/

    # add test options
    parser.addoption(
        "--easlrb", action="store", dest="easlrb_path", default=None,
        help="Directory containing the MMP eASLRB PDF and extracted data file(s)."
    )

    # add test options
    parser.addoption(
        "--short-tests", action="store_true", dest="short_tests", default=False,
        help="Skip running the longer tests."
    )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def pytest_configure( config ):
    """Called after command-line options have been parsed."""
    global _pytest_options
    _pytest_options = config.option
    import asl_rulebook2.tests
    asl_rulebook2.tests.pytest_options = _pytest_options
