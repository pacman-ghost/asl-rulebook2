""" Test underscores in ruleid's. """

from asl_rulebook2.webapp.tests.test_search import do_search
from asl_rulebook2.webapp.tests.utils import init_webapp, refresh_webapp, \
    wait_for, get_curr_target, get_last_footnote_msg

# ---------------------------------------------------------------------

def test_search_results( webdriver, webapp ):
    """Test presentation of ruleid's in search results."""

    # initialize
    webapp.control_tests.set_data_dir( "full" )
    init_webapp( webapp, webdriver )

    # check the presentation of ruleid's in search results
    results = do_search( "flugfeld" )
    assert len(results) == 1
    assert results[0]["ruleids"] == [ "KGS CG1" ] # nb: no underscore

    # test searching for a ruleid that has an underscore
    for ruleid in ( "kgs cg1", "kgs_cg1" ):
        refresh_webapp( webdriver )
        results = do_search( ruleid )
        assert results == []
        assert get_curr_target() == ( 'kampfgruppe-scherer!', 'KGS_CG1' )

# ---------------------------------------------------------------------

def test_footnotes( webdriver, webapp ):
    """Test presentation of ruleid's in footnotes."""

    # initialize
    webapp.control_tests.set_data_dir( "full" )
    init_webapp( webapp, webdriver )

    # search for a rule that has an underscore in its ruleid, and has a footnote
    do_search( "flugfeld" )
    assert get_curr_target() == ( 'kampfgruppe-scherer!', 'KGS_CG1' )
    wait_for( 2,
        lambda: "<span class='caption'>KGS CG1</span>" in get_last_footnote_msg()
    )
