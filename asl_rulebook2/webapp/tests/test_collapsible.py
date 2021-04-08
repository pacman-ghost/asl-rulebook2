""" Test collapsible's and collaper's. """

from asl_rulebook2.webapp.tests.utils import init_webapp, select_tabbed_page, \
    find_child, find_children, wait_for, wait_for_elem

from asl_rulebook2.webapp.tests.test_search import do_search
from asl_rulebook2.webapp.tests.test_asop import unload_asop_nav, open_asop_chapter
from asl_rulebook2.webapp.tests.utils import has_class

# ---------------------------------------------------------------------

def test_index_sr( webapp, webdriver ):
    """Test collapsible index search results."""

    # initialize
    webapp.control_tests.set_data_dir( "collapsible" )
    init_webapp( webapp, webdriver )

    def count_rulerefs( sr_elem ):
        # return how many ruleref's the index search result has
        rulerefs = find_children( "ul.rulerefs li", sr_elem )
        return len( [ r for r in rulerefs if r.is_displayed() ] )

    def do_test( query_string, expected_state, expected_rulerefs, expected_rulerefs2 ):

        # do the search
        results = do_search( query_string )
        assert len(results) == 1

        # check the collapsed/expanded state
        sr_elem = find_child( "#search-results .sr" )
        assert _is_collapsed( sr_elem, has_collapsible=False ) == expected_state

        # check the number of rulerefs
        assert count_rulerefs( sr_elem ) == expected_rulerefs

        if expected_state is None:
            return

        # toggle the state and check the results
        find_child( ".collapser", sr_elem ).click()
        wait_for( 2, lambda: _is_collapsed( sr_elem, has_collapsible=False ) != expected_state )
        assert count_rulerefs( sr_elem ) == expected_rulerefs2

        # toggle the state back and check the results
        find_child( ".collapser", sr_elem ).click()
        wait_for( 2, lambda: _is_collapsed( sr_elem, has_collapsible=False ) == expected_state )
        assert count_rulerefs( sr_elem ) == expected_rulerefs

    # do the tests
    do_test( "CCPh", False, 2, 0 ) # matches the title
    do_test( "Combat", False, 2, 0 ) # matches the subtitle
    do_test( "running", False, 4, 0 ) # matches the content
    do_test( "RCL", True, 1, 2 ) # matches some (but not all) of the ruleref's
    do_test( "rcl AND heat", None, 2, None ) # matches all of the ruleref's
    do_test( "firepower", None, 0, None ) # has no ruleref's

# ---------------------------------------------------------------------

def test_qa( webapp, webdriver ):
    """Test collapsible Q+A entries."""

    # initialize
    webapp.control_tests.set_data_dir( "collapsible" )
    init_webapp( webapp, webdriver )

    # do the tests
    _test_collapsible( '"short Q+A"', "A.1", None )
    _test_collapsible( '"long Q+A"', "A.2", False )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def test_errata( webapp, webdriver ):
    """Test collapsible errata."""

    # initialize
    webapp.control_tests.set_data_dir( "collapsible" )
    init_webapp( webapp, webdriver )

    # do the tests
    _test_collapsible( '"short errata"', "B.1", None )
    _test_collapsible( '"long errata"', "B.2", False )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def test_user_annotations( webapp, webdriver ):
    """Test collapsible user annotations."""

    # initialize
    webapp.control_tests.set_data_dir( "collapsible" )
    init_webapp( webapp, webdriver )

    # do the tests
    _test_collapsible( '"short user annotations"', "C.1", None )
    _test_collapsible( '"long user annotations"', "C.2", False )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def test_asop_sr( webapp, webdriver ):
    """Test ASOP search results."""

    # initialize
    webapp.control_tests.set_data_dir( "collapsible" )
    init_webapp( webapp, webdriver )

    # do the tests
    _test_collapsible( '"short ASOP"', None, None )
    _test_collapsible( '"long ASOP"', None, False )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _test_collapsible( query_string, ruleid, expected ):

    # do the search
    if find_child( "#rule-info" ).is_displayed():
        find_child( ".close-rule-info" ).click()
    results = do_search( query_string )
    assert len(results) == 1
    sr_elem = find_child( "#search-results .sr" )
    assert _is_collapsed( sr_elem ) == expected

    # toggle the state and check the results
    if expected is not None:
        find_child( ".collapser", sr_elem ).click()
        wait_for( 2, lambda: _is_collapsed( sr_elem ) != expected )
        find_child( ".collapser", sr_elem ).click()
        wait_for( 2, lambda: _is_collapsed( sr_elem ) == expected )

    # check if there will be an entry in the rule info popup
    if not ruleid:
        return

    # yup - bring that entry up and check it
    results = do_search( ruleid )
    popup = wait_for_elem( 2, "#rule-info" )
    elems = find_children( ".rule-info", popup )
    assert len(elems) == 1
    elem = elems[0]
    assert _is_collapsed( elem ) == expected

    # toggle the state and check the results
    if expected is not None:
        find_child( ".collapser", elem ).click()
        wait_for( 2, lambda: _is_collapsed( elem ) != expected )
        find_child( ".collapser", elem ).click()
        wait_for( 2, lambda: _is_collapsed( elem ) == expected )

# ---------------------------------------------------------------------

def test_asop_preamble( webapp, webdriver ):
    """Test ASOP preambles."""

    # initialize
    webapp.control_tests.set_data_dir( "collapsible" )
    init_webapp( webapp, webdriver )
    select_tabbed_page( "nav", "asop" )
    nav = unload_asop_nav( True )

    def check_preamble( expected ):
        # check if the preamble is collapsed/expanded
        elem = find_child( "#asop" )
        assert _is_collapsed( elem, has_collapsible=True ) == expected

    # open the "no content" section
    open_asop_chapter( "no-content", nav )
    check_preamble( None )

    # open the "short content" section
    open_asop_chapter( "short-content", nav )
    check_preamble( None )

    # open the "long content" section
    open_asop_chapter( "long-content", nav )
    check_preamble( False )

    # collapse the preamble
    find_child( "#asop .collapser" ).click()
    wait_for( 2, lambda: _is_collapsed( find_child("#asop") ) )
    # nb: the preamble is now collapsed

    # open the "short content" section
    open_asop_chapter( "short-content", nav )
    check_preamble( None )

    # check that the preamble is still collapsed in the "long content" section
    open_asop_chapter( "long-content", nav )
    check_preamble( True )

    # switch to another nav pane, then check that the preamble is still collapsed when we come back
    open_asop_chapter( "short-content", nav )
    select_tabbed_page( "nav", "search" )
    select_tabbed_page( "nav", "asop" )
    check_preamble( None )
    open_asop_chapter( "long-content", nav )
    check_preamble( True )

# ---------------------------------------------------------------------

def _is_collapsed( elem, has_collapsible=True ):
    """Check the state of a collapser and its associated collapsible."""

    # get the state of the collapser
    collapser = find_child( "img.collapser", elem )
    if not collapser:
        return None
    url = collapser.get_attribute( "src" )
    if url.endswith( "collapser-down.png" ):
        is_collapsed = True
    else:
        assert url.endswith( "collapser-up.png" )
        is_collapsed = False

    # check the state of the associated collapsible
    collapsible = find_child( ".collapsible", elem )
    if has_collapsible:
        if is_collapsed:
            assert has_class( collapsible, "collapsed" )
        else:
            assert not has_class( collapsible, "collapsed" )
    else:
        assert collapsible is None

    return is_collapsed
