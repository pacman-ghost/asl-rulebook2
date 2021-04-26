""" Helper utilities. """

import os

from asl_rulebook2.tests import pytest_options

# ---------------------------------------------------------------------

def for_each_easlrb_version( func ):
    """Run tests for each version of the eASLRB."""
    assert pytest_options.easlrb_path
    base_dir = pytest_options.easlrb_path
    ncalls = 0
    for name in os.listdir( base_dir ):
        dname = os.path.join( base_dir, name )
        if os.path.isfile( os.path.join( dname, "eASLRB.pdf" ) ):
            func( dname )
            ncalls += 1
    assert ncalls > 0
