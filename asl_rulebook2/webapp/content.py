""" Manage the content documents. """

import os
import io
import json
import glob

from flask import jsonify, send_file, url_for, abort

from asl_rulebook2.webapp import app
from asl_rulebook2.webapp.utils import change_extn, slugify

content_docs = None

# ---------------------------------------------------------------------

def load_content_docs( startup_msgs, logger ):
    """Load the content documents from the data directory."""

    # initialize
    global content_docs
    content_docs = {}
    dname = app.config.get( "DATA_DIR" )
    if not dname:
        return
    if not os.path.isdir( dname ):
        startup_msgs.error( "Invalid data directory.", dname )
        return

    def load_file( fname, content_doc, key, on_error, binary=False ):
        fname = os.path.join( dname, fname )
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
        content_doc[ key ] = data
        return True

    # load each content doc
    logger.info( "Loading content docs: %s", dname )
    fspec = os.path.join( dname, "*.index" )
    for fname in glob.glob( fspec ):
        # load the main index file
        fname2 = os.path.basename( fname )
        logger.info( "- %s", fname2 )
        title = os.path.splitext( fname2 )[0]
        content_doc = {
            "_fname": fname,
            "doc_id": slugify( title ),
            "title": title,
        }
        if not load_file( fname2, content_doc, "index", startup_msgs.error ):
            continue # nb: we can't do anything without an index file
        # load any associated files
        load_file( change_extn(fname2,".targets"), content_doc, "targets", startup_msgs.warning )
        load_file( change_extn(fname2,".footnotes"), content_doc, "footnotes", startup_msgs.warning )
        load_file( change_extn(fname2,".pdf"), content_doc, "content", startup_msgs.warning, binary=True )
        # save the new content doc
        content_docs[ content_doc["doc_id"] ] = content_doc

# ---------------------------------------------------------------------

@app.route( "/content-docs" )
def get_content_docs():
    """Return the available content docs."""
    resp = {}
    for cdoc in content_docs.values():
        cdoc2 = {
            "doc_id": cdoc["doc_id"],
            "title": cdoc["title"],
        }
        if "content" in cdoc:
            cdoc2["url"] = url_for( "get_content", doc_id=cdoc["doc_id"] )
        if "targets" in cdoc:
            cdoc2["targets"] = cdoc["targets"]
        resp[ cdoc["doc_id"] ] = cdoc2
    return jsonify( resp )

# ---------------------------------------------------------------------

@app.route( "/content/<doc_id>" )
def get_content( doc_id ):
    """Return the content for the specified document."""
    cdoc = content_docs.get( doc_id )
    if not cdoc or "content" not in cdoc:
        abort( 404 )
    buf = io.BytesIO( cdoc["content"] )
    return send_file( buf, mimetype="application/pdf" )
