""" Manage the content documents. """

import os
import io
import json
import glob

from flask import jsonify, send_file, url_for, abort

from asl_rulebook2.webapp import app
from asl_rulebook2.webapp.utils import slugify

content_sets = None
_chapter_resources = None

# ---------------------------------------------------------------------

def load_content_sets( startup_msgs, logger ):
    """Load the content from the data directory."""

    # NOTE: A "content set" is an index file, together with one or more "content docs".
    # A "content doc" is a PDF file, with an associated targets and/or footnote file.
    # This architecture allows us to have:
    # - a single index file that references content spread over multiple PDF's (e.g. the MMP eASLRB,
    #   together with additional modules in separate PDF's (e.g. RB or KGP), until such time these
    #   get included in the main eASLRB).
    # - rules for completely separate modules (e.g. third-party modules) that are not included
    #   in the MMP eASLRB index, and have their own index.

    # initialize
    global content_sets, _chapter_resources
    content_sets = {}
    _chapter_resources = { "background": {}, "icon": {} }

    # get the data directory
    data_dir = app.config.get( "DATA_DIR" )
    if not data_dir:
        return
    if not os.path.isdir( data_dir ):
        startup_msgs.error( "Invalid data directory.", data_dir )
        return

    def find_resource( fname, dnames ):
        # find a chapter resource file
        for dname in dnames:
            fname2 = os.path.join( dname, fname )
            if os.path.isfile( fname2 ):
                return fname2
        return None

    def load_content_doc( fname_stem, title ):
        # load the content doc files
        content_doc = { "title": title }
        load_file( fname_stem+".targets", content_doc, "targets", startup_msgs.warning )
        load_file( fname_stem+".chapters", content_doc, "chapters", startup_msgs.warning )
        load_file( fname_stem+".footnotes", content_doc, "footnotes", startup_msgs.warning )
        load_file( fname_stem+".pdf", content_doc, "content", startup_msgs.warning, binary=True )
        # locate any chapter backgrounds and icons
        resource_dirs = [
            data_dir, os.path.join( os.path.dirname(__file__), "data/chapters/" )
        ]
        for chapter in content_doc.get( "chapters", [] ):
            chapter_id = chapter.get( "chapter_id" )
            if not chapter_id:
                continue
            for rtype in [ "background", "icon" ]:
                fname = find_resource( "{}-{}.png".format( chapter_id, rtype ), resource_dirs )
                if fname:
                    _chapter_resources[ rtype ][ chapter_id ] = os.path.join( "static/", fname )
                    chapter[ rtype ] = url_for( "get_chapter_resource", chapter_id=chapter_id, rtype=rtype )
        return content_doc

    def load_file( fname, save_loc, key, on_error, binary=False ):
        fname = os.path.join( data_dir, fname )
        if not os.path.isfile( fname ):
            return False
        # load the specified file
        try:
            if binary:
                with open( fname, mode="rb" ) as fp:
                    data = fp.read()
                logger.debug( "- Loaded \"%s\" file: #bytes=%d", key, len(data) )
            else:
                with open( fname, "r", encoding="utf-8" ) as fp:
                    data = json.load( fp )
                logger.debug( "- Loaded \"%s\" file.", key )
        except Exception as ex: #pylint: disable=broad-except
            on_error( "Couldn't load \"{}\".".format( os.path.basename(fname) ), str(ex) )
            return False
        # save the file data
        save_loc[ key ] = data
        return True

    def find_assoc_cdocs( fname_stem ):
        # find other content docs associated with the content set (names have the form "Foo (...)")
        matches = set()
        for fname in os.listdir( data_dir ):
            if not fname.startswith( fname_stem ):
                continue
            fname = os.path.splitext( fname )[0]
            fname = fname[len(fname_stem):].strip()
            if fname.startswith( "(" ) and fname.endswith( ")" ):
                matches.add( fname[1:-1] )
        return matches

    # load each content set
    logger.info( "Loading content sets: %s", data_dir )
    fspec = os.path.join( data_dir, "*.index" )
    for fname in glob.glob( fspec ):
        fname2 = os.path.basename( fname )
        logger.info( "- %s", fname2 )
        # load the index file
        title = os.path.splitext( fname2 )[0]
        cset_id = slugify( title )
        content_set = {
            "cset_id": cset_id,
            "title": title,
            "content_docs": {},
            "index_fname": fname,
        }
        if not load_file( fname2, content_set, "index", startup_msgs.error ):
            continue # nb: we can't do anything without an index file
        # load the main content doc
        fname_stem = os.path.splitext( fname2 )[0]
        content_doc = load_content_doc( fname_stem, fname_stem )
        cdoc_id = cset_id # nb: because this the main content document
        content_doc[ "cdoc_id" ] = cdoc_id
        content_set[ "content_docs" ][ cdoc_id ] = content_doc
        # load any associated content docs
        for fname_stem2 in find_assoc_cdocs( fname_stem ):
            # nb: we assume there's only one space between the two filename stems :-/
            content_doc = load_content_doc(
                "{} ({})".format( fname_stem, fname_stem2 ),
                fname_stem2
            )
            cdoc_id2 = "{}!{}".format( cdoc_id, slugify(fname_stem2) )
            content_doc[ "cdoc_id" ] = cdoc_id2
            content_set[ "content_docs" ][ cdoc_id2 ] = content_doc
        # save the new content set
        content_sets[ content_set["cset_id"] ] = content_set

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _dump_content_sets():
    """Dump the available content sets."""
    for cset_id, cset in content_sets.items():
        print( "=== {} ({}) ===".format( cset["title"], cset_id ) )
        for cdoc_id, cdoc in cset["content_docs"].items():
            print( "Content doc: {} ({})".format( cdoc["title"], cdoc_id ) )
            for key in [ "targets", "footnotes", "content" ]:
                if key in cdoc:
                    print( "- {}: {}".format( key, len(cdoc[key]) ))

# ---------------------------------------------------------------------

@app.route( "/content-docs" )
def get_content_docs():
    """Return the available content docs."""
    resp = {}
    for cset in content_sets.values():
        for cdoc in cset["content_docs"].values():
            cdoc2 = {
                "cdoc_id": cdoc["cdoc_id"],
                "parent_cset_id": cset["cset_id"],
                "title": cdoc["title"],
            }
            if "content" in cdoc:
                cdoc2["url"] = url_for( "get_content", cdoc_id=cdoc["cdoc_id"] )
            for key in [ "targets", "chapters", "background", "icon" ]:
                if key in cdoc:
                    cdoc2[key] = cdoc[key]
            resp[ cdoc["cdoc_id"] ] = cdoc2
    return jsonify( resp )

# ---------------------------------------------------------------------

@app.route( "/content/<cdoc_id>" )
def get_content( cdoc_id ):
    """Return the content for the specified document."""
    for cset in content_sets.values():
        for cdoc in cset["content_docs"].values():
            if cdoc["cdoc_id"] == cdoc_id and "content" in cdoc:
                buf = io.BytesIO( cdoc["content"] )
                return send_file( buf, mimetype="application/pdf" )
    abort( 404 )
    return None # stupid pylint :-/

# ---------------------------------------------------------------------

@app.route( "/chapter/<chapter_id>/<rtype>" )
def get_chapter_resource( chapter_id, rtype ):
    """Return a chapter resource."""
    fname = _chapter_resources.get( rtype, {} ).get( chapter_id )
    if not fname:
        abort( 404 )
    return send_file( fname )
