""" Run ESLint over the Javascript files. """

import os.path
import subprocess
import pytest

# ---------------------------------------------------------------------

@pytest.mark.skipif( not os.environ.get("ESLINT"), reason="ESLINT not configured." )
def test_eslint():
    """Run ESLint over the Javascript files."""

    # initialize
    eslint = os.environ[ "ESLINT" ]

    # check each Javascript file
    dname = os.path.join( os.path.dirname(__file__), "../static/" )
    for fname in os.listdir( dname ):

        if os.path.splitext( fname )[1] != ".js":
            continue

        # run ESLint for the next file
        proc = subprocess.run(
            [ eslint, os.path.join(dname,fname) ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8",
            check=False
        )
        if proc.stdout or proc.stderr:
            print( "=== ESLint failed: {} ===".format( fname ) )
            if proc.stdout:
                print( proc.stdout )
            if proc.stderr:
                print( proc.stderr )
            assert False
