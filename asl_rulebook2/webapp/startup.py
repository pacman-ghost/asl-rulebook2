""" Manage the startup process. """

import logging
from collections import defaultdict

from flask import jsonify

from asl_rulebook2.webapp import app
from asl_rulebook2.webapp.content import load_content_sets
from asl_rulebook2.webapp.search import init_search

_logger = logging.getLogger( "startup" )
_startup_msgs = None

# ---------------------------------------------------------------------

def init_webapp():
    """Initialize the webapp.

    IMPORTANT: This is called on the first Flask request, but can also be called multiple times
    after that by the test suite, to reset the webapp before each test.
    """

    # initialize
    global _startup_msgs
    _startup_msgs = StartupMsgs()

    # initialize the webapp
    load_content_sets( _startup_msgs, _logger )
    init_search( _startup_msgs, _logger )

# ---------------------------------------------------------------------

@app.route( "/startup-msgs" )
def get_startup_msgs():
    """Return any messages issued during startup."""
    return jsonify( _startup_msgs.msgs )

# ---------------------------------------------------------------------

class StartupMsgs:
    """Store messages issued during startup."""

    def __init__( self ):
        self.msgs = defaultdict( list )

    #pylint: disable=missing-function-docstring
    def info( self, msg, msg_info=None ):
        return self._add_msg( "info", msg, msg_info )
    def warning( self, msg, msg_info=None ):
        return self._add_msg( "warning", msg, msg_info )
    def error( self, msg, msg_info=None ):
        return self._add_msg( "error", msg, msg_info )

    def _add_msg( self, msg_type, msg, msg_info ):
        """Add a startup message."""
        if msg_info:
            self.msgs[ msg_type ].append( ( msg, msg_info ) )
            getattr( _logger, msg_type )( "%s\n  %s", msg, msg_info )
        else:
            self.msgs[ msg_type ].append( msg )
            getattr( _logger, msg_type )( "%s", msg )
