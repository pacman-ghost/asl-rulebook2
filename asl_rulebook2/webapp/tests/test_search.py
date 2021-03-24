""" Test search. """

import logging

from selenium.webdriver.common.keys import Keys

from asl_rulebook2.webapp.search import load_search_config, _make_fts_query_string
from asl_rulebook2.webapp.startup import StartupMsgs
from asl_rulebook2.webapp.tests.utils import init_webapp, select_tabbed_page, get_curr_target, get_classes, \
    wait_for, find_child, find_children, unload_elem, unload_sr_text

# ---------------------------------------------------------------------

def test_search( webapp, webdriver ):
    """Test search."""

    # initialize
    webapp.control_tests.set_data_dir( "simple" )
    init_webapp( webapp, webdriver )

    # test a search that finds nothing
    results = do_search( "oogah, boogah!" )
    assert results is None

    # test error handling
    results = do_search( "!:simulated-error:!" )
    assert "Simulated error." in results

    # do a search
    results = do_search( "enemy" )
    assert results == [
        { "sr_type": "index",
          "title": "CCPh", "subtitle": "Close Combat Phase",
          "ruleids": [ "A3.8" ],
          "rulerefs": [
              { "caption": "((ENEMY)) Attacks", "ruleids": [ "S11.5" ] },
              { "caption": "dropping SW before CC", "ruleids": [ "A4.43" ] },
          ]
        },
        { "sr_type": "index",
          "title": "Double Time",
          "content": "Also known as \"running really fast.\"",
          "see_also": [ "CX" ],
          "ruleids": [ "A4.5-.51", "S6.222" ],
          "rulerefs": [
              { "caption": "((ENEMY)) Guard Automatic Action", "ruleids": [ "S6.303" ] },
              { "ruleids": [ "C10.3" ] },
              { "caption": "NA in Advance Phase", "ruleids": [ "A4.7" ] },
              { "caption": "'S?' is \"<NA>\"" },
          ]
      },
    ]

    # do another search
    results = do_search( "gap" )
    assert results == [
        { "sr_type": "index",
          "title": "((Gaps)), Convoy",
          "ruleids": [ "E11.21" ],
        },
    ]

# ---------------------------------------------------------------------

def test_content_fixup( webapp, webdriver ):
    """Test fixing up of content returned by the search engine."""

    # initialize
    webapp.control_tests.set_data_dir( "simple" )
    init_webapp( webapp, webdriver )

    # search for a fraction
    results = do_search( "3/4" )
    assert len(results) == 1
    assert results[0]["content"] == "HTML content: 2((\u00be)) MP"

    # search for something that ends with a hash
    results = do_search( "H#" )
    assert len(results) == 1
    assert results[0]["title"] == "((H#))"

    # search for "U.S."
    results = do_search( "U.S." )
    assert len(results) == 1
    assert results[0]["content"] == "The ((U.S.)) has lots of this."

# ---------------------------------------------------------------------

def test_targets( webapp, webdriver ):
    """Test clicking on search results."""

    # initialize
    webapp.control_tests.set_data_dir( "simple" )
    init_webapp( webapp, webdriver, no_content=1, add_empty_doc=1 )

    def do_test( query_string, sel, expected ):

        # select the dummy document
        select_tabbed_page( "#content", "empty" )

        # do the search
        do_search( query_string )

        # click on a target
        elem = find_child( "#search-results {}".format( sel ) )
        elem.click()
        wait_for( 2, lambda: get_curr_target() == ( "simple", expected ) )

    # do the tests
    do_test( "CC", ".sr .ruleids .ruleid a", "A3.8" )
    do_test( "time", ".sr .rulerefs .ruleid a", "A4.7" )

# ---------------------------------------------------------------------

def test_toggle_rulerefs( webapp, webdriver ):
    """Test expanding/collapsing ruleref's."""

    # initialize
    webapp.control_tests.set_data_dir( "simple" )
    init_webapp( webapp, webdriver )

    def do_test( query_string, expected ):
        results = do_search( query_string )
        assert len(results) == 1
        sr_elem = find_child( "#search-results .sr" )
        assert _is_expanded_rulerefs( sr_elem ) == expected

    # do the tests
    do_test( "CCPh", True ) # nb: matches the title
    do_test( "Combat", True ) # nb: matches the subtitle
    do_test( "running", True ) # nb: matches the content
    do_test( "RCL", False ) # nb: matches some (but not all) of the ruleref's
    do_test( "rcl AND heat", None ) # nb: matches all of the ruleref's
    do_test( "firepower", None ) # nb: has no ruleref's

# ---------------------------------------------------------------------

def test_target_search( webapp, webdriver ):
    """Test searching for targets."""

    # initialize
    webapp.control_tests.set_data_dir( "simple" )
    init_webapp( webapp, webdriver )

    # search for a target
    results = do_search( "cc" )
    assert len(results) > 0
    results = do_search( "D1.4" )
    assert len(results) == 0 # nb: previous search results should be removed
    wait_for( 2, lambda: get_curr_target() == ( "simple", "D1.4" ) )

    # search for a target
    results = do_search( "astral plane" )
    assert results is None # nb: this is the "no results" message
    results = do_search( "E11.21" )
    assert len(results) == 0 # nb: the "no results"  message should be cleared
    wait_for( 2, lambda: get_curr_target() == ( "simple", "E11.21" ) )

    # search for a target
    results = do_search( "*" )
    assert isinstance( results, str ) # nb: this is an error message
    results = do_search( "a4.7" )
    assert len(results) == 0 # nb: the error message should be cleared
    wait_for( 2, lambda: get_curr_target() == ( "simple", "A4.7" ) )

# ---------------------------------------------------------------------

def test_see_also( webapp, webdriver ):
    """Test searching for "see also" fields."""

    # initialize
    webapp.control_tests.set_data_dir( "see-also" )
    init_webapp( webapp, webdriver )

    # do a search
    results = do_search( "foo" )
    assert results == [ {
        "sr_type": "index",
        "title": "((Foo))",
        "see_also": [ "Bar", "Baz Baz" ]
    } ]

    def click_see_also( caption ):
        elems = {
            e.text: e
            for e in find_children( "#search-results .see-also a" )
        }
        assert len(elems) == 2
        elems[ caption ].click()
        expected = '"{}"'.format( caption ) if " " in caption else caption
        wait_for( 2, lambda: find_child( "input#query-string" ).get_attribute( "value" ) == expected )
        return _unload_search_results()

    # click on the "Bar" link and check that it gets searched for
    results = click_see_also( "Bar" )
    assert results == [ {
        "sr_type": "index",
        "title": "((Bar))"
    } ]

    # search for "foo" again, and click on the "Baz Baz" link
    do_search( "foo" )
    results = click_see_also( "Baz Baz" )
    assert results is None

# ---------------------------------------------------------------------

def test_bad_sr_highlights( webapp, webdriver ):
    """Test fixing up highlight markers that have been incorrectly inserted into search result content."""

    # initialize
    webapp.control_tests.set_data_dir( "bad-sr-highlights" )
    init_webapp( webapp, webdriver )

    # bring up an index  search result with a problem in its content
    results = do_search( "highlight" )
    assert results == [ {
        "sr_type": "index",
        "title": "Bad ((highlight))",
        "content": "before link after",
    } ]

    # bring up a Q+A entry with a problem in its question
    results = do_search( "foo" )
    assert len(results) == 1
    assert results[0]["content"][0]["question"] == "((foo)) link ((foo))"

    # bring up a Q+A entry with a problem in one of its answers
    results = do_search( "bar" )
    assert len(results) == 1
    assert results[0]["content"][0]["answers"][0][0] == "..((bar)).. link  ((bar))"

# ---------------------------------------------------------------------

def test_make_fts_query_string():
    """Test generating the FTS query string."""

    # initialize
    startup_msgs = StartupMsgs()
    load_search_config( startup_msgs, logging.getLogger("_unknown_") )

    def check( query, expected ):
        fts_query_string, _ = _make_fts_query_string(query)
        assert fts_query_string == expected
        assert not startup_msgs.msgs

    # test some query strings
    check( "", "" )
    check( "hello", "hello" )
    check( "  hello,  world!  ", "hello AND world" )
    check(
        "foo 1+2 A-T K# bar",
        'foo AND "1+2" AND "a-t" AND "k#" AND bar'
    )
    check(
        "a'b a''b",
        "\"a'b\" AND \"a''b\""
    )
    check(
        'foo "set dc" bar',
        'foo AND "set dc" AND bar'
    )

    # test some quoted phrases
    check( '""', '' )
    check( ' " " ', '' )
    check(
        '"hello world"',
        '"hello world"'
    )
    check(
        '  foo  "hello  world"  bar  ',
        'foo AND "hello world" AND bar'
    )
    check(
        ' foo " xyz " bar ',
        'foo AND xyz AND bar'
    )
    check(
        ' foo " xyz 123 " bar ',
        'foo AND "xyz 123" AND bar'
    )

    # test some incorrectly quoted phrases
    check( '"', '' )
    check( ' " " " ', '' )
    check( ' a "b c d e', 'a AND "b c d e"' )
    check( ' a b" c d e ', 'a AND b AND c AND d AND e' )

    # test pass-through
    check( "AND", "AND" )
    check( " OR", "OR" )
    check( "OR ", "OR" )
    check( "foo OR bar", "foo OR bar" )
    check( "(a OR b)", "(a OR b)" )

    # test search replacements
    check( "1/2 3/4 3/8 5/8", '"&frac12;" AND "&frac34;" AND "&frac38;" AND "&frac58;"' )
    check( "(r)", '"&reg;"' )

    # test search aliases
    check( "entrenchment", "( ditch OR entrenchment OR foxhole OR trench )" )
    check( "entrenchments", "( ditch OR entrenchments OR foxhole OR trench )" )
    check( "foxhole", "foxhole" )

    # test search synonyms
    check( "armor", "( armor OR armour )" )
    check( "american big armor", '( america OR american OR "u.s." ) AND big AND ( armor OR armour )' )

# ---------------------------------------------------------------------

def do_search( query_string ):
    """Do a search."""

    def get_seq_no():
        return find_child( "#search-results" ).get_attribute( "data-seqno" )

    # submit the search
    select_tabbed_page( "#nav", "search" )
    elem = find_child( "input#query-string" )
    elem.clear()
    elem.send_keys( query_string )
    seq_no = get_seq_no()
    elem.send_keys( Keys.RETURN )

    # unload the results
    wait_for( 2, lambda: get_seq_no() > seq_no )
    return _unload_search_results()

def _unload_search_results():
    """Unload the search results."""

    # check if there were any search results
    elem = find_child( "#search-results .error" )
    if elem:
        return elem.text # nb: string = error message
    elem = find_child( "#search-results .no-results" )
    if elem:
        assert elem.text == "Nothing was found."
        return None # nb: None = no results

    def unload_ruleids( result, key, parent ):
        """Unload a list of ruleid's."""
        if not parent:
            return
        ruleids = []
        for elem in find_children( ".ruleid", parent ):
            ruleid = unload_sr_text( elem )
            assert ruleid.startswith( "[" ) and ruleid.endswith( "]" )
            ruleids.append( ruleid[1:-1] )
        if ruleids:
            result[key] = ruleids

    def unload_rulerefs( result, key, parent ):
        """Unload a list of ruleref's."""
        if not parent:
            return
        rulerefs = []
        for elem in find_children( "li", parent ):
            ruleref = {}
            unload_elem( ruleref, "caption", find_child(".caption",elem), adjust_hilites=True )
            unload_ruleids( ruleref, "ruleids", elem )
            rulerefs.append( ruleref )
        if rulerefs:
            result[key] = rulerefs

    def unload_index_sr( sr ): #pylint: disable=possibly-unused-variable
        """Unload an "index" search result."""
        result = {}
        unload_elem( result, "title", find_child("span.title",sr), adjust_hilites=True )
        unload_elem( result, "subtitle", find_child(".subtitle",sr), adjust_hilites=True )
        unload_elem( result, "content", find_child(".content",sr), adjust_hilites=True )
        if unload_elem( result, "see_also", find_child(".see-also",sr) ):
            assert result["see_also"].startswith( "See also:" )
            result["see_also"] = [ s.strip() for s in result["see_also"][9:].split( "," ) ]
        unload_ruleids( result, "ruleids", find_child(".ruleids",sr) )
        unload_rulerefs( result, "rulerefs", find_child(".rulerefs",sr) )
        return result

    def unload_qa_sr( sr ): #pylint: disable=possibly-unused-variable
        """Unload a "qa" search result."""
        from asl_rulebook2.webapp.tests.test_qa import unload_qa
        return unload_qa( sr )

    def unload_anno_sr( sr ): #pylint: disable=possibly-unused-variable
        """Unload an "anno" search result."""
        from asl_rulebook2.webapp.tests.test_annotations import unload_anno
        return unload_anno( sr )

    def unload_asop_entry_sr( sr ): #pylint: disable=possibly-unused-variable
        """Unload an "ASOP entry" search result."""
        result = {}
        unload_elem( result, "caption", find_child(".caption",sr), adjust_hilites=True )
        unload_elem( result, "content", find_child(".content",sr), adjust_hilites=True )
        return result

    # unload the search results
    results = []
    for sr in find_children( "#search-results .sr"):
        classes = get_classes( sr )
        classes.remove( "sr" )
        classes = [ c for c in classes if c in ["index-sr","qa","anno","asop-entry-sr"] ]
        assert len(classes) == 1
        sr_type = classes[0]
        if sr_type.endswith( "-sr" ):
            sr_type = sr_type[:-3]
        func = locals()[ "unload_{}_sr".format( sr_type.replace("-","_") ) ]
        sr = func( sr )
        sr["sr_type"] = sr_type
        results.append( sr )

    return results

# ---------------------------------------------------------------------

def _is_expanded_rulerefs( sr_elem ):
    """Check if ruleref's have been expanded for a search result."""
    img = find_child( "img.toggle-rulerefs", sr_elem )
    if not img:
        return None
    url = img.get_attribute( "src" )
    if url.endswith( "collapse-rulerefs.png" ):
        return True
    assert url.endswith( "expand-rulerefs.png" )
    return False
