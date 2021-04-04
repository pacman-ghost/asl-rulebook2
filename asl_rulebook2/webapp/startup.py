""" Manage the startup process. """

import logging
from collections import defaultdict

from flask import jsonify

from asl_rulebook2.webapp import app
from asl_rulebook2.webapp.content import load_content_sets
from asl_rulebook2.webapp.search import init_search
from asl_rulebook2.webapp.rule_info import init_qa, init_errata, init_annotations
from asl_rulebook2.webapp.asop import init_asop
from asl_rulebook2.webapp.utils import parse_int

_logger = logging.getLogger( "startup" )
_startup_msgs = None

_capabilities = None

# ---------------------------------------------------------------------

def init_webapp():
    """Initialize the webapp.

    IMPORTANT: This is called on the first Flask request, but can also be called multiple times
    after that by the test suite, to reset the webapp before each test.
    """

    # initialize
    global _startup_msgs, _capabilities
    _startup_msgs = StartupMsgs()
    _capabilities = {}

    # initialize the webapp
    content_sets = load_content_sets( _startup_msgs, _logger )
    if content_sets:
        _capabilities[ "content-sets" ] = True
    qa = init_qa( _startup_msgs, _logger )
    if qa:
        _capabilities[ "qa" ] = True
    errata = init_errata( _startup_msgs, _logger )
    if errata:
        _capabilities[ "errata" ] = True
    user_anno = init_annotations( _startup_msgs, _logger )
    if user_anno:
        _capabilities[ "user-anno" ] = True
    asop, asop_content = init_asop( _startup_msgs, _logger )
    if asop:
        _capabilities[ "asop" ] = True
    init_search(
        content_sets, qa, errata, user_anno, asop, asop_content,
        _startup_msgs, _logger
    )

# ---------------------------------------------------------------------

@app.route( "/app-config" )
def get_app_config():
    """Return the app config."""
    result = {
        "capabilities": _capabilities,
    }
    for key in [ "INITIAL_QUERY_STRING", "DISABLE_AUTO_SHOW_RULE_INFO" ]:
        val = app.config.get( key )
        if val is not None:
            result[ key ] = parse_int( val, val )
    return jsonify( result )

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
