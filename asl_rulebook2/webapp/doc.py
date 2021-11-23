""" Serve documentation files. """

import os
import io
import re

import markdown
from flask import make_response, send_file, abort, safe_join

from asl_rulebook2.webapp import app

# ---------------------------------------------------------------------

@app.route( "/doc/<path:path>" )
def get_doc( path ):
    """Return the specified documentation file."""

    # locate the documentation file
    doc_dir = os.path.join( os.path.dirname( __file__ ), "../../doc/" )
    fname = safe_join( doc_dir, path )
    if not os.path.isfile( fname ):
        abort( 404 )

    # check if the file is Markdown
    if os.path.splitext( path )[1] == ".md":
        # yup - convert it to HTML
        buf = io.BytesIO()
        markdown.markdownFromFile( input=fname, output=buf, encoding="utf-8" )
        # FUDGE! Code fragments are wrapped with <code> tags, and while we would like to style them using CSS,
        # there's no way to distinguish between inline and block fragments :-/ We identify block fragments
        # by the <code> tag being at the start of a line, and style them using inline attributes. Sigh...
        code = b"<code style='display:block;white-space:pre;margin:0.5em 0 1em 2em;'>"
        resp = re.sub( rb"^<code>", code, buf.getvalue(), flags=re.MULTILINE )
        resp = make_response( resp )
        resp.mimetype = "text/html"
        return resp
    else:
        # nope - just serve it as-is
        return send_file( fname )
