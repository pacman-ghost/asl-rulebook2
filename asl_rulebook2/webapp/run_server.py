#!/usr/bin/env python3
""" Run the webapp server. """

import os
import threading
import urllib.request
import time
import glob

import click

from asl_rulebook2.webapp import app

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

    # run the server
    app.run( host=host, port=port, debug=flask_debug,
        extra_files = extra_files
    )

# ---------------------------------------------------------------------

if __name__ == "__main__":
    main() #pylint: disable=no-value-for-parameter
