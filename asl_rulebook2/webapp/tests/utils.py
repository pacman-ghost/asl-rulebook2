""" Helper utilities. """

from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException

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

def find_child( sel, parent=None ):
    """Find a single child element."""
    try:
        if parent is None:
            parent = _webdriver
        return parent.find_element_by_css_selector( sel )
    except NoSuchElementException:
        return None

# ---------------------------------------------------------------------

def wait_for( timeout, func ):
    """Wait for a condition to become true."""
    WebDriverWait( _webdriver, timeout, poll_frequency=0.1 ).until(
        lambda driver: func()
    )
