""" Allow the test suite to control a remote webapp server. """

import grpc
from google.protobuf.empty_pb2 import Empty

from asl_rulebook2.webapp.tests.proto.generated.control_tests_pb2_grpc import ControlTestsStub

from asl_rulebook2.webapp.tests.proto.generated.control_tests_pb2 import \
    SetDataDirRequest, SetAppConfigValRequest

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

    def set_data_dir( self, fixtures_dname ):
        """Set the data directory."""
        self._stub.setDataDir(
            SetDataDirRequest( fixturesDirName = fixtures_dname )
        )
        return self

    def set_app_config_val( self, key, val ):
        """Set an app config value."""
        if isinstance( val, str ):
            req = SetAppConfigValRequest( key=key, strVal=val )
        elif isinstance( val, int ):
            req = SetAppConfigValRequest( key=key, intVal=val )
        elif isinstance( val, bool ):
            req = SetAppConfigValRequest( key=key, boolVal=val )
        else:
            raise ValueError( "Invalid value type: {}".format( type(val).__name__ ) )
        self._stub.setAppConfigVal( req )
        return self
