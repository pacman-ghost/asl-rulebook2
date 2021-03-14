"""Helper functions."""

# ---------------------------------------------------------------------

def parse_int( val, default=None ):
    """Parse an integer."""
    try:
        return int( val )
    except (ValueError, TypeError):
        return default
