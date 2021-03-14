""" pytest support functions. """

import os
import threading
import urllib.request
from urllib.error import URLError
import json
import re
import logging
import tempfile

import pytest
from flask import url_for

from asl_rulebook2.webapp import app
from asl_rulebook2.webapp.tests.control_tests import ControlTests
from asl_rulebook2.webapp.tests.utils import wait_for

_FLASK_WEBAPP_PORT = 5021

_pytest_options = None

# ---------------------------------------------------------------------

def pytest_addoption( parser ):
    """Configure pytest options."""

    # NOTE: This file needs to be in the project root for this to work :-/

    # add test options
    parser.addoption(
        "--webapp", action="store", dest="webapp_url", default=None,
        help="Webapp server to test against."
    )
    parser.addoption(
        "--webdriver", action="store", dest="webdriver", default="chrome",
        help="Webdriver to use (Chrome/Firefox)."
    )
    parser.addoption(
        "--headless", action="store_true", dest="headless", default=False,
        help="Run the tests headless."
    )
    parser.addoption(
        "--window-size", action="store", dest="window_size", default="1000x700",
        help="Browser window size."
    )

    # add test options
    parser.addoption(
        "--easlrb", action="store", dest="easlrb_path", default=None,
        help="Directory containing the MMP eASLRB PDF and extracted data file(s)."
    )

    # add test options
    parser.addoption(
        "--short-tests", action="store_true", dest="short_tests", default=False,
        help="Skip running the longer tests."
    )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def pytest_configure( config ):
    """Called after command-line options have been parsed."""
    global _pytest_options
    _pytest_options = config.option
    # notify the test suites about the pytest options
    import asl_rulebook2.tests
    asl_rulebook2.tests.pytest_options = _pytest_options
    import asl_rulebook2.webapp.tests
    asl_rulebook2.webapp.tests.pytest_options = _pytest_options

# ---------------------------------------------------------------------

_webapp = None

@pytest.fixture( scope="function" )
def webapp():
    """Launch the webapp."""

    # get the global webapp fixture
    global _webapp
    if _webapp is None:
        _webapp = _make_webapp()

    # reset the remote webapp server
    _webapp.control_tests.start_tests()

    # return the webapp to the caller
    yield _webapp

    # reset the remote webapp server
    _webapp.control_tests.end_tests()

def _make_webapp():
    """Create the global webapp fixture."""

    # initialize
    webapp_url = _pytest_options.webapp_url
    if webapp_url and not webapp_url.startswith( "http://" ):
        webapp_url = "http://" + webapp_url
    app.base_url = webapp_url if webapp_url else "http://localhost:{}".format( _FLASK_WEBAPP_PORT )
    logging.disable( logging.CRITICAL )

    # initialize
    # WTF?! https://github.com/pallets/flask/issues/824
    def make_webapp_url( endpoint, **kwargs ):
        """Generate a webapp URL."""
        with app.test_request_context():
            url = url_for( endpoint, _external=True, **kwargs )
            url = url.replace( "http://localhost", app.base_url )
            return url
    app.url_for = make_webapp_url

    # check if we need to start a local webapp server
    if not webapp_url:
        # yup - make it so
        # NOTE: We run the server thread as a daemon so that it won't prevent the tests from finishing
        # when they're done. However, this makes it difficult to know when to shut the server down,
        # and, in particular, clean up the gRPC service. We send an EndTests message at the end of each test,
        # which gives the remote server a chance to clean up then. It's not perfect (e.g. if the tests fail
        # or otherwise finish eearly before they get a chance to send the EndTests message), but we can
        # live with it.
        thread = threading.Thread(
            target = lambda: app.run( host="0.0.0.0", port=_FLASK_WEBAPP_PORT, use_reloader=False ),
            daemon = True
        )
        thread.start()
        # wait for the server to start up
        def is_ready():
            """Try to connect to the webapp server."""
            try:
                resp = urllib.request.urlopen( app.url_for( "ping" ) ).read()
                assert resp == b"pong"
                return True
            except URLError:
                return False
            except Exception as ex: #pylint: disable=broad-except
                assert False, "Unexpected exception: {}".format( ex )
        wait_for( 5, is_ready )

    # set up control of the remote webapp server
    try:
        resp = json.load(
            urllib.request.urlopen( app.url_for( "get_control_tests" ) )
        )
    except urllib.error.HTTPError as ex:
        if ex.code == 404:
            raise RuntimeError( "Can't get the test control port - has remote test control been enabled?" ) from ex
        raise
    port_no = resp.get( "port" )
    if not port_no:
        raise RuntimeError( "The webapp server is not running the test control service." )
    mo = re.search( r"^http://(.+):\d+$", app.base_url )
    addr = "{}:{}".format( mo.group(1), port_no )
    app.control_tests = ControlTests( addr )

    return app

# ---------------------------------------------------------------------

@pytest.fixture( scope="session" )
def webdriver():
    """Return a webdriver that can be used to control a browser."""

    # initialize
    driver = _pytest_options.webdriver
    from selenium import webdriver as wd
    if driver == "firefox":
        options = wd.FirefoxOptions()
        options.headless = _pytest_options.headless
        driver = wd.Firefox(
            options = options,
            service_log_path = os.path.join( tempfile.gettempdir(), "geckodriver.log" )
        )
    elif driver == "chrome":
        options = wd.ChromeOptions()
        options.headless = _pytest_options.headless
        options.add_argument( "--disable-gpu" )
        driver = wd.Chrome( options=options )
    else:
        raise RuntimeError( "Unknown webdriver: {}".format( driver ) )

    # set the browser size
    words = _pytest_options.window_size.split( "x" )
    driver.set_window_size( int(words[0]), int(words[1]) )

    # return the webdriver to the caller
    try:
        yield driver
    finally:
        driver.quit()
