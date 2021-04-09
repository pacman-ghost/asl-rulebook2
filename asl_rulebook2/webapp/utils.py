"""Helper functions."""

import os
import pathlib
import re
import json
import traceback

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

def load_data_file( fname, ftype, binary, logger, on_error ):
    """Load a data file."""
    try:
        # load the file
        logger.debug("- Loading %s: %s", ftype, fname )
        if binary:
            with open( fname, mode="rb" ) as fp:
                data = fp.read()
        else:
            with open( fname, "r", encoding="utf-8" ) as fp:
                data = json.load( fp )
    except Exception as ex: #pylint: disable=broad-except
        msg = "Couldn't load \"{}\".".format( os.path.basename(fname) )
        on_error( msg, str(ex) )
        logger.error( "%s\n%s", msg, traceback.format_exc() )
        return None
    return data

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

def split_strip( val, sep ):
    """Split a string and strip each field."""
    return [ v.strip() for v in val.split( sep ) ]

def parse_int( val, default=None ):
    """Parse an integer."""
    try:
        return int( val )
    except (ValueError, TypeError):
        return default
