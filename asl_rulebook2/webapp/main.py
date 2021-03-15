""" Main webapp handlers. """

import os
import threading
import concurrent
import logging

from flask import render_template, jsonify, abort

from asl_rulebook2.webapp import app, globvars, shutdown_event
from asl_rulebook2.webapp.content import load_content_docs
from asl_rulebook2.webapp.utils import parse_int

# ---------------------------------------------------------------------

def init_webapp():
    """Initialize the webapp.

    IMPORTANT: This is called on the first Flask request, but can also be called multiple times
    after that by the test suite, to reset the webapp before each test.
    """
    # initialize the webapp
    load_content_docs()

# ---------------------------------------------------------------------

@app.route( "/" )
def main():
    """Return the main page."""
    return render_template( "index.html" )

# ---------------------------------------------------------------------

_control_tests_port_no = None

@app.route( "/control-tests" )
def get_control_tests():
    """Return information about the remote test control service."""

    def get_port():
        """Get the configured gRPC service port."""
        # NOTE: The Docker container configures this setting via an environment variable.
        return app.config.get( "CONTROL_TESTS_PORT", os.environ.get("CONTROL_TESTS_PORT") )

    # check if the test control service should be made available
    port_no = get_port()
    if not port_no:
        abort( 404 )

    # check if we've already started the service
    if not _control_tests_port_no:

        # nope - make it so
        print( "*** WARNING: Remote test control enabled! ***" )
        started_event = threading.Event()

        def run_service():
            # start the gRPC service
            import grpc
            server = grpc.server( concurrent.futures.ThreadPoolExecutor( max_workers=1 ) )
            from asl_rulebook2.webapp.tests.proto.generated.control_tests_pb2_grpc \
                import add_ControlTestsServicer_to_server
            from asl_rulebook2.webapp.tests.control_tests_servicer \
                import ControlTestsServicer #pylint: disable=cyclic-import
            servicer = ControlTestsServicer( app )
            add_ControlTestsServicer_to_server( servicer, server )
            port_no = parse_int( get_port(), -1 ) # nb: have to get this again?!
            if port_no <= 0:
                # NOTE: Requesting port 0 tells grpc to use any free port, which is usually OK, unless
                # we're running inside a Docker container, in which case it needs to be pre-defined,
                # so that the port can be mapped to an external port when the container is started.
                port_no = 0
            port_no = server.add_insecure_port( "[::]:{}".format( port_no ) )
            logging.getLogger( "control_tests" ).debug(
                "Started the gRPC test control service: port=%s", str(port_no)
            )
            server.start()
            global _control_tests_port_no
            _control_tests_port_no = port_no
            # notify the caller that the service has started
            started_event.set()
            # wait for the application to end
            shutdown_event.wait()
            # stop the service
            server.stop( None )
            server.wait_for_termination()

        # start the service in a background thread
        thread = threading.Thread( target=run_service, daemon=True )
        thread.start()
        # NOTE: We wait for the service to start (since the caller will probably try to connect
        # to it as soon as we return a response).
        started_event.wait( timeout=10 )

        # make sure the gRPC server gets cleaned up when we shutdown
        def cleanup(): #pylint: disable=missing-docstring
            thread.join()
        globvars.cleanup_handlers.append( cleanup )

    # return the service info to the caller
    return jsonify( { "port": _control_tests_port_no } )

# ---------------------------------------------------------------------

@app.route( "/ping" )
def ping():
    """Let the caller know we're alive."""
    return "pong"
