""" Test search result filtering. """

from asl_rulebook2.webapp.tests.test_search import do_search, unload_search_results
from asl_rulebook2.webapp.tests.utils import init_webapp, refresh_webapp, \
    check_sr_filters, find_child

# ---------------------------------------------------------------------

def test_sr_filtering( webdriver, webapp ):
    """Test filtering search results."""

    # initialize
    webapp.control_tests.set_data_dir( "full" )
    webapp.control_tests.set_app_config_val( "DISABLE_AUTO_SHOW_RULE_INFO", True )
    init_webapp( webapp, webdriver )
    check_sr_filters( [ "index", "qa", "errata", "asop-entry" ] )

    def check_sr_count( nvisible, ntotal ):
        """Check the search result count reported in the UI."""
        elem = find_child( "#search-box .sr-count" )
        assert elem.text == "{}/{}".format( nvisible, ntotal )

    def do_test( query_string, sr_type, expected ):

        # make sure the checkbox for the specified search result type is enabled
        sel = "#search-box input[type='checkbox'][name='show-{}-sr']".format( sr_type )
        elem = find_child( sel )
        assert elem.is_selected()

        # do the search
        results = _do_search( query_string )
        assert results == expected
        check_sr_count( len(expected), len(expected) )

        # filter out the specified type of search result
        find_child( sel ).click()
        results = _unload_search_results()
        sr_type2 = "anno" if sr_type == "errata" else sr_type
        expected2 = [ e for e in expected if e["sr_type"] != sr_type2 ]
        if not expected2:
            expected2 = "All search results have been filtered."
        assert results == expected2
        check_sr_count( len(expected2) if isinstance(expected2,list) else 0, len(expected) )

        # refresh the page
        refresh_webapp( webdriver )
        elem = find_child( sel )
        assert not elem.is_selected()

        # repeat the search
        results = _do_search( query_string )
        assert results == expected2
        check_sr_count( len(expected2) if isinstance(expected2,list) else 0, len(expected) )

        # re-enable the specified type of search result
        elem.click()
        results = _unload_search_results()
        assert results == expected
        check_sr_count( len(expected), len(expected) )

    # test filtering index search results
    do_test( "bu", "index", [
        { "sr_type": "index", "title": "((BU))" },
        { "sr_type": "index", "title": "CC" },
    ] )

    # test filtering Q+A search results
    do_test( "encirclement", "qa", [
        { "sr_type": "index", "title": "((Encirclement))" },
        { "sr_type": "qa", "caption": "A7.7" },
        { "sr_type": "qa", "caption": "A7.7 & A23.3" },
    ] )

    # test filtering errata search results
    do_test( "errata", "errata", [
        { "sr_type": "index", "title": "CCPh" },
        { "sr_type": "anno", "caption": "A3.8" },
    ] )

    # test filtering ASOP search results
    do_test( "cc", "asop-entry", [
        { "sr_type": "index", "title": "((CC))" },
        { "sr_type": "index", "title": "CCPh" },
        { "sr_type": "asop-entry", "caption": "8.2: DURING LOCATION's CCPh (ASOP)" },
    ] )

# ---------------------------------------------------------------------

def test_sr_count( webdriver, webapp ):
    """Test the search result count reported in the UI."""

    # initialize
    webapp.control_tests.set_data_dir( "full" )
    init_webapp( webapp, webdriver )

    # NOTE: Most of the testing is done in test_sr_filtering(), we just test error cases here.

    # check the search result when there are no search results
    results = do_search( "xyz" )
    assert results is None
    assert find_child( "#search-box .sr-count" ).text == ""

    # check the search result when there was an error
    results = do_search( "!:simulated-error:!" )
    assert results.startswith( "Search error:" )
    assert find_child( "#search-box .sr-count" ).text == ""

# ---------------------------------------------------------------------

def _do_search( query_string ):
    """Do a search."""
    return _strip_results( do_search( query_string ) )

def _unload_search_results():
    """Unload the current search results."""
    return _strip_results( unload_search_results() )

def _strip_results( results ):
    """Strip search results down to only include what we're interested in."""
    if results is None or isinstance( results, str ):
        return results
    for result_no, result in enumerate( results ):
        results[ result_no ] = {
            key: val for key, val in result.items()
            if key in ( "sr_type", "title", "caption" )
        }
    return results
