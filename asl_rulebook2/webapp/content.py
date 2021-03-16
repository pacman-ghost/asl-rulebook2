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

def load_content_docs( logger ):
    """Load the content documents from the data directory."""

    # initialize
    global content_docs
    content_docs = {}
    dname = app.config.get( "DATA_DIR" )
    if not dname:
        return
    if not os.path.dirname( dname ):
        raise RuntimeError( "Invalid data directory: {}".format( dname ) )

    def get_doc( content_doc, key, fname, binary=False ):
        fname = os.path.join( dname, fname )
        if not os.path.isfile( fname ):
            return
        if binary:
            with open( fname, mode="rb" ) as fp:
                data = fp.read()
            logger.debug( "- Loaded \"%s\" file: #bytes=%d", key, len(data) )
            content_doc[ key ] = data
        else:
            with open( fname, "r", encoding="utf-8" ) as fp:
                content_doc[ key ] = json.load( fp )
            logger.debug( "- Loaded \"%s\" file.", key )

    # load each content doc
    logger.info( "Loading content docs: %s", dname )
    fspec = os.path.join( dname, "*.index" )
    for fname in glob.glob( fspec ):
        fname2 = os.path.basename( fname )
        logger.info( "- %s", fname2 )
        title = os.path.splitext( fname2 )[0]
        content_doc = {
            "_fname": fname,
            "doc_id": slugify( title ),
            "title": title,
        }
        get_doc( content_doc, "index", fname2 )
        get_doc( content_doc, "targets", change_extn(fname2,".targets") )
        get_doc( content_doc, "footnotes", change_extn(fname2,".footnotes") )
        get_doc( content_doc, "content", change_extn(fname2,".pdf"), binary=True )
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
