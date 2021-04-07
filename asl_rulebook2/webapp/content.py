""" Manage the content documents. """

import os
import re
import io
import glob

from flask import jsonify, send_file, url_for, abort

from asl_rulebook2.webapp import app
from asl_rulebook2.webapp.utils import load_data_file, slugify

_content_sets = None
_target_index = None
_footnote_index = None
_chapter_resources = None

_tag_ruleid_regexes = None

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
    global _content_sets, _target_index, _footnote_index, _chapter_resources
    _content_sets, _target_index, _footnote_index = {}, {}, {}
    _chapter_resources = { "background": {}, "icon": {} }

    # get the data directory
    data_dir = app.config.get( "DATA_DIR" )
    if not data_dir:
        return None
    if not os.path.isdir( data_dir ):
        startup_msgs.error( "Invalid data directory.", data_dir )
        return None

    def find_resource( fname, dnames ):
        # find a chapter resource file
        for dname in dnames:
            fname2 = os.path.join( dname, fname )
            if os.path.isfile( fname2 ):
                return fname2
        return None

    def load_content_doc( fname_stem, title, cdoc_id ):
        # load the content doc files
        content_doc = { "cdoc_id": cdoc_id, "title": title }
        if load_file( fname_stem+".targets", content_doc, "targets", startup_msgs.warning ):
            # update the target index
            _target_index[ cdoc_id ] = {}
            for ruleid, target in content_doc.get( "targets", {} ).items():
                _target_index[ cdoc_id ][ ruleid ] = target
        load_file( fname_stem+".chapters", content_doc, "chapters", startup_msgs.warning )
        if load_file( fname_stem+".footnotes", content_doc, "footnotes", startup_msgs.warning ):
            # update the footnote index
            # NOTE: The front-end doesn't care about what chapter a footnote belongs to,
            # and we rework things a bit to make it easier to map ruleid's to footnotes.
            if cdoc_id not in _footnote_index:
                _footnote_index[ cdoc_id ] = {}
            for chapter_id, footnotes in content_doc.get( "footnotes", {} ).items():
                for footnote_id, footnote in footnotes.items():
                    for caption in footnote.get( "captions", [] ):
                        footnote[ "display_name" ] = "{}{}".format( chapter_id, footnote_id )
                        ruleid = caption[ "ruleid" ]
                        if ruleid not in _footnote_index[ cdoc_id ]:
                            _footnote_index[ cdoc_id ][ ruleid ] = []
                        _footnote_index[ cdoc_id ][ ruleid ].append( footnote )
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
        data = load_data_file( fname, key, binary, logger, on_error )
        if data is None:
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
    for fname in sorted( glob.glob( fspec ) ):
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
        cdoc_id = cset_id # nb: because this the main content document
        content_doc = load_content_doc( fname_stem, fname_stem, cdoc_id )
        content_set[ "content_docs" ][ cdoc_id ] = content_doc
        # load any associated content docs
        for fname_stem2 in find_assoc_cdocs( fname_stem ):
            # nb: we assume there's only one space between the two filename stems :-/
            cdoc_id2 = "{}!{}".format( cdoc_id, slugify(fname_stem2) )
            content_doc = load_content_doc(
                "{} ({})".format( fname_stem, fname_stem2 ),
                fname_stem2,
                cdoc_id2
            )
            content_set[ "content_docs" ][ cdoc_id2 ] = content_doc
        # save the new content set
        _content_sets[ content_set["cset_id"] ] = content_set

    # generate a list of regex's that identify each ruleid
    global _tag_ruleid_regexes
    _tag_ruleid_regexes = {}
    for cset_id, cset in _content_sets.items():
        for cdoc_id, cdoc in cset["content_docs"].items():
            for ruleid in cdoc.get( "targets", {} ):
                # nb: we also want to detect things like A1.23-.45
                _tag_ruleid_regexes[ ruleid ] = re.compile(
                    r"\b{}(-\.\d+)?\b".format( ruleid.replace( ".", "\\." ) )
                )

    return _content_sets

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _dump_content_sets():
    """Dump the available content sets."""
    for cset_id, cset in _content_sets.items():
        print( "=== {} ({}) ===".format( cset["title"], cset_id ) )
        for cdoc_id, cdoc in cset["content_docs"].items():
            print( "Content doc: {} ({})".format( cdoc["title"], cdoc_id ) )
            for key in [ "targets", "footnotes", "content" ]:
                if key in cdoc:
                    print( "- {}: {}".format( key, len(cdoc[key]) ))

# ---------------------------------------------------------------------


def tag_ruleids( content, cset_id ):
    """Identify ruleid's in a piece of content and tag them.

    There are a lot of free-form ruleid's in the content (e.g. Q+A or ASOP,) which we would
    like to make clickable. We could do it in the front-end using regex's, but it gets
    quite tricky to do this reliably (e.g. "AbtF SSR CG.1a"), so we do things a different way.
    We already have a list of known ruleid's (i.e. the content set targets), so we look
    specifically for those in the content, and mark them with a special <span>, which the front-end
    can look for and convert into clickable links. It would be nice to detect ruleid's that
    we don't know about, and mark them accordingly in the UI, but then we're back in regex hell,
    so we can live without it.
    """

    # NOTE: This function is quite expensive, so it's worth doing a quick check to see if there's
    # any point looping through all the regex's e.g. it's pointless doing this for all those
    # numerous Q+A answers that just say "Yes." or "No." :-/
    if not content:
        return content
    if all( not c.isdigit() for c in content ):
        return content

    # NOTE: To avoid excessive string operations, we identify all ruleid matches first,
    # then fixup the string content in one pass.

    # look for ruleid matches in the content
    matches = []
    for ruleid, regex in _tag_ruleid_regexes.items():
        matches.extend(
            ( mo, ruleid )
            for mo in regex.finditer( content )
        )

    # sort the matches by start position, longer matches first
    matches.sort( key = lambda m: (
        m[0].start(), -len( m[0].group() )
    ) )

    # remove "duplicate" matches (e.g "A1.2" when we've already matched "A1.23")
    prev_match = [] # nb: we use [] instead of None to stop unsubscriptable-object warnings :-/
    for match_no, match in enumerate( matches ):
        if prev_match:
            if match[0].start() == prev_match[0].start():
                if match[0].group() == prev_match[0].group()[ : len(match[0].group()) ]:
                    # this is a "duplicate" match - delete it
                    matches[ match_no ] = None
                    continue
            assert match[0].start() > prev_match[0].end()
        prev_match = match
    matches = [ m for m in matches if m ]

    # tag the matches
    for match in reversed( matches ):
        mo = match[0]
        buf = [
            content[ : mo.start() ],
            "<span data-ruleid='{}' class='auto-ruleid'".format( match[1] )
        ]
        if cset_id:
            buf.append( " data-csetid='{}'".format( cset_id ) )
        buf.append( ">" )
        buf.extend( [
            mo.group(),
            "</span>",
            content[ mo.end() : ]
        ] )
        content = "".join( buf )

    return content

# ---------------------------------------------------------------------

@app.route( "/content-docs" )
def get_content_docs():
    """Return the available content docs."""
    resp = {}
    for cset in _content_sets.values():
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
    for cset in _content_sets.values():
        for cdoc in cset["content_docs"].values():
            if cdoc["cdoc_id"] == cdoc_id and "content" in cdoc:
                buf = io.BytesIO( cdoc["content"] )
                return send_file( buf, mimetype="application/pdf" )
    abort( 404 )
    return None # stupid pylint :-/

# ---------------------------------------------------------------------

@app.route( "/footnotes" )
def get_footnotes():
    """Return the footnote index."""
    return jsonify( _footnote_index )

# ---------------------------------------------------------------------

@app.route( "/chapter/<chapter_id>/<rtype>" )
def get_chapter_resource( chapter_id, rtype ):
    """Return a chapter resource."""
    fname = _chapter_resources.get( rtype, {} ).get( chapter_id )
    if not fname:
        abort( 404 )
    return send_file( fname )
