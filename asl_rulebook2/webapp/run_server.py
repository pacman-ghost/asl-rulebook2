#!/usr/bin/env python3
""" Run the webapp server. """

import os
import threading
import urllib.request
import time
import glob

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
    port = None
    if bind_addr:
        words = bind_addr.split( ":" )
        host = words[0]
        if len(words) > 1:
            port = words[1]
    else:
        host = app.config.get( "FLASK_HOST", "localhost" )
    if not port:
        port = app.config.get( "FLASK_PORT_NO" )
    if not flask_debug:
        flask_debug = app.config.get( "FLASK_DEBUG", False )

    # initialize
    if data_dir:
        if not os.path.isdir( data_dir ):
            raise RuntimeError( "Invalid data directory: {}".format( data_dir ) )
        app.config["DATA_DIR"] = data_dir

    # validate the configuration
    if not host:
        raise RuntimeError( "The server host was not set." )
    if not port:
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
            url = "http://{}:{}/ping".format( host, port )
            _ = urllib.request.urlopen( url )
        threading.Thread( target=_start_server, daemon=True ).start()

    # check if the user needs to prepare their data files
    if not app.config.get( "DATA_DIR" ):
        # yup - initialize the socketio server
        init_prepare_socketio( app )

    # run the server
    app.run( host=host, port=port, debug=flask_debug,
        extra_files = extra_files
    )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def init_prepare_socketio( flask_app ):
    """Initialize the socketio server needed to prepare the data files."""
    # NOTE: We only set this up if it's needed (i.e. because there is no data directory,
    # and the user needs to prepare their data files), rather than always having it running
    # on the off-chance that the user might need it :-/
    # NOTE: socketio doesn't really work well with threads, and it's tricky to get it to
    # send events to the client if we're using e.g. eventlet:
    #   https://stackoverflow.com/questions/43801884/how-to-run-python-socketio-in-thread
    #   https://python-socketio.readthedocs.io/en/latest/server.html#standard-threads
    # Using native threads is less-performant, but it's not an issue for us, and it works :-/
    import socketio
    sio = socketio.Server( async_mode="threading" )
    flask_app.wsgi_app = socketio.WSGIApp( sio, flask_app.wsgi_app )
    globvars.socketio_server = sio

# ---------------------------------------------------------------------

if __name__ == "__main__":
    main() #pylint: disable=no-value-for-parameter
