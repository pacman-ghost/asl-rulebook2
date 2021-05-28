""" Manage the ASOP. """

import os

from flask import jsonify, render_template_string, send_from_directory, safe_join, url_for, abort

from asl_rulebook2.webapp import app
from asl_rulebook2.webapp.content import tag_ruleids
from asl_rulebook2.webapp.utils import load_data_file

_asop = None
_asop_dir = None
_asop_preambles = None
_asop_section_content = None
_footer = None
user_css_url = None

# ---------------------------------------------------------------------

def init_asop( startup_msgs, logger ):
    """Initialize the ASOP."""

    # initiailize
    global _asop, _asop_dir, _asop_preambles, _asop_section_content, _footer, user_css_url
    _asop, _asop_preambles, _asop_section_content, _footer = {}, {}, {}, ""

    # get the data directory
    data_dir = app.config.get( "DATA_DIR" )
    if not data_dir:
        return None, None, None
    dname = os.path.join( data_dir, "asop/" )
    if not os.path.isdir( dname ):
        return None, None, None
    _asop_dir = dname
    fname = os.path.join( _asop_dir, "asop.css" )
    if os.path.isfile( fname ):
        user_css_url = url_for( "get_asop_file", path="asop.css" )

    # load the ASOP index
    fname = os.path.join( _asop_dir, "index.json" )
    _asop = load_data_file( fname, "ASOP index", "json", logger, startup_msgs.error )
    if not _asop:
        return None, None, None

    # load the ASOP content
    for chapter in _asop.get( "chapters", [] ):
        chapter_id = chapter[ "chapter_id" ]
        # load the chapter preamble
        preamble = _render_template( chapter_id + "-0.html" )
        if preamble:
            _asop_preambles[chapter_id] = preamble
        # load the content for each section
        for section_no, section in enumerate( chapter.get( "sections", [] ) ):
            section_id = "{}-{}".format( chapter_id, 1+section_no )
            section[ "section_id" ] = section_id
            content = _render_template( section_id + ".html" )
            _asop_section_content[ section_id ] = content

    # load the ASOP footer
    footer = _render_template( "footer.html" )
    _footer = tag_ruleids( footer, None )

    return _asop, _asop_preambles, _asop_section_content

# ---------------------------------------------------------------------

@app.route( "/asop" )
def get_asop():
    """Return the ASOP."""
    return jsonify( _asop )

@app.route( "/asop/intro" )
def get_asop_intro():
    """Return the ASOP intro."""
    resp = _render_template( "intro.html" )
    if not resp:
        return "No ASOP intro."
    return resp

@app.route( "/asop/footer" )
def get_asop_footer():
    """Return the ASOP footer."""
    if not _footer:
        abort( 404 )
    return _footer

@app.route( "/asop/preamble/<chapter_id>" )
def get_asop_preamble( chapter_id ):
    """Return the specified ASOP chapter preamble."""
    content = _asop_preambles.get( chapter_id )
    if not content:
        abort( 404 )
    return content

@app.route( "/asop/section/<section_id>" )
def get_asop_section( section_id ):
    """Return the specified ASOP section."""
    content = _asop_section_content.get( section_id )
    if not content:
        abort( 404 )
    return content

@app.route( "/asop/<path:path>" )
def get_asop_file( path ):
    """Return a user-defined ASOP file."""
    return send_from_directory( _asop_dir, path )

# ---------------------------------------------------------------------

def _render_template( fname ):
    """Render an ASOP template."""
    if not _asop_dir:
        return None
    fname = safe_join( _asop_dir, fname )
    if not os.path.isfile( fname ):
        return None
    args = {
        "ASOP_BASE_URL": url_for( "get_asop_file", path="" ),
    }
    args.update( _asop.get( "template_args", {} ) )
    with open( fname, "r" ) as fp:
        return render_template_string( fp.read(), **args )
