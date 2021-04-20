""" Helper utilities. """

import sys
import os
import urllib.request
import json
import re
import uuid

from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from asl_rulebook2.utils import strip_html
from asl_rulebook2.webapp import tests as webapp_tests

_webapp = None
_webdriver = None

# ---------------------------------------------------------------------

def init_webapp( webapp, webdriver, **options ):
    """Initialize the webapp."""

    # initialize
    expected_warnings = options.pop( "warnings", [] )
    expected_errors = options.pop( "errors", [] )

    # initialize
    global _webapp, _webdriver
    _webapp = webapp
    _webdriver = webdriver
    options = {
        key.replace("_","-"): val
        for key, val in options.items()
    }

    # load the webapp
    webapp.control_tests.set_app_config_val( "BLOCKING_FIXUP_CONTENT", True )
    webdriver.get( make_webapp_main_url( options ) )
    _wait_for_webapp()

    # make sure there were no errors or warnings
    startup_msgs = json.load(
        urllib.request.urlopen( webapp.url_for( "get_startup_msgs" ) )
    )
    errors = startup_msgs.pop( "error", [] )
    errors = [ e[0] for e in errors ]
    assert set( errors ) == set( expected_errors )
    warnings = startup_msgs.pop( "warning", [] )
    warnings = [ w[0] for w in warnings ]
    assert set( warnings ) == set( expected_warnings )
    assert not startup_msgs

    # reset the user settings
    webdriver.delete_all_cookies()

def make_webapp_main_url( options ):
    """Generate the webapp URL."""
    if get_pytest_option("webdriver") == "chrome" and get_pytest_option("headless"):
        # FUDGE! Headless Chrome doesn't want to show the PDF in the browser,
        # it downloads the file and saves it in the current directory :wtf:
        options["no-content"] = 1
    options["store-msgs"] = 1 # nb: so that we can retrive notification messages
    options["no-animations"] = 1
    options["reload"] = 1 # nb: force the webapp to reload
    return _webapp.url_for( "main", **options )

def refresh_webapp( webdriver ):
    """Refresh the webapp."""
    webdriver.refresh()
    _wait_for_webapp()

def _wait_for_webapp():
    """Wait for the webapp to finish initialization."""
    timeout = 5
    wait_for( timeout, lambda: find_child("#_mainapp-loaded_") )

# ---------------------------------------------------------------------

def select_tabbed_page( tabbed_pages_id, tab_id ):
    """Select a tabbed page."""
    tabbed_pages = find_child( "#tabbed-pages-" + tabbed_pages_id )
    assert tabbed_pages
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

def check_sr_filters( expected ):
    """Check the search result filter checkboxes."""
    sr_filters = find_child( "#search-box .sr-filters" )
    if expected:
        elems = [
            c.get_attribute("name") for c in find_children( "input[type='checkbox']", sr_filters )
            if c.is_displayed()
        ]
        assert all( e.startswith("show-") and e.endswith("-sr") for e in elems )
        elems = [ e[5:-3] for e in elems ]
        assert elems == expected
    else:
        assert not sr_filters.is_displayed()

# ---------------------------------------------------------------------

#pylint: disable=multiple-statements,missing-function-docstring
def get_last_info(): return get_stored_msg( "info" )
def get_last_warning_msg(): return get_stored_msg( "warning" )
def get_last_error_msg(): return get_stored_msg( "error" )
def get_last_footnote_msg(): return get_stored_msg( "footnote" )
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

def unload_elem( save_loc, key, elem, adjust_hilites=False ):
    """Unload a single element."""
    if not elem:
        return False
    if elem.tag_name in ("div", "span"):
        val = unload_sr_text( elem ) if adjust_hilites else elem.text
    elif elem.tag_name == "img":
        val = get_image_filename( elem )
    else:
        assert False, "Unknown element type: " + elem.tag_name
        return False
    if not val:
        return False
    save_loc[ key ] = val
    return True

def unload_sr_text( elem ):
    """Unload a text value that is part of a search result."""
    val = elem.get_attribute( "innerHTML" )
    # change how highlighted content is represented
    matches = list( re.finditer( r'<span class="hilite">(.*?)</span>', val ) )
    for mo in reversed(matches):
        val = val[:mo.start()] + "((" + mo.group(1) + "))" + val[mo.end():]
    # remove HTML tags
    val = strip_html( val ).strip()
    return val

def get_image_filename( elem, full=False ):
    """Get the filename of an <img> element."""
    if elem is None:
        return None
    assert elem.tag_name == "img"
    src = elem.get_attribute( "src" )
    if full:
        src = re.sub( r"^http://[^/]+", "", src )
    else:
        src = os.path.basename( src )
    return re.sub( r"/+", "/", src )

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
