""" Manage the Q+A. """

import os
import glob
import re
import logging
from collections import defaultdict

from flask import jsonify, send_from_directory, abort

from asl_rulebook2.utils import plural
from asl_rulebook2.webapp import app
from asl_rulebook2.webapp.utils import load_data_file

_qa_index = None
_qa_images_dir = None

# ---------------------------------------------------------------------

def init_qa( startup_msgs, logger ):
    """Initialize the Q+A."""

    # initialize
    global _qa_index, _qa_images_dir
    _qa_index, _qa_images_dir = {}, None

    # get the data directory
    data_dir = app.config.get( "DATA_DIR" )
    if not data_dir:
        return None
    base_dir = os.path.join( data_dir, "q+a" )
    _qa_images_dir = os.path.join( base_dir, "images" )

    qa = {}
    def load_qa( fname ):
        """Load the Q+A entries from a data file."""
        logger.info( "Loading Q+A: %s", fname )
        qa_entries = load_data_file( fname, "Q+A", False, logger, startup_msgs.warning )
        if qa_entries is None:
            return
        for key, vals in qa_entries.items():
            if key in qa:
                qa[ key ].extend( vals )
            else:
                qa[ key ] = vals
        n = sum( len(v) for v in qa_entries.values() )
        logger.info( "- Loaded %s.", plural(n,"entry","entries") )

    # load the Q+A entries
    fspec = os.path.join( base_dir, "*.json" )
    for fname in sorted( glob.glob( fspec ) ):
        if os.path.basename( fname ) in ("sources.json", "fixups.json"):
            continue
        load_qa( fname )

    # build an index of the Q+A entries
    for qa_entries in qa.values():
        for qa_entry in qa_entries:
            for ruleid in qa_entry.get( "ruleids", [] ):
                if ruleid in _qa_index:
                    _qa_index[ ruleid ].append( qa_entry )
                else:
                    _qa_index[ ruleid ] = [ qa_entry ]

    fixups = None
    def apply_fixups( val ):
        """Fix-up Q+A content."""
        for search_for, replace_with in fixups.get( "replace", {} ).items():
            val = val.replace( search_for, replace_with )
        val = re.sub( r"\[EXC: .*?\]", r"<span class='exc'>\g<0></span>", val )
        return val

    # fixup the Q+A content
    fname = os.path.join( base_dir, "fixups.json" )
    if os.path.isfile( fname ):
        logger.info( "Loading Q+A fixups: %s", fname )
        fixups = load_data_file( fname, "fixups", False, logger, startup_msgs.warning )
        for qa_entries in qa.values():
            for qa_entry in qa_entries:
                for content in qa_entry.get( "content", [] ):
                    if "question" in content:
                        content["question"] = apply_fixups( content["question"] )
                    for answer in content.get( "answers", [] ):
                        answer[0] = apply_fixups( answer[0] )

    # load the Q+A sources
    sources = {}
    fname = os.path.join( base_dir, "sources.json" )
    if os.path.isfile( fname ):
        logger.info( "Loading Q+A sources: %s", fname )
        sources = load_data_file( fname, "sources", False, logger, startup_msgs.warning )
        if sources:
            logger.info( "- Loaded %s.", plural(len(sources),"source","sources") )

    # fix up all the Q+A entries with their real source
    if sources:
        usage, unknown = defaultdict(int), set()
        for qa_entries in qa.values():
            for qa_entry in qa_entries:
                for content in qa_entry.get( "content", [] ):
                    for answer in content.get( "answers", [] ):
                        source = answer[1]
                        usage[ source ] += 1
                        source_name = sources.get( source )
                        if source_name:
                            answer[1] = source_name
                        else:
                            unknown.add( source )
        if unknown:
            logger.warning( "Unknown Q+A sources: %s", " ; ".join(unknown) )
        if logger.isEnabledFor( logging.DEBUG ):
            usage = sorted( usage.items(), key=lambda v: v[1], reverse=True )
            for u in usage:
                logger.debug( "-   %s (%s) = %d", sources.get(u[0],"???"), u[0], u[1] )

    return qa

# ---------------------------------------------------------------------

@app.route( "/qa/<ruleid>" )
def get_qa( ruleid ):
    """Get the Q+A for the specified ruleid."""
    ruleid = ruleid.upper()
    qa_entries = _qa_index.get( ruleid, [] )
    return jsonify( qa_entries )

# ---------------------------------------------------------------------

@app.route( "/qa/image/<fname>" )
def get_qa_image( fname ):
    """Get an image that is part of a Q+A entry."""
    if not _qa_images_dir:
        abort( 404 )
    return send_from_directory( _qa_images_dir, fname )
