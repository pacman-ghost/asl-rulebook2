""" Global definitions. """

import threading

from flask import request

from asl_rulebook2.webapp import app
from asl_rulebook2.webapp.config.constants import APP_NAME, APP_VERSION

cleanup_handlers = []

socketio_server = None

# ---------------------------------------------------------------------

_init_lock = threading.Lock()
_init_done = False

def on_request():
    """Called before each request."""
    if request.path == "/control-tests":
        # NOTE: The test suite calls $/control-tests to find out which port the gRPC test control service
        # is running on, which is nice since we don't need to configure both ends with a predefined port.
        # However, we don't want this call to trigger initialization, since the tests will often want to
        # configure the remote webapp before loading the main page.
        return
    if request.path == "/ping":
        # NOTE: The test suite pings the server to detect when it's up.
        return
    with _init_lock:
        global _init_done
        if not _init_done or (request.path == "/" and request.args.get("reload")):
            try:
                from asl_rulebook2.webapp.startup import init_webapp
                init_webapp()
            finally:
                # NOTE: It's important to set this, even if initialization failed, so we don't
                # try to initialize again.
                _init_done = True

# ---------------------------------------------------------------------

@app.context_processor
def inject_template_params():
    """Inject template parameters into Jinja2."""
    web_debug = app.config.get( "WEB_DEBUG" )
    return {
        "APP_NAME": APP_NAME,
        "APP_VERSION": APP_VERSION,
        "WEB_DEBUG": web_debug,
        "WEB_DEBUG_MIN": "" if web_debug else ".min",
    }
