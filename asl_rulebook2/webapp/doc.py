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
    dname = os.path.join( os.path.dirname( __file__ ), "../../doc/" )
    fname = safe_join( dname, path )
    if not os.path.isfile( fname ):
        # FUDGE! If this package has been installed in non-editable mode (i.e. into site-packages, while it's possible
        # to get the root doc/ directory included in the installation (by adding a __init__.py file :-/, then including
        # it in MANIFEST.in), it ends up in asl-rulebook2's parent directory (i.e. the main site-packages directory),
        # which is definitely not what we want.
        # We work-around this my creating a symlink to the doc/ directory, which will get followed when the package
        # is installed. This won't work on Windows, but we'll do the necessary penance, and just live with it... :-/
        dname = os.path.join( os.path.dirname( __file__ ), "data/doc/" )
        fname = safe_join( dname, path )
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
