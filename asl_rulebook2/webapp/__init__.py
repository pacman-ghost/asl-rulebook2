""" Initialize the webapp. """

import os
import threading
import signal
import configparser
import logging
import logging.config

from flask import Flask
import flask.cli
import yaml

from asl_rulebook2.webapp.config.constants import BASE_DIR, CONFIG_DIR

shutdown_event = threading.Event()

# ---------------------------------------------------------------------

def _load_config( fname, section ):
    """Load config settings from a file."""
    fname = os.path.join( CONFIG_DIR, fname )
    if not os.path.isfile( fname ):
        return
    config_parser = configparser.ConfigParser()
    config_parser.optionxform = str # preserve case for the keys :-/
    config_parser.read( fname )
    app.config.update( dict( config_parser.items( section ) ) )

def _set_config_from_env( key ):
    """Set an app config setting from an environment variable."""
    val = os.environ.get( "DOCKER_" + key )
    if val:
        app.config[ key ] = val

# ---------------------------------------------------------------------

def _on_sigint( signum, stack ): #pylint: disable=unused-argument
    """Clean up after a SIGINT."""

    # notify everyone that we're shutting down
    shutdown_event.set()

    # call any registered cleanup handlers
    for handler in globvars.cleanup_handlers:
        handler()

    # exit the application
    raise SystemExit()

# ---------------------------------------------------------------------

# initialize Flask
app = Flask( __name__ )

# load the application configuration
_load_config( "app.cfg", "System" )
_load_config( "site.cfg", "Site Config" )
_load_config( "debug.cfg", "Debug" )
for _key, _val in app.config.items():
    if str( _val ).isdigit():
        app.config[ _key ] = int( _val )

# load any config from environment variables (e.g. set in the Docker container)
_set_config_from_env( "DATA_DIR" )
_set_config_from_env( "CACHED_SEARCHDB" )

# initialize logging
_fname = os.path.join( CONFIG_DIR, "logging.yaml" )
if os.path.isfile( _fname ):
    with open( _fname, "r", encoding="utf-8" ) as fp:
        try:
            logging.config.dictConfig( yaml.safe_load( fp ) )
        except Exception as ex: #pylint: disable=broad-except
            logging.error( "Can't load the logging config: %s", ex )
else:
    # stop Flask from logging every request :-/
    logging.getLogger( "werkzeug" ).setLevel( logging.WARNING )

# load the application
import asl_rulebook2.webapp.main #pylint: disable=wrong-import-position,cyclic-import
import asl_rulebook2.webapp.startup #pylint: disable=wrong-import-position,cyclic-import
import asl_rulebook2.webapp.content #pylint: disable=wrong-import-position,cyclic-import
import asl_rulebook2.webapp.search #pylint: disable=wrong-import-position,cyclic-import
import asl_rulebook2.webapp.rule_info #pylint: disable=wrong-import-position,cyclic-import
import asl_rulebook2.webapp.prepare #pylint: disable=wrong-import-position,cyclic-import
from asl_rulebook2.webapp import globvars #pylint: disable=wrong-import-position,cyclic-import
app.before_request( globvars.on_request )

# install our signal handler
signal.signal( signal.SIGINT, _on_sigint )
