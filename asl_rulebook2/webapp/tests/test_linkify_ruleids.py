""" Testing converting auto-deteected ruleid's into links. """

from asl_rulebook2.webapp.tests.utils import init_webapp, refresh_webapp, select_tabbed_page, \
    find_child, find_children, wait_for, wait_for_elem, get_curr_target
from asl_rulebook2.webapp.tests.test_search import do_search
from asl_rulebook2.webapp.tests.test_asop import open_asop_chapter, open_asop_section

# ---------------------------------------------------------------------

def test_index_entry( webdriver, webapp ):
    """Test ruleid's in index entries."""

    # initialize
    webapp.control_tests.set_data_dir( "full" )
    init_webapp( webapp, webdriver )

    # test ruleid's in an index entry's search result
    results = _do_search( "CCPh", True )
    assert len(results) == 1
    sr_elem = find_child( "#search-results .sr" )
    _check_ruleid( find_child(".subtitle",sr_elem), ("asl-rulebook!","A11") )

    # test ruleid's in an index entry's content
    results = _do_search( "also want to", False )
    assert len(results) == 1
    sr_elem = find_child( "#search-results .sr" )
    _check_ruleid( find_child(".content",sr_elem), ("asl-rulebook!","A3.8") )
    _dismiss_rule_info_popup()

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def test_alternate_content_set( webdriver, webapp ):
    """Test ruleid's that reference another document."""

    # initialize
    webapp.control_tests.set_data_dir( "full" )
    init_webapp( webapp, webdriver )

    # test a ruleid that references the Red Barricades document
    results = _do_search( "cellar", True )
    assert len(results) == 1
    sr_elem = find_child( "#search-results .sr" )
    _check_ruleid( find_child(".content",sr_elem), ("asl-rulebook!red-barricades","O6.7") )

# ---------------------------------------------------------------------

def test_qa( webdriver, webapp ):
    """Testing ruleid's in Q+A entries."""

    # initialize
    webapp.control_tests.set_data_dir( "full" )
    init_webapp( webapp, webdriver )

    # test ruleid's in a Q+A entry's search result
    results = _do_search( "wp", True )
    assert len(results) == 5
    sr_elem = find_children( "#search-results .sr" )[ 3 ]
    _check_ruleid( find_child(".caption",sr_elem), ("asl-rulebook!","A24.31") )
    _dismiss_rule_info_popup()
    _check_ruleid( find_child(".question",sr_elem), ("asl-rulebook!","A24.3") )
    _dismiss_rule_info_popup()
    _check_ruleid( find_child(".answer",sr_elem), ("asl-rulebook!","A24.31") )
    _dismiss_rule_info_popup()

    # test ruleid's in a Q+A entry in the rule info popup
    expected = [
        ( ".caption", ("asl-rulebook!","A24.31") ),
        ( ".question", ("asl-rulebook!","A24.3") ),
        ( ".answer", ("asl-rulebook!","A24.31") )
    ]
    for sel, target in expected:
        _do_search( "A24.31", False )
        elems = find_children( "#rule-info .rule-info" )
        assert len(elems) == 1
        _check_ruleid( find_child(sel,elems[0]), target )
        _dismiss_rule_info_popup()

# ---------------------------------------------------------------------

def test_errata( webdriver, webapp ):
    """Test ruleid's in errata."""

    # initialize
    webapp.control_tests.set_data_dir( "full" )
    init_webapp( webapp, webdriver )

    # test ruleid's in an errata's search result
    results = _do_search( "errata", True )
    assert len(results) == 2
    sr_elem = find_children( "#search-results .sr" )[ 1 ]
    _check_ruleid( find_child(".caption",sr_elem), ("asl-rulebook!","A3.8") )
    _dismiss_rule_info_popup()
    _check_ruleid( find_child(".content",sr_elem), ("asl-rulebook!","A.2") )

    # test ruleid's in an errata in the rule info popup
    expected = [
        ( ".caption", ("asl-rulebook!","A3.8") ),
        ( ".content", ("asl-rulebook!","A.2") )
    ]
    for sel, target in expected:
        _do_search( "errata", False )
        sr_elem = find_child( "#rule-info .rule-info" )
        _check_ruleid( find_child(sel,sr_elem), target )
        _dismiss_rule_info_popup()

# ---------------------------------------------------------------------

def test_user_annotations( webdriver, webapp ):
    """Test ruleid's in user annotations."""

    # initialize
    webapp.control_tests.set_data_dir( "full" )
    init_webapp( webapp, webdriver )

    # test ruleid's in a user annotation's search result
    results = _do_search( "is there anything", False )
    assert len(results) == 1
    sr_elem = find_child( "#search-results .sr" )
    _check_ruleid( find_child(".caption",sr_elem), ("asl-rulebook!","A24.3") )
    _dismiss_rule_info_popup()
    _check_ruleid( find_child(".content",sr_elem), ("asl-rulebook!","A24.31") )
    _dismiss_rule_info_popup()

# ---------------------------------------------------------------------

def test_asop( webdriver, webapp ):
    """Test ruleid's in ASOP entries."""

    # initialize
    webapp.control_tests.set_data_dir( "full" )
    init_webapp( webapp, webdriver )

    # test ruleid's in an ASOP entry's search result
    results = _do_search( "first/next", False )
    assert len(results) == 1
    sr_elem = find_child( "#search-results .sr" )
    _check_ruleid( find_child(".content",sr_elem), ("asl-rulebook!","A11.3-.34") )

    # click through to the ASOP section and check the ruleid there
    find_child( ".caption", sr_elem ).click()
    _check_ruleid( find_child("#asop .section"), ("asl-rulebook!","A11.3-.34") )

    # check the ruleid in the ASOP chapter
    refresh_webapp( webdriver ) # nb: clear the ASOP overrides
    select_tabbed_page( "nav", "asop" )
    open_asop_chapter( "close-combat" )
    sections = find_children( "#asop .section" )
    assert len(sections) == 4
    _check_ruleid( sections[1], ("asl-rulebook!","A11.3-.34") )

    # check the ruleid in the ASOP section
    refresh_webapp( webdriver )
    select_tabbed_page( "nav", "asop" )
    open_asop_section( "close-combat", 1 )
    section = find_child( "#asop .section" )
    _check_ruleid( section, ("asl-rulebook!","A11.3-.34") )

# ---------------------------------------------------------------------

def _do_search( query_string, dismiss_rule_info ):
    """Do a search."""
    results = do_search( query_string )
    if dismiss_rule_info:
        _dismiss_rule_info_popup()
    return results

def _dismiss_rule_info_popup():
    """Dismiss the rule info popup."""
    elem = wait_for_elem( 2, "#rule-info" )
    find_child( ".close-rule-info" ).click()
    wait_for( 2, lambda: not elem.is_displayed() )

def _check_ruleid( elem, expected ):
    """Check the ruleid in the specified element."""

    # check the ruleid
    elems = find_children( "span.auto-ruleid", elem )
    assert len(elems) == 1
    elem = elems[0]
    cset_id = elem.get_attribute( "data-csetid" )
    if cset_id:
        pos = expected[0].find( "!" )
        assert cset_id == expected[0] if pos < 0 else expected[0][:pos]
    ruleid = expected[1]
    pos = ruleid.find( "-" )
    if pos >= 0:
        ruleid = ruleid[:pos]
    assert elem.get_attribute( "data-ruleid" ) == ruleid
    assert elem.text == expected[1]

    # click on the ruleid and make sure we go to the right place
    elem.click()
    wait_for( 2, lambda: get_curr_target() == ( expected[0], ruleid ) )
