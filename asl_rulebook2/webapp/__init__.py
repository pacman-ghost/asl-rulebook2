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

from asl_rulebook2.webapp.config.constants import BASE_DIR

shutdown_event = threading.Event()

# ---------------------------------------------------------------------

def _load_config( fname, section ):
    """Load config settings from a file."""
    if not os.path.isfile( fname ):
        return
    config_parser = configparser.ConfigParser()
    config_parser.optionxform = str # preserve case for the keys :-/
    config_parser.read( fname )
    app.config.update( dict( config_parser.items( section ) ) )

# ---------------------------------------------------------------------

def _on_sigint( signum, stack ): #pylint: disable=unused-argument
    """Clean up after a SIGINT."""

    # notify everyone that we're shutting down
    shutdown_event.set()

    # call any registered cleanup handlers
    from asl_rulebook2.webapp import globvars #pylint: disable=cyclic-import
    for handler in globvars.cleanup_handlers:
        handler()

    # exit the application
    raise SystemExit()

# ---------------------------------------------------------------------

# disable the Flask startup banner
flask.cli.show_server_banner = lambda *args: None

# initialize Flask
app = Flask( __name__ )

# load the application configuration
config_dir = os.path.join( BASE_DIR, "config" )
_fname = os.path.join( config_dir, "app.cfg" )
_load_config( _fname, "System" )

# load any site configuration
_fname = os.path.join( config_dir, "site.cfg" )
_load_config( _fname, "Site Config" )

# load any debug configuration
_fname = os.path.join( config_dir, "debug.cfg" )
if os.path.isfile( _fname ) :
    _load_config( _fname, "Debug" )

# initialize logging
_fname = os.path.join( config_dir, "logging.yaml" )
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

# install our signal handler
signal.signal( signal.SIGINT, _on_sigint )
