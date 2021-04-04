""" Test basic functionality. """

from asl_rulebook2.webapp.tests.utils import init_webapp, \
    get_nav_panels, get_content_docs, check_sr_filters, select_tabbed_page, find_child

# ---------------------------------------------------------------------

def test_hello( webapp, webdriver ):
    """Test basic functionality."""

    # initialize
    webapp.control_tests.set_data_dir( "simple" )
    init_webapp( webapp, webdriver )
    check_sr_filters( [] )

    # check that the nav panel loaded correctly
    nav_panels = get_nav_panels()
    assert nav_panels == [ "search", "chapters" ]

    # check that there are no chapters
    select_tabbed_page( "nav", "search" )
    assert find_child( "#nav .tabbed-page[data-tabid='chapters'] .no-chapters" )

    # check that the content docs loaded correctly
    content_docs = get_content_docs()
    assert content_docs == [ "simple" ]
