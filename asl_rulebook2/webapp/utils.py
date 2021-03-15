"""Helper functions."""

import pathlib
import re

# ---------------------------------------------------------------------

def change_extn( fname, extn ):
    """Change a filename's extension."""
    return pathlib.Path( fname ).with_suffix( extn )

def slugify( val ):
    """Convert a string to a slug."""
    val = re.sub( r"\s+", " ", val ).lower()
    def fix( ch ):
        if ch.isalnum() or ch == "-":
            return ch
        if ch in " _":
            return "-"
        return "_"
    return "".join( fix(ch) for ch in val )

def parse_int( val, default=None ):
    """Parse an integer."""
    try:
        return int( val )
    except (ValueError, TypeError):
        return default
