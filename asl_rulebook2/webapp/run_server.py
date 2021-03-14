#!/usr/bin/env python3
""" Run the webapp server. """

import os
import glob

import click

from asl_rulebook2.webapp import app

# ---------------------------------------------------------------------

@click.command()
@click.option( "--addr","-a","bind_addr", help="Webapp server address (host:port)." )
@click.option( "--debug","flask_debug", is_flag=True, default=False, help="Run Flask in debug mode." )
def main( bind_addr, flask_debug ):
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

    # validate the configuration
    if not host:
        raise RuntimeError( "The server host was not set." )
    if not port:
        raise RuntimeError( "The server port was not set." )

    # monitor extra files for changes
    extra_files = []
    fspecs = [ "static/", "templates/", "config/" ]
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

    # run the server
    app.run( host=host, port=port, debug=flask_debug,
        extra_files = extra_files
    )

# ---------------------------------------------------------------------

if __name__ == "__main__":
    main() #pylint: disable=no-value-for-parameter
