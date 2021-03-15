""" Manage the content documents. """

import os
import io
import glob

from flask import jsonify, send_file, url_for, abort

from asl_rulebook2.webapp import app
from asl_rulebook2.webapp.utils import change_extn, slugify

content_docs = None

# ---------------------------------------------------------------------

def load_content_docs():
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
        kwargs = {}
        kwargs["mode"] = "rb" if binary else "r"
        if not binary:
            kwargs["encoding"] = "utf-8"
        with open( fname, **kwargs ) as fp:
            content_doc[ key ] = fp.read()

    # load each content doc
    fspec = os.path.join( dname, "*.index" )
    for fname in glob.glob( fspec ):
        fname = os.path.basename( fname )
        title = os.path.splitext( fname )[0]
        content_doc = {
            "doc_id": slugify( title ),
            "title": title,
        }
        get_doc( content_doc, "index", fname )
        get_doc( content_doc, "targets", change_extn(fname,".targets") )
        get_doc( content_doc, "footnotes", change_extn(fname,".footnotes") )
        get_doc( content_doc, "content", change_extn(fname,".pdf"), binary=True )
        content_docs[ content_doc["doc_id"] ] = content_doc

# ---------------------------------------------------------------------

@app.route( "/content-docs" )
def get_content_docs():
    """Return the available content docs."""
    resp = {}
    for cdoc in content_docs.values():
        cdoc2 = {
            "docId": cdoc["doc_id"],
            "title": cdoc["title"],
        }
        if "content" in cdoc:
            cdoc2["url"] = url_for( "get_content", doc_id=cdoc["doc_id"] )
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
