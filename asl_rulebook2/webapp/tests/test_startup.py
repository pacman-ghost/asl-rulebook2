""" Test the startup process. """

from asl_rulebook2.webapp.tests.utils import init_webapp, \
    wait_for_warning_msg, wait_for_error_msg, find_children

# ---------------------------------------------------------------------

def test_load_content_docs( webapp, webdriver ):
    """Test loading content docs."""

    # test handling of an invalid data directory
    webapp.control_tests.set_data_dir( "_unknown_" )
    init_webapp( webapp, webdriver )
    wait_for_error_msg( 2, "Invalid data directory.", contains=True )

    # test handling of an invalid index file
    webapp.control_tests.set_data_dir( "invalid-index" )
    init_webapp( webapp, webdriver )
    wait_for_error_msg( 2, "Couldn't load \"test.index\".", contains=True )
    # NOTE: If we can't load the index file, the content doc is useless and we don't load it at all.
    # If any of the associated files are invalid, the content doc is loaded (i.e. a tab will be shown
    # for it), and we degrade gracefully.
    assert len( find_children( "#content .tabbed-page" ) ) == 0

    # test handling of an invalid targets file
    webapp.control_tests.set_data_dir( "invalid-targets" )
    init_webapp( webapp, webdriver )
    wait_for_warning_msg( 2, "Couldn't load \"test.targets\".", contains=True )
    assert len( find_children( "#content .tabbed-page" ) ) == 1

    # test handling of an invalid footnotes file
    webapp.control_tests.set_data_dir( "invalid-footnotes" )
    init_webapp( webapp, webdriver )
    wait_for_warning_msg( 2, "Couldn't load \"test.footnotes\".", contains=True )
    assert len( find_children( "#content .tabbed-page" ) ) == 1

# ---------------------------------------------------------------------

def test_init_search( webapp, webdriver ):
    """Test initializing the search engine."""

    # test handling of an invalid search replacements file
    webapp.control_tests.set_data_dir( "invalid-search-replacements" )
    init_webapp( webapp, webdriver )
    wait_for_warning_msg( 2, "Can't load user search replacements.", contains=True )

    # test handling of an invalid search aliases file
    webapp.control_tests.set_data_dir( "invalid-search-aliases" )
    init_webapp( webapp, webdriver )
    wait_for_warning_msg( 2, "Can't load user search aliases.", contains=True )

    # test handling of an invalid search synonyms file
    webapp.control_tests.set_data_dir( "invalid-search-synonyms" )
    init_webapp( webapp, webdriver )
    wait_for_warning_msg( 2, "Can't load user search synonyms.", contains=True )
