""" gRPC servicer that allows the webapp server to be controlled. """

import inspect
import logging

from google.protobuf.empty_pb2 import Empty

from asl_rulebook2.webapp.tests.proto.generated.control_tests_pb2_grpc \
    import ControlTestsServicer as BaseControlTestsServicer

_logger = logging.getLogger( "control_tests" )

# ---------------------------------------------------------------------

# NOTE: The API for this class should be kept in sync with ControlTests.

class ControlTestsServicer( BaseControlTestsServicer ):
    """Allows a webapp server to be controlled by a remote client."""

    def __init__( self, webapp ):
        # initialize
        self._webapp = webapp

    def __del__( self ):
        # clean up
        self.cleanup()

    def cleanup( self ):
        """Clean up."""
        # nb: nothing required here, for now

    def startTests( self, request, context ):
        """Start a new test run."""
        self._log_request( request, context )
        return Empty()

    def endTests( self, request, context ):
        """End a test run."""
        self._log_request( request, context )
        self.cleanup()
        return Empty()

    @staticmethod
    def _log_request( req, ctx ): #pylint: disable=unused-argument
        """Log a request."""
        # get the entry-point name
        msg = "{}()".format( inspect.currentframe().f_back.f_code.co_name )
        # log the message
        _logger.info( "TEST CONTROL: %s", msg )
