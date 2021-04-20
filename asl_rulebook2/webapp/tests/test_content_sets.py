""" Test how content sets are handled. """

from asl_rulebook2.webapp.tests.utils import init_webapp, select_tabbed_page, get_curr_target, \
    set_stored_msg_marker, get_last_error_msg, find_child, find_children, wait_for, has_class
from asl_rulebook2.webapp.tests.test_search import do_search

# ---------------------------------------------------------------------

def test_targets( webapp, webdriver ):
    """Test showing targets from different content sets."""

    # initialize
    webapp.control_tests.set_data_dir( "content-sets" )
    init_webapp( webapp, webdriver, add_empty_doc=1 )

    # bring up all the targets
    results = do_search( "content" )
    results = {
        sr["title"]: [
            [ rref["caption"], rref["ruleids"] ]
            for rref in sr["rulerefs"]
        ] for sr in results
    }
    assert results == {
        "((Content)) Set 1": [
            [ "Main document", [ "1a", "2a", "3a", "4a", "5a", "6a" ] ],
            [ "Linked document", [ "1b", "2b", "3b", "4b", "5b", "6b" ] ],
        ],
        "((Content)) Set 2": [
            [ "The only document", [ "cs2a", "cs2b", "cs2c", "cs2d", "cs2e", "cs2f" ] ]
        ],
        "Unknown ruleid": [
            [ "Incorrect ruleref", [ "cs2a" ] ]
        ],
    }

    # check that the ruleid links are enabled/disabled correctly
    ruleid_elems = {}
    for sr_elem in find_children( "#search-results .sr" ):
        title = find_child( ".title", sr_elem ).text
        for ruleid_elem in find_children( ".ruleid", sr_elem ):
            link = find_child( "a", ruleid_elem )
            if title == "Unknown ruleid":
                assert link is None
            else:
                assert link
                assert link.text not in ruleid_elems
                ruleid_elems[ link.text ] = ruleid_elem

    def do_test( ruleid, expected ):
        ruleid_elems[ ruleid ].click()
        wait_for( 2, lambda: get_curr_target() == (expected, ruleid) )

    # test clicking on ruleid's
    do_test( "4b", "content-set-1!linked" )
    do_test( "1a", "content-set-1!" )
    do_test( "cs2d", "content-set-2!" )
    select_tabbed_page( "content", "empty" )
    do_test( "1b", "content-set-1!linked" )

# ---------------------------------------------------------------------

def test_chapters( webapp, webdriver ):
    """Test handling of chapters from different content sets."""

    # initialize
    webapp.control_tests.set_data_dir( "content-sets" )
    init_webapp( webapp, webdriver )

    # check the chapters have been loaded correctly
    select_tabbed_page( "nav", "chapters" )
    chapters = _unload_chapters()
    assert chapters == [
        { "title": "Page 1",
          "entries": [ "Top of the page", "Middle of the page", "Bottom of the page" ]
        },
        { "title": "Page 2",
          "entries": [ "Top of the page", "Middle of the page", "Bottom of the page", "Link to page 2", "No ruleid" ]
        },
        { "title": "Linked document - Page 1",
          "entries": [ "Top of the page", "Middle of the page", "Bottom of the page" ]
        },
        { "title": "Linked document - Page 2",
          "entries": [ "Top of the page", "Middle of the page", "Bottom of the page", "Unknown ruleid" ]
        },
        { "title": "Page 1 (Content Set 2)",
          "entries": [ "Top of the page", "Middle of the page", "Bottom of the page" ]
        },
        { "title": "Page 2 (Content Set 2)",
          "entries": [ "Top of the page", "Middle of the page", "Bottom of the page" ]
        },
    ]

    # check that the chapter section with a missing target is not clickable
    elems = find_children( "#accordian-chapters .accordian-pane" )
    assert len(elems) == 6
    elems = find_children( ".entry", elems[1] )
    assert len(elems) == 5
    elem = elems[4]
    assert find_child( "a", elem ) is None

    def do_test( chapter_no, entry_no, expected ):
        """Click on a chapter entry."""
        select_tabbed_page( "nav", "chapters" )
        elems = find_children( "#accordian-chapters .accordian-pane" )
        chapter_elem = elems[ chapter_no ]
        _select_chapter( chapter_elem )
        entries = find_children( ".entries .entry a", chapter_elem )
        marker = set_stored_msg_marker( "error" )
        entries[ entry_no ].click()
        if isinstance( expected, tuple ):
            wait_for( 2, lambda: get_curr_target() == expected )
            assert get_last_error_msg() == marker
        else:
            assert isinstance( expected, str )
            assert expected in get_last_error_msg()

    # click on some chapter entries
    do_test( 1, 2, ( "content-set-1!", "6a" ) )
    do_test( 4, 0, ( "content-set-2!", "cs2a" ) )
    do_test( 2, 1, ( "content-set-1!linked", "2b" ) )
    do_test( 1, 3, ( "content-set-1!", 2 ) )

    # try to show an unknown target
    do_test( 3, 3, "Unknown ruleid:" )

# ---------------------------------------------------------------------

def _unload_chapters():
    """Unload the chapters and their entries."""
    chapters = []
    for chapter_elem in find_children( "#accordian-chapters .accordian-pane" ):
        _select_chapter( chapter_elem ) # nb: panes need to be expanded to unload their content
        chapters.append( {
            "title": find_child( ".title", chapter_elem ).text,
            "entries": [ c.text for c in find_children( ".entries .entry", chapter_elem ) ],
        } )
    return chapters

def _select_chapter( chapter_elem ):
    """Expand a chapter."""
    assert has_class( chapter_elem, "accordian-pane" )
    # expand the specified chapter (nb: we assume it's currently collapsed)
    find_child( ".title", chapter_elem ).click()
    wait_for( 2, lambda: find_child( ".entries", chapter_elem ).is_displayed() )
    # make sure all other chapters are collapsed
    parent = chapter_elem.find_element_by_xpath( ".." )
    assert has_class( parent, "accordian" )
    for elem in find_children( ".accordian-pane", parent ):
        is_expanded = find_child( ".entries", elem ).is_displayed()
        if elem == chapter_elem:
            assert is_expanded
        else:
            assert not is_expanded
