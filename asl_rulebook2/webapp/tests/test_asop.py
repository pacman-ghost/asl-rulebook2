""" Test the ASOP. """

import os
import json

from asl_rulebook2.webapp.tests.test_search import do_search
from asl_rulebook2.webapp.tests.utils import init_webapp, select_tabbed_page, \
    wait_for, wait_for_elem, find_child, find_children, unload_elem, unload_sr_text, get_image_filename, has_class

# ---------------------------------------------------------------------

def test_asop_nav( webdriver, webapp ):
    """Test the ASOP nav."""

    # initialize
    webapp.control_tests.set_data_dir( "asop" )
    init_webapp( webapp, webdriver )

    # load the ASOP
    fname = os.path.join( os.path.dirname(__file__), "fixtures/asop/asop/index.json" )
    with open( fname, "r" ) as fp:
        asop_index = json.load( fp )

    # check the nav
    select_tabbed_page( "nav", "asop" )
    nav = _unload_nav( False )
    chapters = asop_index["chapters"]
    for chapter_no, chapter in enumerate( chapters ):
        chapters[ chapter_no ] = {
            key: val for key, val in chapter.items()
            if key != "sniper_phase" and not key.startswith("_")
        }
        chapter.pop( "sniper_phase", None )
    assert nav == asop_index["chapters"]

    # check the footer
    footer = find_child( "#asop-footer" )
    assert "Sniper Attacks/Checks are possible" in footer.text
    images = [
        get_image_filename( c, full=True )
        for c in find_children( "img", footer )
    ]
    assert images == [
        "/asop/images/attacker.png",
        "/asop/images/defender.png",
        "/asop/images/both-players.png"
    ]

# ---------------------------------------------------------------------

def test_asop_content( webdriver, webapp ):
    """Test the ASOP content."""

    # initialize
    webapp.control_tests.set_data_dir( "asop" )
    init_webapp( webapp, webdriver )
    select_tabbed_page( "nav", "asop" )
    nav = _unload_nav( True )

    def load_asop_file( fname, as_json ):
        """Load an ASOP data file."""
        fname = os.path.join( base_dir, fname )
        if not os.path.isfile( fname ):
            return None
        with open( fname, "r" ) as fp:
            return json.load( fp ) if as_json else fp.read()

    # load the ASOP index
    base_dir = os.path.join( os.path.dirname(__file__), "fixtures/asop/asop/" )
    asop_index = load_asop_file( "index.json", True )

    def check_chapter( chapter_no, callbacks ):
        """Check the specified ASOP chapter."""

        # open the chapter
        expected_chapter = asop_index["chapters"][ chapter_no ]
        nav[ chapter_no ][ "elem" ].click()
        expected = len( expected_chapter["sections"] )
        wait_for( 2, lambda: len( find_children( "#asop .sections .section" ) ) == expected )

        # check the title
        title = find_child( "#asop .title" ).text
        expected = expected_chapter[ "caption" ]
        if expected_chapter.get( "sniper_phase" ):
            expected += "\u2020"
        assert title == expected
        chapter_id = find_child( "#asop" ).get_attribute( "data-chapterid" )
        assert chapter_id == expected_chapter["chapter_id"]

        # check the preamble
        expected_preamble = load_asop_file( "{}-0.html".format( chapter_id ), False )
        preamble = find_child( "#asop .preamble" ).text
        if preamble:
            # NOTE: We only check the first few characters since the data file is processed as a template,
            # so it may not match exactly what's in the UI.
            assert preamble[0:20] in expected_preamble
        else:
            assert preamble == ""

        # do any chapter-specific checks
        func = callbacks.get( "check_{}".format( chapter_id.replace("-","_") ) )
        if func:
            func()

        # check each section (in the combined view)
        expected_sections = expected_chapter[ "sections" ]
        section_elems = find_children( "#asop .sections .section" )
        assert len(expected_sections) == len(section_elems)
        for section_no in range( len(expected_sections) ):

            # check the section's caption
            caption = find_child( ".caption", section_elems[section_no] ).text
            assert caption == expected_sections[section_no]["caption"]

            # check the section's content
            section_id = "{}-{}".format( chapter_id, 1+section_no )
            expected_content = load_asop_file( section_id+".html", False )
            content = find_child( "ul", section_elems[section_no] ).text
            assert content[0:20] in expected_content

        # check each individual section
        for section_no, nav_section in enumerate( nav[chapter_no]["sections"] ):

            # click on the section in the nav pane
            find_child( "a", nav_section["elem"] ).click()

            # wait for the section's content to appear
            expected = expected_sections[ section_no ][ "caption" ]
            if expected_chapter.get( "sniper_phase" ):
                expected += "\u2020"
            wait_for( 2, lambda: find_child("#asop .title").text == expected )

            # check the preamble
            # NOTE: The preamble is part of the parent chapter, and so should remain unchanged.
            preamble = find_child( "#asop .preamble" ).text
            if preamble:
                assert preamble[0:20] in expected_preamble
            else:
                assert preamble == ""

            # check the section's content
            section_id = "{}-{}".format( chapter_id, 1+section_no )
            expected_content = load_asop_file( section_id+".html", False )
            sections = find_children( "#asop .sections .section" )
            assert len(sections) == 1
            content = find_child( "ul", sections[0] ).text
            assert content[0:20] in expected_content

            # do any section-specific checks
            func = callbacks.get( "check_{}_section".format( chapter_id.replace("-","_") ) )
            if func:
                func( 1+section_no )

    def check_pre_game(): #pylint: disable=possibly-unused-variable
        # check the DYO image in the preamble
        assert get_image_filename( find_child("#asop .preamble img.icon"), full=True ) == "/asop/images/dyo.png"
        # check the images in the sections
        images = set(
            get_image_filename( c, full=True )
            for c in find_children( "#asop .sections .section img.icon" )
        )
        assert images == set( [
            "/asop/images/dyo.png", "/asop/images/both-players.png"
        ] )
    def check_pre_game_section( section_no ): #pylint: disable=possibly-unused-variable
        if section_no == 1:
            # check the DYO image in the preamble
            assert get_image_filename( find_child("#asop .preamble img.icon"), full=True ) == "/asop/images/dyo.png"

    def check_rally(): #pylint: disable=possibly-unused-variable
        # check the EXC block in the preamble
        assert has_class( find_child( "#asop .preamble span" ), "exc" )

    def check_movement(): #pylint: disable=possibly-unused-variable
        # there should be 3 EXC blocks
        elems = [
            c for c in find_children( "#asop .sections .section span" )
            if has_class( c, "exc" )
        ]
        elems = set( e.text for e in elems ) # why are we seeing everything twice?! :-/
        assert len(elems) == 3
    def check_movement_section( section_no ): #pylint: disable=possibly-unused-variable
        # check an EXC block
        if section_no == 5:
            assert has_class( find_child( "#asop .sections .section span" ), "exc" )

    # check each chapter
    for i in range( 0, 8+1 ):
        check_chapter( i, locals() )

    # check error handling
    nav[ 9 ][ "elem" ].click()
    sections = find_children( "#asop .sections .section" )
    assert len(sections) == 0

# ---------------------------------------------------------------------

def test_asop_entries( webdriver, webapp ):
    """Test searching for individual ASOP entries."""

    # initialize
    webapp.control_tests.set_data_dir( "asop" )
    init_webapp( webapp, webdriver )

    def do_test( query_string, expected ):

        # do the search
        results = do_search( query_string )

        # check the search results
        assert len(results) == len(expected)
        for i in range( len(results) ):
            assert expected[i][0] in results[i]["content"]
            assert expected[i][1]in results[i]["content"]

        # make sure we can click through to the ASOP
        sr_elems = find_children( "#search-results .asop-entry-sr" )
        for sr_no, sr_elem in enumerate( sr_elems ):

            # click on the search result
            find_child( ".caption", sr_elem ).click()
            wait_for_elem( 2, "#asop" )

            # check the contents of the ASOP popup
            entries = find_children( "#asop .sections .section .entry" )
            assert len(entries) == 1
            assert expected[sr_no][0] in unload_sr_text( entries[0] )

            # check the nav pane
            panes = [
                c for c in find_children( "#accordian-asop .accordian-pane" )
                if find_child( ".entries", c ).value_of_css_property( "display" ) != "none"
            ]
            assert len(panes) == 1
            assert panes[0].get_attribute( "data-chapterid" ) == expected[sr_no][2]

            # return back to the Search nav pane
            select_tabbed_page( "nav", "search" )

    # do the tests
    do_test( "napalm", [
        [ "2.11A", "checking for any ((Napalm)) terrain-Blaze/weapon", "prep-fire" ]
    ] )
    do_test( "reverse", [
        [ "2.15A", "((Reverse)) Slopes", "prep-fire" ],
        [ "4.14D", "((Reverse)) Slopes", "defensive-fire" ],
    ] )
    do_test( '"mop up"', [
        [ "2.21A", "((Mop Up)) (A12.153)", "prep-fire" ]
    ] )
    do_test( '"crew become TI"', [
        [ "2.23A", "it and ((crew become TI))", "prep-fire" ],
        [ "4.22D", "it and ((crew become TI))", "defensive-fire" ],
    ] )

    # search for something that is not part of an "entry" div
    results = do_search( "porpoise" )
    assert results is None

# ---------------------------------------------------------------------

def _unload_nav( include_elems ):
    """Unload the ASOP nav."""

    chapters = []
    for chapter_elem in find_children( "#accordian-asop .accordian-pane" ):

        # unload the next chapter
        chapter = {
            "chapter_id": chapter_elem.get_attribute( "data-chapterid" ),
        }
        unload_elem( chapter, "caption", find_child(".title",chapter_elem) )
        if include_elems:
            chapter[ "elem" ] = chapter_elem

        # unload the chapter's sections
        chapter_elem.click() # nb: panes must be open to unload their sections :-/
        sections = []
        for section_elem in find_children( ".entry", chapter_elem ):
            sections.append( {
                "caption": section_elem.text,
            } )
            if include_elems:
                sections[-1]["elem"] = section_elem
        if sections:
            chapter[ "sections" ] = sections
        chapters.append( chapter )

    return chapters
