#!/usr/bin/env python3
""" Run the webapp server. """

import os
import threading
import urllib.request
import time
import glob

import flask_socketio
import click

from asl_rulebook2.webapp import app, globvars

# ---------------------------------------------------------------------

@click.command()
@click.option( "--addr","-a","bind_addr", help="Webapp server address (host:port)." )
@click.option( "--data","-d","data_dir", help="Data directory." )
@click.option( "--force-init-delay", default=0, help="Force the webapp to initialize (#seconds delay)." )
@click.option( "--debug","flask_debug", is_flag=True, default=False, help="Run Flask in debug mode." )
def main( bind_addr, data_dir, force_init_delay, flask_debug ):
    """Run the webapp server."""

    # initialize
    flask_port = None
    if bind_addr:
        words = bind_addr.split( ":" )
        flask_host = words[0]
        if len(words) > 1:
            flask_port = words[1]
    else:
        flask_host = app.config.get( "FLASK_HOST", "localhost" )
    if not flask_port:
        flask_port = app.config.get( "FLASK_PORT_NO" )
    if not flask_debug:
        flask_debug = app.config.get( "FLASK_DEBUG", False )

    # initialize
    if data_dir:
        if not os.path.isdir( data_dir ):
            raise RuntimeError( "Invalid data directory: {}".format( data_dir ) )
        app.config["DATA_DIR"] = data_dir

    # validate the configuration
    if not flask_host:
        raise RuntimeError( "The server host was not set." )
    if not flask_port:
        raise RuntimeError( "The server port was not set." )

    # monitor extra files for changes
    extra_files = []
    fspecs = [ "static/", "templates/", "config/" ]
    if app.config.get( "DATA_DIR" ):
        data_dir = app.config["DATA_DIR"]
        fspecs.append( data_dir )
        fspecs.append( os.path.join( data_dir, "annotations.json" ) )
        paths = [
            os.path.join( data_dir, p )
            for p in os.listdir( data_dir )
        ]
        fspecs.extend( p for p in paths if os.path.isdir(p) )
    for fspec in fspecs:
        fspec = os.path.abspath( os.path.join( os.path.dirname(__file__), fspec ) )
        if os.path.isdir( fspec ):
            files = [ os.path.join(fspec,f) for f in os.listdir(fspec) ]
            files = [
                f for f in files
                if os.path.isfile(f) and os.path.splitext(f)[1] not in [".swp"]
            ]
        else:
            files = glob.glob( fspec )
        extra_files.extend( files )

    # check if we should force webapp initialization
    if force_init_delay > 0:
        def _start_server():
            time.sleep( force_init_delay )
            url = "http://{}:{}".format( flask_host, flask_port )
            _ = urllib.request.urlopen( url )
        threading.Thread( target=_start_server, daemon=True ).start()

    # run the server
    run_server( flask_host, flask_port, flask_debug, extra_files )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def run_server( host, port, debug, extra_files=None ):
    """Run the webapp server."""

    # NOTE: flask-socketio + eventlet handles concurrency differently to the Flask development server,
    # and we need to remain responsive, otherwise pings from the socketio client will timeout, and it will
    # disconnect (and show a big warning in the UI that the server has gone away). To avoid this,
    # we relinquish the CPU regularly, but just in case, we increase the ping timeout (and allow the user
    # to increase it even further, if necessary). This should only be an issue when preparing the data files,
    # since the main program doesn't use socketio.
    # NOTE: Setting the timeout high shouldn't be a problem, since if the server really does go away,
    # the connection will be dropped, and the front-end Javascript will detect that immediately.
    ping_timeout = app.config.get( "SOCKETIO_PING_TIMEOUT", 30 )

    # run the server
    sio = flask_socketio.SocketIO( app,
        async_mode = "eventlet",
        ping_timeout = ping_timeout
    )
    globvars.socketio_server = sio
    args = {
        "debug": debug,
        "log_output": False
    }
    if extra_files:
        args.update( {
            "use_reloader": True,
            "reloader_options": { "extra_files": extra_files },
        } )
    sio.run( app,
        host=host, port=port,
        **args
    )

# ---------------------------------------------------------------------

if __name__ == "__main__":
    main() #pylint: disable=no-value-for-parameter
