""" Manage the startup process. """

import time
import datetime
import threading
import logging
import traceback
import enum
from collections import defaultdict

from flask import jsonify

from asl_rulebook2.webapp import app
from asl_rulebook2.webapp.content import load_content_sets
from asl_rulebook2.webapp.search import init_search
from asl_rulebook2.webapp.rule_info import init_qa, init_errata, init_annotations
from asl_rulebook2.webapp.asop import init_asop
from asl_rulebook2.webapp.utils import parse_int

_capabilities = None

_startup_tasks = None

_logger = logging.getLogger( "startup" )
_startup_msgs = None

# ---------------------------------------------------------------------

class StartupStatusEnum( enum.IntEnum ): #pylint: disable=missing-class-docstring
    NOT_STARTED = 0
    STARTED = 1
    TASKS_RUNNING = 2
    COMPLETED = -1

_startup_status = StartupStatusEnum.NOT_STARTED

# ---------------------------------------------------------------------

def init_webapp():
    """Initialize the webapp.

    IMPORTANT: This is called on the first Flask request, but can also be called multiple times
    after that by the test suite, to reset the webapp before each test.
    """

    # initialize
    global _startup_status, _startup_msgs, _capabilities, _startup_tasks
    _startup_status = StartupStatusEnum.STARTED
    _startup_msgs = StartupMsgs()
    _capabilities = {}
    _startup_tasks = []

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
    asop, asop_preambles, asop_content = init_asop( _startup_msgs, _logger )
    if asop:
        _capabilities[ "asop" ] = True
    init_search(
        content_sets, qa, errata, user_anno, asop, asop_preambles, asop_content,
        _startup_msgs, _logger
    )

    # everything has been initialized - now we can go back and fixup content
    # NOTE: This is quite a slow process (~1 minute for a full data load), which is why we don't do it inline,
    # during the normal startup process. So, we start up using the original content, and if the user does
    # a search, that's what they will see, but we fix it up in the background, and the new content will
    # eventually start to be returned as search results. We could do this process once, and save the results
    # in a file, then reload everything at startup, which will obviously be much faster, but we then have to
    # figure out when that file needs to be rebuolt :-/
    if app.config.get( "BLOCKING_STARTUP_TASKS" ):
        # NOTE: It's useful to do this synchronously when running the test suite, since if the tests
        # need the linkified ruleid's, they can't start until the fixup has finished (and if they don't
        # it won't really matter, since there will be so little data, this process will be fast).
        _do_startup_tasks( False )
    else:
        threading.Thread( target=_do_startup_tasks, args=(True,) ).start()

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _add_startup_task( ctype, func ):
    """Register a function to run at startup."""
    if app.config.get( "DISABLE_STARTUP_TASKS" ):
        return
    _startup_tasks.append( ( ctype, func ) )

def _do_startup_tasks( delay ):
    """Run each registered startup task."""

    # initialize
    global _startup_status
    if not _startup_tasks:
        _startup_status = StartupStatusEnum.COMPLETED
        return

    # FUDGE! If we start processing straight away, the main PDF loads very slowly because of us :-/,
    # and since there's no way to set thread priorities in Python, we delay for a short time, to give
    # the PDF time to load, before we start working.
    # NOTE: This delay only helps the initial load of the main ASLRB PDF. After processing has started,
    # if the user reloads the page, or tries to load another PDF, they will have the same problem of
    # very slow loads. To work around this, _tag_ruleids_in_field() sleeps periodically, to give
    # other threads a chance to run. The PDF's load a bit slowly, but it's acceptable.
    if delay:
        delay = parse_int( app.config.get( "STARTUP_TASKS_DELAY" ), 5 )
        time.sleep( delay )

    # process each startup task
    _startup_status = StartupStatusEnum.TASKS_RUNNING
    _logger.info( "Processing startup tasks..." )
    start_time = time.time()
    for task_no, (ctype, func) in enumerate( _startup_tasks ):
        _logger.debug( "Running startup task '%s' (%d/%d)...", ctype, 1+task_no, len(_startup_tasks) )
        start_time2 = time.time()
        try:
            msg = func()
        except Exception as ex: #pylint: disable=broad-except
            _logger.error( "Startup task '%s' failed: %s\n%s", ctype, ex, traceback.format_exc() )
            continue
        elapsed_time = datetime.timedelta( seconds = int( time.time() - start_time2 ) )
        _logger.debug( "- Finished startup task '%s' (%s): %s", ctype, elapsed_time, msg )

    # finish up
    elapsed_time = datetime.timedelta( seconds = int( time.time() - start_time ) )
    _logger.info( "All startup tasks completed (%s).", elapsed_time )
    _startup_status = StartupStatusEnum.COMPLETED

# ---------------------------------------------------------------------

@app.route( "/app-config" )
def get_app_config():
    """Return the app config."""

    # initialize
    _logger.debug( "Sending app config:" )
    result = {}

    # send the available capabilities
    _logger.debug( "- capabilities: %s", _capabilities )
    result["capabilities"] = _capabilities

    # send any user-defined debug settings
    for key in app.config:
        if not key.startswith( "WEBAPP_" ):
            continue
        val = app.config.get( key )
        if val is not None:
            _logger.debug( "- %s = %s", key, val )
            result[ key ] = parse_int( val, val )

    return jsonify( result )

# ---------------------------------------------------------------------

@app.route( "/startup-msgs" )
def get_startup_msgs():
    """Return any messages issued during startup."""
    return jsonify( _startup_msgs.msgs )

@app.route( "/startup-status" )
def get_startup_status():
    """Return the current startup status."""
    return jsonify( {
        "status": _startup_status
    } )

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
