""" Test search. """

import re
import logging

from selenium.webdriver.common.keys import Keys

from asl_rulebook2.utils import strip_html
from asl_rulebook2.webapp.search import load_search_config, _make_fts_query_string
from asl_rulebook2.webapp.tests.utils import init_webapp, select_tabbed_page, get_classes, \
    wait_for, find_child, find_children

# ---------------------------------------------------------------------

def test_search( webapp, webdriver ):
    """Test search."""

    # initialize
    webapp.control_tests.set_data_dir( "simple" )
    init_webapp( webapp, webdriver )

    # test a search that finds nothing
    results = _do_search( "oogah, boogah!" )
    assert results is None

    # test error handling
    results = _do_search( "!:simulated-error:!" )
    assert "Simulated error." in results

    # do a search
    results = _do_search( "enemy" )
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
    results = _do_search( "gap" )
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
    results = _do_search( "3/4" )
    assert len(results) == 1
    assert results[0]["content"] == "HTML content: 2((\u00be)) MP"

    # search for something that ends with a hash
    results = _do_search( "H#" )
    assert len(results) == 1
    assert results[0]["title"] == "((H#))"

    # search for "U.S."
    results = _do_search( "U.S." )
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
        _do_search( query_string )

        # click on a target
        elem = find_child( "#search-results {}".format( sel ) )
        elem.click()
        def check_target():
            # check the active tab
            if find_child( "#content .tab-strip .tab.active" ).get_attribute( "data-tabid" ) != "simple":
                return False
            # check the current target
            elem = find_child( "#content .tabbed-page[data-tabid='simple'] .content-doc" )
            return elem.get_attribute( "data-target" ) == expected
        wait_for( 2, check_target )

    # do the tests
    do_test( "CC", ".sr .ruleids .ruleid a", "A3.8" )
    do_test( "time", ".sr .rulerefs .ruleid a", "A4.7" )

# ---------------------------------------------------------------------

def test_make_fts_query_string():
    """Test generating the FTS query string."""

    # initialize
    load_search_config( logging.getLogger("_unknown_") )

    def check( query, expected ):
        fts_query_string, _ = _make_fts_query_string(query)
        assert fts_query_string == expected

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

def _do_search( query_string ):
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
    elem = find_child( "#search-results .error" )
    if elem:
        return elem.text # nb: string = error message
    elem = find_child( "#search-results .no-results" )
    if elem:
        assert elem.text == "Nothing was found."
        return None # nb: None = no results
    results = _unload_search_results()
    assert isinstance( results, list ) # nb: list = search results
    return results

def _unload_search_results():
    """Unload the search results."""

    def unload_elem( result, key, elem ):
        """Unload a single element."""
        if not elem:
            return False
        elem_text = get_elem_text( elem )
        if not elem_text:
            return False
        result[key] = elem_text
        return True

    def get_elem_text( elem ):
        """Get the element's text content."""
        val = elem.get_attribute( "innerHTML" )
        # change how highlighted content is represented
        matches = list( re.finditer( r'<span class="hilite">(.*?)</span>', val ) )
        for mo in reversed(matches):
            val = val[:mo.start()] + "((" + mo.group(1) + "))" + val[mo.end():]
        # remove HTML tags
        return strip_html( val.strip() )

    def unload_ruleids( result, key, parent ):
        """Unload a list of ruleid's."""
        if not parent:
            return
        ruleids = []
        for elem in find_children( ".ruleid", parent ):
            ruleid = get_elem_text( elem )
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
            unload_elem( ruleref, "caption", find_child(".caption",elem) )
            unload_ruleids( ruleref, "ruleids", elem )
            rulerefs.append( ruleref )
        if rulerefs:
            result[key] = rulerefs

    def unload_index_sr( sr ): #pylint: disable=possibly-unused-variable
        """Unload an "index" search result."""
        result = {}
        unload_elem( result, "title", find_child("span.title",sr) )
        unload_elem( result, "subtitle", find_child(".subtitle",sr) )
        unload_elem( result, "content", find_child(".content",sr) )
        if unload_elem( result, "see_also", find_child(".see-also",sr) ):
            assert result["see_also"].startswith( "See also:" )
            result["see_also"] = [ s.strip() for s in result["see_also"][9:].split( "," ) ]
        unload_ruleids( result, "ruleids", find_child(".ruleids",sr) )
        unload_rulerefs( result, "rulerefs", find_child(".rulerefs",sr) )
        return result

    # unload the search results
    results = []
    for sr in find_children( "#search-results .sr"):
        classes = get_classes( sr )
        classes.remove( "sr" )
        assert len(classes) == 1 and classes[0].endswith( "-sr" )
        sr_type = classes[0][:-3]
        func = locals()[ "unload_{}_sr".format( sr_type ) ]
        sr = func( sr )
        sr["sr_type"] = sr_type
        results.append( sr )

    return results
