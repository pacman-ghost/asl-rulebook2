""" Test basic functionality. """

from asl_rulebook2.webapp.tests.utils import init_webapp, get_nav_panels, get_content_docs

# ---------------------------------------------------------------------

def test_hello( webapp, webdriver ):
    """Test basic functionality."""

    # initialize
    webapp.control_tests.set_data_dir( "simple" )
    init_webapp( webapp, webdriver )

    # check that the nav panel loaded correctly
    nav_panels = get_nav_panels()
    assert nav_panels == [ "search" ]

    # check that the content docs loaded correctly
    content_docs = get_content_docs()
    assert content_docs == [ "simple" ]
