""" Test documentation files. """

import urllib.request
import urllib.error

import pytest

from asl_rulebook2.webapp.tests.utils import init_webapp

# ---------------------------------------------------------------------

def test_doc( webapp, webdriver ):
    """Test serving documentation files."""

    # initialize
    webapp.control_tests.set_data_dir( "simple" )
    init_webapp( webapp, webdriver )

    def get_doc( path ):
        # get the specified documentation file
        url = "{}/{}".format( webapp.base_url, path )
        resp = urllib.request.urlopen( url ).read()
        return resp.decode( "utf-8" )

    # test a valid documentation file
    resp = get_doc( "/doc/prepare.md" )
    assert "Preparing the data files" in resp

    # test an unknown documentation file
    with pytest.raises( urllib.error.HTTPError ):
        _ = get_doc( "/doc/UNKNOWN" )

    # try to bust out of the documentation directory
    with pytest.raises( urllib.error.HTTPError ):
        _ = get_doc( "/doc/../LICENSE.txt" )
