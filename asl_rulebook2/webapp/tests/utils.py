""" Helper utilities. """

import sys
import os
import uuid

from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from asl_rulebook2.webapp import tests as webapp_tests

_webapp = None
_webdriver = None

# ---------------------------------------------------------------------

def init_webapp( webapp, webdriver, **options ):
    """Initialize the webapp."""

    # initialize
    global _webapp, _webdriver
    _webapp = webapp
    _webdriver = webdriver
    options = {
        key.replace("_","-"): val
        for key, val in options.items()
    }

    # load the webapp
    if get_pytest_option("webdriver") == "chrome" and get_pytest_option("headless"):
        # FUDGE! Headless Chrome doesn't want to show the PDF in the browser,
        # it downloads the file and saves it in the current directory :wtf:
        options["no-content"] = 1
    options["store-msgs"] = 1 # nb: so that we can retrive notification messages
    options["no-animations"] = 1
    options["reload"] = 1 # nb: force the webapp to reload
    webdriver.get( webapp.url_for( "main", **options ) )
    _wait_for_webapp()

    # reset the user settings
    webdriver.delete_all_cookies()

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _wait_for_webapp():
    """Wait for the webapp to finish initialization."""
    timeout = 5
    wait_for( timeout, lambda: find_child("#_mainapp-loaded_") )

# ---------------------------------------------------------------------

def select_tabbed_page( parent_sel, tab_id ):
    """Select a tabbed page."""
    tabbed_pages = find_child( ".tabbed-pages", find_child(parent_sel) )
    btn = find_child( ".tab-strip .tab[data-tabid='{}']".format( tab_id ), tabbed_pages )
    btn.click()
    def find_tabbed_page():
        elem = find_child( ".tabbed-page[data-tabid='{}']".format( tab_id ), tabbed_pages )
        return elem and elem.is_displayed()
    wait_for( 2, find_tabbed_page )

# ---------------------------------------------------------------------

def get_nav_panels():
    """Get the available nav panels."""
    return _get_tab_ids( "#nav .tab-strip" )

def get_content_docs():
    """Get the available content docs."""
    return _get_tab_ids( "#content .tab-strip" )

def _get_tab_ids( sel ):
    """Get the tabs in a tab-strip."""
    tabs = find_children( "{} .tab".format( sel ) )
    return [ tab.get_attribute( "data-tabid" ) for tab in tabs ]

def get_curr_target():
    """Get the currently-shown target."""
    # check the active tab
    elem = find_child( "#content .tab-strip .tab.active" )
    if not elem:
        return ( None, None )
    tab_id = elem.get_attribute( "data-tabid" )
    # check the current ruleid
    elem = find_child( "#content .tabbed-page[data-tabid='{}'] .content-doc".format( tab_id ) )
    ruleid = elem.get_attribute( "data-ruleid" )
    return ( tab_id, ruleid )

# ---------------------------------------------------------------------

#pylint: disable=multiple-statements,missing-function-docstring
def get_last_info(): return get_stored_msg( "info" )
def get_last_warning_msg(): return get_stored_msg( "warning" )
def get_last_error_msg(): return get_stored_msg( "error" )
#pylint: enable=multiple-statements,missing-function-docstring

def get_stored_msg( msg_type ):
    """Get a message stored for us by the front-end."""
    elem = find_child( "#_last-{}-msg_".format(msg_type), _webdriver )
    assert elem.tag_name == "textarea"
    return elem.get_attribute( "value" )

def set_stored_msg( msg_type, val ):
    """Set a message for the front-end."""
    elem = find_child( "#_last-{}-msg_".format(msg_type), _webdriver )
    assert elem.tag_name == "textarea"
    _webdriver.execute_script( "arguments[0].value = arguments[1]", elem, val )

def set_stored_msg_marker( msg_type ):
    """Store marker text in the message buffer (so we can tell if the front-end changes it)."""
    marker = "marker:{}:{}".format( msg_type, uuid.uuid4() )
    set_stored_msg( msg_type, marker )
    return marker

# ---------------------------------------------------------------------

def find_child( sel, parent=None ):
    """Find a single child element."""
    try:
        if parent is None:
            parent = _webdriver
        return parent.find_element_by_css_selector( sel )
    except NoSuchElementException:
        return None

def find_children( sel, parent=None ):
    """Find child elements."""
    try:
        if parent is None:
            parent = _webdriver
        return parent.find_elements_by_css_selector( sel )
    except NoSuchElementException:
        return None

def get_classes( elem ):
    """Get the element's classes."""
    classes = elem.get_attribute( "class" )
    return classes.split()

def has_class( elem, class_name ):
    """Check if an element has a specified CSS class."""
    return class_name in get_classes( elem )

def get_image_filename( elem ):
    """Get the filename of an <img> element."""
    if elem is None:
        return None
    assert elem.tag_name == "img"
    return os.path.basename( elem.get_attribute( "src" ) )

# ---------------------------------------------------------------------

def wait_for_elem( timeout, sel, parent=None ):
    """Wait for an element to appear."""
    elem = None
    def check_elem():
        nonlocal elem
        elem = find_child( sel, parent )
        return elem is not None and elem.is_displayed()
    wait_for( timeout, check_elem )
    return elem

def wait_for( timeout, func ):
    """Wait for a condition to become true."""
    WebDriverWait( _webdriver, timeout, poll_frequency=0.1 ).until(
        lambda driver: func()
    )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

#pylint: disable=missing-function-docstring
def wait_for_info_msg( timeout, expected, contains=True ):
    return _do_wait_for_msg( timeout, "info", expected, contains )
def wait_for_warning_msg( timeout, expected, contains=True ):
    return _do_wait_for_msg( timeout, "warning", expected, contains )
def wait_for_error_msg( timeout, expected, contains=True ):
    return _do_wait_for_msg( timeout, "error", expected, contains )
#pylint: enable=missing-function-docstring

def _do_wait_for_msg( timeout, msg_type, expected, contains ):
    """Wait for a message to be issued."""
    func = getattr( sys.modules[__name__], "get_last_{}_msg".format( msg_type ) )
    try:
        wait_for( timeout,
            lambda: expected in func() if contains else expected == func()
        )
    except TimeoutException:
        print( "ERROR: Didn't get expected {} message: {}".format( msg_type, expected ) )
        print( "- last {} message: {}".format( msg_type, func() ) )
        assert False

# ---------------------------------------------------------------------

def get_pytest_option( opt ):
    """Get a pytest configuration option."""
    return getattr( webapp_tests.pytest_options, opt )
