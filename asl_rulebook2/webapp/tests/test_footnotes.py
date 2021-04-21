""" Test footnotes. """

import lxml.html

from asl_rulebook2.webapp.tests.utils import init_webapp, \
    find_children, wait_for, set_stored_msg_marker, get_last_footnote_msg
from asl_rulebook2.webapp.tests.test_search import do_search

# ---------------------------------------------------------------------

def test_footnotes( webdriver, webapp ):
    """Test footnotes."""

    # initialize
    webapp.control_tests.set_data_dir( "footnotes" )
    init_webapp( webapp, webdriver )

    # bring up the ruleid's and locate the ruleid links
    do_search( "document" )
    def remove_brackets( val ):
        assert val.startswith( "[" ) and val.endswith( "]" )
        return val[1:-1]
    ruleid_elems = {
        remove_brackets( c.text ): c
        for c in find_children( "#search-results .ruleid" )
    }

    def do_test( ruleid, expected ):
        # click on the specified ruleid and wait for the footnote to appear
        marker = set_stored_msg_marker( "footnote" )
        ruleid_elems[ ruleid ].click()
        wait_for( 2, lambda: get_last_footnote_msg() != marker )
        # locate the footnote(s)
        footnotes = []
        root = lxml.html.fragment_fromstring( get_last_footnote_msg() )
        if root.attrib["class"] == "footnote":
            # this is a single footnote
            footnote_elems = [ root ]
            get_content = lambda fnote: fnote.find( "div[@class='content']" ).text
        else:
            # there are multiple footnotes
            footnote_elems = root.findall( "div[@class='footnote']" )
            get_content = lambda fnote: "".join( fnote.xpath( "text()" ) )
        # extract content from each footnote
        for footnote in footnote_elems:
            header = footnote.find( "div[@class='header']" )
            footnotes.append( {
                "caption": header.find( "span[@class='caption']" ).text,
                "footnote_id": remove_brackets( header.find( "span[@class='footnote-id']" ).text ),
                "content": get_content( footnote )
            } )
        assert footnotes == expected

    # do the tests (content set 1)
    do_test( "1a.1", [ {
        "caption": "Alpha (1a.1)", "footnote_id": "X1",
        "content": "This footnote is for ruleid 1a.1."
    } ] )
    do_test( "1a.2", [ {
        "caption": "Bravo (1a.2)", "footnote_id": "X2",
        "content": "This footnote is for ruleid 1a.2."
    } ] )
    do_test( "1b.1", [ {
        "caption": "Charlie (1b.1)", "footnote_id": "X10",
        "content": "This footnote is for ruleid 1b1.1."
    }, {
        "caption": "Delta (1b.1)", "footnote_id": "X11",
        "content": "This footnote is also for ruleid 1b1.1."
    } ] )
    do_test( "1b.2", [ {
        "caption": "1b.2", "footnote_id": "X20",
        "content": None
    } ] )

    # do the tests (content set 2)
    do_test( "2.1", [ {
        "caption": "Mike (2.1)", "footnote_id": "Y1",
        "content": "This footnote is for ruleid 2.1."
    } ] )
    do_test( "2.2", [ {
        "caption": "November (2.2)", "footnote_id": "Y2",
        "content": "This footnote is for ruleid 2.2."
    } ] )
