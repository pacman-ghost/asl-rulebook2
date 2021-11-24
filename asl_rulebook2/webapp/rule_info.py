""" Manage the Q+A and annotations. """

import os
import glob
import re
import copy
import logging
from collections import defaultdict

from flask import jsonify, send_from_directory, abort

from asl_rulebook2.utils import plural
from asl_rulebook2.webapp import app
from asl_rulebook2.webapp.utils import load_data_file

_qa_index = None
_qa_images_dir = None
_errata = None
_user_anno = None

# ---------------------------------------------------------------------

def init_qa( startup_msgs, logger ):
    """Initialize the Q+A."""

    # initialize
    global _qa_index, _qa_images_dir
    _qa_index, _qa_images_dir = {}, None

    # get the data directory
    data_dir = app.config.get( "DATA_DIR" )
    if not data_dir:
        return None, None
    base_dir = os.path.join( data_dir, "q+a" )
    _qa_images_dir = os.path.abspath( os.path.join( base_dir, "images" ) )

    qa = {}
    def load_qa( fname ):
        """Load the Q+A entries from a data file."""
        logger.info( "Loading Q+A: %s", fname )
        qa_entries = load_data_file( fname, "Q+A", "json", logger, startup_msgs.warning )
        if qa_entries is None:
            return
        for key, entries in qa_entries.items():
            if key in qa:
                qa[ key ].extend( entries )
            else:
                qa[ key ] = entries
        n = sum( len(v) for v in qa_entries.values() )
        logger.info( "- Loaded %s.", plural(n,"entry","entries") )

    # load the Q+A entries
    qa_fnames = []
    fspec = os.path.join( base_dir, "*.json" )
    for fname in sorted( glob.glob( fspec ) ):
        if os.path.basename( fname ) in ("sources.json", "fixups.json"):
            continue
        load_qa( fname )
        qa_fnames.append( fname )

    # build an index of the Q+A entries
    for qa_entries in qa.values():
        for qa_entry in qa_entries:
            for ruleid in qa_entry.get( "ruleids", [] ):
                if ruleid in _qa_index:
                    _qa_index[ ruleid ].append( qa_entry )
                else:
                    _qa_index[ ruleid ] = [ qa_entry ]

    # fixup the Q+A content
    fname = os.path.join( base_dir, "fixups.json" )
    if os.path.isfile( fname ):
        logger.info( "Loading Q+A fixups: %s", fname )
        fixups = load_data_file( fname, "fixups", "json", logger, startup_msgs.warning )
        if fixups:
            for qa_entries in qa.values():
                for qa_entry in qa_entries:
                    for content in qa_entry.get( "content", [] ):
                        if "question" in content:
                            content["question"] = _apply_fixups( content["question"], fixups )
                        for answer in content.get( "answers", [] ):
                            answer[0] = _apply_fixups( answer[0], fixups )

    # load the Q+A sources
    sources = {}
    fname = os.path.join( base_dir, "sources.json" )
    if os.path.isfile( fname ):
        logger.info( "Loading Q+A sources: %s", fname )
        sources = load_data_file( fname, "sources", "json", logger, startup_msgs.warning )
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

    return qa, qa_fnames

# ---------------------------------------------------------------------

def init_annotations( startup_msgs, logger ):
    """Initialize the user-defined annotations."""

    # initialize
    global _user_anno
    _user_anno = {}

    # get the data directory
    data_dir = app.config.get( "DATA_DIR" )
    if not data_dir:
        return None, None

    # load the user-defined annotations
    fname = os.path.join( data_dir, "annotations.json" )
    if os.path.isfile( fname ):
        _load_anno( fname, "annotations", _user_anno, logger, startup_msgs )
    else:
        fname = None

    return _user_anno, fname

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def init_errata( startup_msgs, logger ):
    """Initialize the errata."""

    # NOTE: Internally, errata are identical to user-defined annotations - they're just a bit of
    # free-form content, associated with a ruleid. The only difference is how they're loaded
    # into the program, and how they're presented to the user.

    # initialize
    global _errata
    _errata = {}

    # get the data directory
    data_dir = app.config.get( "DATA_DIR" )
    if not data_dir:
        return None, None
    base_dir = os.path.join( data_dir, "errata" )

    # load the errata
    errata_fnames = []
    fspec = os.path.join( base_dir, "*.json" )
    for fname in sorted( glob.glob( fspec ) ):
        if os.path.basename( fname ) in ("sources.json", "fixups.json"):
            continue
        _load_anno( fname, "errata", _errata, logger, startup_msgs )
        errata_fnames.append( fname )

    # apply any fixups
    fname = os.path.join( base_dir, "fixups.json" )
    if os.path.isfile( fname ):
        logger.info( "Loading errata fixups: %s", fname )
        fixups = load_data_file( fname, "fixups", "json", logger, startup_msgs.warning )
        if fixups:
            for ruleid in _errata:
                for anno in _errata[ruleid]:
                    anno["content"] = _apply_fixups( anno["content"], fixups )

    # load the errata sources
    sources = {}
    fname = os.path.join( base_dir, "sources.json" )
    if os.path.isfile( fname ):
        logger.info( "Loading errata sources: %s", fname )
        sources = load_data_file( fname, "sources", "json", logger, startup_msgs.warning )
        if sources:
            logger.info( "- Loaded %s.", plural(len(sources),"source","sources") )

    # fixup all the errata entries with their real source
    for ruleid in _errata:
        for anno in _errata[ruleid]:
            if "source" in anno:
                anno["source"] = sources.get( anno["source"], anno["source"] )

    return _errata, errata_fnames

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _load_anno( fname, atype, save_loc, logger, startup_msgs ):
    """Load annotations from a data file."""
    logger.info( "Loading %s: %s", atype, fname )
    anno_entries = load_data_file( fname, atype, "json", logger, startup_msgs.warning )
    if not anno_entries:
        return
    for anno in anno_entries:
        if anno["ruleid"] in save_loc:
            save_loc[ anno["ruleid"] ].append( anno )
        else:
            save_loc[ anno["ruleid"] ] = [ anno ]

# ---------------------------------------------------------------------

def _apply_fixups( val, fixups ):
    """Apply used-defined fixups to a value."""
    for search_for, replace_with in fixups.get( "replace", {} ).items():
        val = val.replace( search_for, replace_with )
    val = re.sub( r"\[EXC: .*?\]", r"<span class='exc'>\g<0></span>", val )
    return val

# ---------------------------------------------------------------------

@app.route( "/rule-info/<ruleid>" )
def get_rule_info( ruleid ):
    """Get the Q+A and annotations for the specified ruleid."""
    results = []
    def get_entries( index, ri_type ):
        for entry in index.get( ruleid.upper(), [] ):
            entry = copy.deepcopy( entry )
            entry[ "ri_type" ] = ri_type
            results.append( entry )
    get_entries( _user_anno, "user-anno" )
    get_entries( _errata, "errata" )
    get_entries( _qa_index, "qa" )
    return jsonify( results )

# ---------------------------------------------------------------------

@app.route( "/qa/image/<fname>" )
def get_qa_image( fname ):
    """Get an image that is part of a Q+A entry."""
    if not _qa_images_dir:
        abort( 404 )
    return send_from_directory( _qa_images_dir, fname )
