"""Helper functions."""

import os
import pathlib
import re

from asl_rulebook2.webapp import app, CONFIG_DIR

# ---------------------------------------------------------------------

def make_data_path( path ):
    """Generate a path relative to the data directory."""
    dname = app.config.get( "DATA_DIR" )
    if not dname:
        return None
    return os.path.join( dname, path )

def make_config_path( path ):
    """Generate a path in the config directory."""
    return os.path.join( CONFIG_DIR, path )

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
