""" Test annotations. """

from asl_rulebook2.webapp.tests.utils import init_webapp, \
    find_child, find_children, wait_for_elem, check_sr_filters
from asl_rulebook2.webapp.tests.test_search import do_search, unload_elem

# ---------------------------------------------------------------------

def test_full_errata( webapp, webdriver ):
    """Test handling of an errata that has everything."""

    # initialize
    webapp.control_tests.set_data_dir( "annotations" )
    init_webapp( webapp, webdriver )
    check_sr_filters( [ "index", "errata" ] )

    # bring up the errata and check it in the search results
    results = do_search( "erratum" )
    expected = {
        "sr_type": "anno",
        "caption": "E1",
        "icon": "errata.png",
        "content": "This is a test ((erratum)).",
        "source": "Test Fixture"
    }
    assert len(results) == 1
    result = results[0]
    assert result == expected

    # bring up the errata in the rule info popup and check it there
    find_child( "#search-results .auto-ruleid" ).click()
    anno = _unload_rule_info_anno()
    expected = {
        "caption": "E1",
        "icon": "errata.png",
        "content": "This is a test erratum.",
        "source": "Test Fixture"
    }
    assert anno == expected

# ---------------------------------------------------------------------

def test_empty_errata( webapp, webdriver ):
    """Test handling of an errata that has nothing in it."""

    # initialize
    webapp.control_tests.set_data_dir( "annotations" )
    init_webapp( webapp, webdriver )

    # bring up the errata amd check it in the rule info popup
    do_search( "empty" )
    anno = _unload_rule_info_anno()
    expected = {
        "caption": "E0",
        "icon": "errata.png",
    }
    assert anno == expected

# ---------------------------------------------------------------------

def unload_anno( anno_elem ):
    """Unload an annotation from the UI."""
    anno = {}
    unload_elem( anno, "caption", find_child(".caption",anno_elem), adjust_hilites=True )
    unload_elem( anno, "content", find_child(".content",anno_elem), adjust_hilites=True )
    img = find_child( "img.icon", anno_elem )
    unload_elem( anno, "icon", img )
    source = img.get_attribute( "title" )
    if source:
        anno["source"] = source
    return anno

def _unload_rule_info_anno():
    """Unload an annotation from the rule info popup."""
    popup = wait_for_elem( 2, "#rule-info" )
    assert popup
    elems = find_children( ".anno", popup )
    assert len(elems) == 1 # nb: we assume there's only 1 annotation
    return unload_anno( elems[0] )
