""" Base class for the extraction classes. """

# ---------------------------------------------------------------------

class ExtractBase:
    """Base class for the extraction classes."""

    def __init__( self, args, default_args, log ):
        self._args = args
        if default_args:
            for key in default_args:
                if key not in self._args:
                    self._args[ key ] = default_args[ key ]
        self._log = log

    @staticmethod
    def parse_args( args, default_args ):
        """Helper method to parse command-line arguments."""
        args2 = {}
        for arg in args:
            pos = arg.find( "=" )
            if pos < 0:
                raise RuntimeError( "Invalid configuration parameter: {}".format( arg ) )
            key, val = arg[:pos], arg[pos+1:]
            if key not in default_args:
                raise RuntimeError( "Unknown configuration parameter: {}".format( key ) )
            args2[ key ] = int(val) if val.isdigit() else val
        return args2

    def _in_viewport( self, elem, vp_type ):
        """Check if an element is in the viewport."""
        if elem.x0 <= self._args[vp_type+"_vp_left"] or elem.x1 >= self._args[vp_type+"_vp_right"]:
            return False
        if elem.y0 <= self._args[vp_type+"_vp_bottom"] or elem.y1 >= self._args[vp_type+"_vp_top"]:
            return False
        return True

    @staticmethod
    def _is_bold( elem ):
        """Check if an element is using a bold font."""
        return elem.fontname.endswith( ( "-Bold", ",Bold", "-BoldMT" ) )

    def log_msg( self, msg_type, msg, *args, **kwargs ):
        """Log a message."""
        if not self._log:
            return
        msg = msg.format( *args, **kwargs )
        self._log( msg_type, msg )
