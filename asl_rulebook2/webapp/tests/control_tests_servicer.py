""" gRPC servicer that allows the webapp server to be controlled. """

import os
import inspect
import logging

from google.protobuf.empty_pb2 import Empty

from asl_rulebook2.webapp.tests.proto.generated.control_tests_pb2_grpc \
    import ControlTestsServicer as BaseControlTestsServicer
from asl_rulebook2.webapp.tests.proto.generated.control_tests_pb2 import \
    SetDataDirRequest

_logger = logging.getLogger( "control_tests" )

# ---------------------------------------------------------------------

# NOTE: The API for this class should be kept in sync with ControlTests.

class ControlTestsServicer( BaseControlTestsServicer ):
    """Allows a webapp server to be controlled by a remote client."""

    def __init__( self, webapp ):
        # initialize
        self._webapp = webapp
        self._fixtures_dir = os.path.join( os.path.dirname(__file__), "fixtures/" )

    def __del__( self ):
        # clean up
        self.cleanup()

    def cleanup( self ):
        """Clean up."""
        # nb: nothing required here, for now

    def startTests( self, request, context ):
        """Start a new test run."""
        self._log_request( request, context )
        # reset the webapp
        ctx = None
        self.setDataDir( SetDataDirRequest( fixturesDirName=None ), ctx )
        # NOTE: The webapp has now been reset, but the client must reloaed the home page
        # with "?reload=1", to force it to reload with the new settings.
        return Empty()

    def endTests( self, request, context ):
        """End a test run."""
        self._log_request( request, context )
        self.cleanup()
        return Empty()

    def setDataDir( self, request, context ):
        """Set the data directory."""
        self._log_request( request, context )
        dname = request.fixturesDirName
        # set the data directory
        _logger.debug( "- Setting data directory: %s", dname )
        if dname:
            self._webapp.config[ "DATA_DIR" ] = os.path.join( self._fixtures_dir, dname )
            _logger.warning( os.path.join( self._fixtures_dir, dname ) )
        else:
            self._webapp.config.pop( "DATA_DIR", None )
        return Empty()

    @staticmethod
    def _log_request( req, ctx ): #pylint: disable=unused-argument
        """Log a request."""
        if ctx is None:
            return # nb: we don't log internal calls
        # get the entry-point name
        msg = "{}()".format( inspect.currentframe().f_back.f_code.co_name )
        # log the message
        _logger.info( "TEST CONTROL: %s", msg )
