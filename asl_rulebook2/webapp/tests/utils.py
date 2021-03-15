""" Helper utilities. """

from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException

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

    # load the webapp
    if get_pytest_option("webdriver") == "chrome" and get_pytest_option("headless"):
        # FUDGE! Headless Chrome doesn't want to show the PDF in the browser,
        # it downloads the file and saves it in the current directory :wtf:
        options["no-content"] = 1
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

# ---------------------------------------------------------------------

def wait_for( timeout, func ):
    """Wait for a condition to become true."""
    WebDriverWait( _webdriver, timeout, poll_frequency=0.1 ).until(
        lambda driver: func()
    )

# ---------------------------------------------------------------------

def get_pytest_option( opt ):
    """Get a pytest configuration option."""
    return getattr( webapp_tests.pytest_options, opt )
