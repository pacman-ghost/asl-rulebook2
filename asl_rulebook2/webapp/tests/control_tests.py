""" Allow the test suite to control a remote webapp server. """

import grpc
from google.protobuf.empty_pb2 import Empty

from asl_rulebook2.webapp.tests.proto.generated.control_tests_pb2_grpc import ControlTestsStub

# ---------------------------------------------------------------------

# NOTE: The API for this class should be kept in sync with ControlTestsServicer.

class ControlTests:
    """Control a remote webapp server."""

    def __init__( self, addr ):
        # initialize
        channel = grpc.insecure_channel( addr )
        self._stub = ControlTestsStub( channel )

    def start_tests( self ):
        """Start a new test run."""
        self._stub.startTests( Empty() )
        return self

    def end_tests( self ):
        """End a test run."""
        self._stub.endTests( Empty() )
