""" Manage the search engine. """

import os
import sqlite3
import json
import re
import itertools
import string
import tempfile
import logging
import traceback

from flask import request, jsonify

from asl_rulebook2.utils import plural
from asl_rulebook2.webapp import app
from asl_rulebook2.webapp import content as webapp_content
from asl_rulebook2.webapp.utils import make_config_path, make_data_path

_sqlite_path = None
_fts_index_entries= None

_logger = logging.getLogger( "search" )

# these are used to highlight search matches (nb: the front-end looks for these)
_BEGIN_HIGHLIGHT = "!@:"
_END_HIGHLIGHT = ":@!"

# NOTE: These regex's fix up content returned to us by the SQLite search engine (typically problems
# with highlighting search terms).
_FIXUP_TEXT_REGEXES = [
    [ re.compile( fixup[0].format( _BEGIN_HIGHLIGHT, _END_HIGHLIGHT ) ),
      fixup[1].format( _BEGIN_HIGHLIGHT, _END_HIGHLIGHT )
    ]
    for fixup in [
        [ r"&{}(.+?){};", r"{}&\g<1>;{}" ], # HTML entities e.g. &((frac12)); -> (($frac12;))
        [ r"{}(.+?){}#", r"{}\g<1>#{}" ], # e.g. ((TH)# -> ((TH#)
        [ r"{}U\.S{}\.", "{}U.S.{}" ], # ((U.S)). -> ((U.S.))
    ]
]

# these are used to separate ruleref's in the FTS table (internal use only)
_RULEREF_SEPARATOR = "-:-"

_SEARCH_TERM_ADJUSTMENTS = None

# ---------------------------------------------------------------------

@app.route( "/search", methods=["POST"] )
def search() :
    """Run a search."""

    # log the request
    _logger.info( "SEARCH REQUEST:" )
    args = dict( request.form.items() )
    for key,val in args.items():
        _logger.info( "- %s: %s", key, val )

    # run the search
    try:
        return _do_search( args )
    except Exception as exc: #pylint: disable=broad-except
        msg = str( exc )
        if msg.startswith( "fts5: " ):
            msg = msg[5:] # nb: this is a sqlite3.OperationalError
        _logger.warning( "SEARCH ERROR: %s\n%s", args, traceback.format_exc() )
        return jsonify( { "error": msg } )

def _do_search( args ):

    def fixup_text( val ):
        if val is None:
            return None
        for regex in _FIXUP_TEXT_REGEXES:
            val = regex[0].sub( regex[1], val )
        return val

    # run the search
    query_string = args[ "queryString" ].strip()
    if query_string == "!:simulated-error:!":
        raise RuntimeError( "Simulated error." ) # nb: for the test suite
    fts_query_string, search_terms = _make_fts_query_string( query_string )
    _logger.debug( "FTS query string: %s", fts_query_string )
    conn = sqlite3.connect( _sqlite_path )
    def highlight( n ):
         # NOTE: highlight() is an FTS extension function, and takes column numbers :-/
        return "highlight(searchable,{},'{}','{}')".format( n, _BEGIN_HIGHLIGHT, _END_HIGHLIGHT )
    sql = "SELECT rowid,cset_id,sr_type,rank,{},{},{},{} FROM searchable".format(
        highlight(2), highlight(3), highlight(4), highlight(5)
    )
    sql += " WHERE searchable MATCH ?"
    sql += " ORDER BY rank"
    curs = conn.execute( sql,
        ( "{title subtitle content rulerefs}: " + fts_query_string, )
    )

    def get_col( sr, key, val ):
        if val:
            sr[key] = fixup_text( val )

    # get the results
    results = []
    for row in curs:
        if row[2] != "index":
            _logger.error( "Unknown searchable row type (rowid=%d): %s", row[0], row[2] )
            continue
        index_entry = _fts_index_entries[ row[0] ]
        result = {
            "cset_id": row[1],
            "sr_type": row[2],
            "_key": "{}:{}:{}".format( row[1], row[2], row[0] ),
            "_score": - row[3],
        }
        get_col( result, "title", row[4] )
        get_col( result, "subtitle", row[5] )
        get_col( result, "content", row[6] )
        if index_entry.get( "ruleids" ):
            result["ruleids"] = index_entry["ruleids"]
        if index_entry.get( "see_also" ):
            result["see_also"] = index_entry["see_also"]
        rulerefs = [ r.strip() for r in row[7].split(_RULEREF_SEPARATOR) ] if row[7] else []
        assert len(rulerefs) == len(index_entry.get("rulerefs",[]))
        if rulerefs:
            result[ "rulerefs" ] = []
            for i, ruleref in enumerate(rulerefs):
                ruleref2 = {}
                if "caption" in index_entry["rulerefs"][i]:
                    assert ruleref.replace( _BEGIN_HIGHLIGHT, "" ).replace( _END_HIGHLIGHT, "" ) \
                           == index_entry["rulerefs"][i]["caption"].strip()
                    ruleref2["caption"] = fixup_text( ruleref )
                if "ruleids" in index_entry["rulerefs"][i]:
                    ruleref2["ruleids"] = index_entry["rulerefs"][i]["ruleids"]
                assert ruleref2
                result["rulerefs"].append( ruleref2 )
        results.append( result )

    # fixup the results
    results = _fixup_results_for_hash_terms( results, search_terms )

    # adjust the sort order
    results = _adjust_sort_order( results )

    # return the results
    _logger.debug( "Search results:" if len(results) > 0 else "Search results: none" )
    for result in results:
        _logger.debug( "- %s (%.3f)",
           result["title"].replace( _BEGIN_HIGHLIGHT, "" ).replace( _END_HIGHLIGHT, "" ),
           result["_score"]
        )
    return jsonify( results )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

PASSTHROUGH_REGEXES = set([
    re.compile( r"\bAND\b" ),
    re.compile( r"\bOR\b" ),
    re.compile( r"\bNOT\b" ),
    re.compile( r"\((?![Rr]\))" ),
])

def _make_fts_query_string( query_string ):
    """Generate the SQLite query string.

    SQLite's MATCH function recognizes a lot of special characters, which need
    to be enclosed in double-quotes to disable.
    """

    # check if this looks like a raw FTS query
    if any( regex.search(query_string) for regex in PASSTHROUGH_REGEXES ):
        return query_string.strip(), None

    # split the search string into words (taking quoted phrases into account)
    ignore = app.config.get( "SQLITE_FTS_IGNORE_CHARS", ",;!?$" )
    query_string = "".join( ch for ch in query_string if ch not in ignore )
    terms = query_string.lower().split()
    i = 0
    while True:
        if i >= len(terms):
            break
        if i > 0 and terms[i-1].startswith( '"' ):
            terms[i-1] += " {}".format( terms[i] )
            del terms[i]
            if terms[i-1].startswith( '"' ) and terms[i-1].endswith( '"' ):
                terms[i-1] = terms[i-1][1:-1]
            continue
        i += 1

    # clean up quoted phrases
    terms = [ t[1:] if t.startswith('"') else t for t in terms ]
    terms = [ t[:-1] if t.endswith('"') else t for t in terms ]
    terms = [ t.strip() for t in terms ]
    terms = [ t for t in terms if t ]

    # adjust search terms
    for term_no, term in enumerate(terms):
        aliases = _SEARCH_TERM_ADJUSTMENTS.get( term )
        if not aliases:
            continue
        if isinstance( aliases, str ):
            # the search term is replaced by a new one
            terms[ term_no ] = aliases
        elif isinstance( aliases, set ):
            # the search term is replaced by multiple new ones (that will be OR'ed together)
            # NOTE: We sort the terms so that the tests will work reliably.
            terms[ term_no ] = sorted( aliases )
        else:
            assert "Unknown search alias type: {}".format( type(aliases) )

    # fixup each term
    def has_special_char( term ):
        """Check if the term contains any special characters."""
        for ch in term:
            if ch in "*":
                continue
            if ch.isspace() or ch in string.punctuation:
                return True
            if ord(ch) < 32 or ord(ch) > 127:
                return True
        return False
    def fixup_terms( terms ):
        """Fixup a list of terms."""
        for term_no, term in enumerate(terms):
            if isinstance( term, str ):
                if has_special_char( term ):
                    terms[term_no] = '"{}"'.format( term )
            else:
                fixup_terms( term )
    fixup_terms( terms )

    # return the final FTS query string
    def term_string( term ):
        if isinstance( term, str ):
            return term
        assert isinstance( term, list )
        return "( {} )".format( " OR ".join( term ) )
    return " AND ".join( term_string(t) for t in terms ), terms

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _fixup_results_for_hash_terms( results, search_terms ):
    """Fixup search results for search terms that end with a hash.

    SQLite doesn't handle search terms that end with a hash particularly well.
    We correct highlighted search terms in fixup_text(), but searching for e.g. "US#"
    will also match "use" and "using" - we remove such results here.
    """

    # figure out which search terms end with a hash
    # NOTE: We don't bother descending down into sub-terms.
    if not search_terms:
        return results
    terms = [
        t[1:-1] for t in search_terms
        if isinstance(t,str) and t.startswith('"') and t.endswith('"')
    ]
    terms = [
        t[:-1].lower() for t in terms
        if isinstance(t,str) and t.endswith("#")
    ]
    if not terms:
        return results
    if "us" in terms:
        terms.extend( [ "use", "used", "using", "user" ] )

    def keep( sr ):
        # remove every incorrectly matched search term (e.g. ((K)) when searching for "K#")
        buf = json.dumps( sr ).lower()
        for term in terms:
            buf = buf.replace( "{}{}{}".format( _BEGIN_HIGHLIGHT, term, _END_HIGHLIGHT ), "_removed_" )
        # we keep this search result if there are still some highlighted search terms
        return _BEGIN_HIGHLIGHT in buf

    return [
        result for result in results if keep(result)
    ]

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _adjust_sort_order( results ):
    """Adjust the sort order of the search results."""

    results2 = []
    def extract_sr( func ):
        # move results that pass the filter function to the new list
        i = 0
        while True:
            if i >= len(results):
                break
            # NOTE: We never prefer small entries (i.e .have no ruleref's)
            # e.g. those that only contain a "see also".
            if func( results[i] ) and len(results[i].get("rulerefs",[])) > 0:
                results2.append( results[i] )
                del results[i]
            else:
                i += 1

    def get( sr, key ):
        val = sr.get( key )
        return val if val else ""

    # prefer search results whose title is an exact match
    extract_sr(
        lambda sr: get(sr,"title").startswith( _BEGIN_HIGHLIGHT ) and get(sr,"title").endswith( _END_HIGHLIGHT )
    )
    # prefer search results whose title starts with a match
    extract_sr(
        lambda sr: get(sr,"title").startswith( _BEGIN_HIGHLIGHT )
    )
    # prefer search results that have a match in the title
    extract_sr(
        lambda sr: _BEGIN_HIGHLIGHT in get(sr,"title")
    )
    # prefer search results that have a match in the subtitle
    extract_sr(
        lambda sr: _BEGIN_HIGHLIGHT in get(sr,"subtitle")
    )

    # include any remaining search results
    results2.extend( results )

    return results2

# ---------------------------------------------------------------------

def init_search( startup_msgs, logger ):
    """Initialize the search engine."""

    # initialize
    global _fts_index_entries
    _fts_index_entries = {}

    # initialize the database
    global _sqlite_path
    _sqlite_path = app.config.get( "SQLITE_PATH" )
    if not _sqlite_path:
        # FUDGE! We should be able to create a shared, in-memory database using this:
        #   file::XYZ:?mode=memory&cache=shared
        # but it doesn't seem to work (on Linux) and ends up creating a file with this name :-/
        # We manually create a temp file, which has to have the same name each time, so that we don't
        # keep creating a new database each time we start up. Sigh...
        _sqlite_path = os.path.join( tempfile.gettempdir(), "asl-rulebook2.searchdb" )
    if os.path.isfile( _sqlite_path ):
        os.unlink( _sqlite_path )
    logger.info( "Creating the search index: %s", _sqlite_path )
    conn = sqlite3.connect( _sqlite_path )
    # NOTE: Storing everything in a single table allows FTS to rank search results based on
    # the overall content, and also lets us do AND/OR queries across all searchable content.
    conn.execute(
        "CREATE VIRTUAL TABLE searchable USING fts5"
        " ( cset_id, sr_type, title, subtitle, content, rulerefs, tokenize='porter unicode61' )"
    )

    # load the searchable content
    logger.info( "Loading the search index..." )
    conn.execute( "DELETE FROM searchable" )
    curs = conn.cursor()
    for cset in webapp_content.content_sets.values():
        logger.info( "- Loading index file: %s", cset["index_fname"] )
        nrows = 0
        for index_entry in cset["index"]:
            rulerefs = _RULEREF_SEPARATOR.join( r.get("caption","") for r in index_entry.get("rulerefs",[]) )
            # NOTE: We should really strip content before adding it to the search index, otherwise any HTML tags
            # will need to be included in search terms. However, this means that the content returned by a query
            # will be this stripped content. We could go back to the original data to get the original HTML content,
            # but that means we would lose the highlighting of search terms that SQLite gives us. We opt to insert
            # the original content, since none of it should contain HTML, anyway.
            curs.execute(
                "INSERT INTO searchable (cset_id,sr_type,title,subtitle,content,rulerefs) VALUES (?,?,?,?,?,?)", (
                    cset["cset_id"], "index",
                    index_entry.get("title"), index_entry.get("subtitle"), index_entry.get("content"), rulerefs
            ) )
            _fts_index_entries[ curs.lastrowid ] = index_entry
            index_entry["_fts_rowid"] = curs.lastrowid
            nrows += 1
        conn.commit()
        logger.info( "  - Loaded %s.", plural(nrows,"index entry","index entries"),  )
    assert len(_fts_index_entries) == _get_row_count( conn, "searchable" )

    # load the search config
    load_search_config( startup_msgs, logger )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def load_search_config( startup_msgs, logger ):
    """Load the search config."""

    # initialize
    global _SEARCH_TERM_ADJUSTMENTS
    _SEARCH_TERM_ADJUSTMENTS = {}

    def add_search_term_adjustment( key, vals ):
        # make sure everything is lower-case
        key = key.lower()
        if isinstance( vals, str ):
            vals = vals.lower()
        elif isinstance( vals, set ):
            vals = set( v.lower() for v in vals )
        else:
            assert "Unknown search alias type: {}".format( type(vals) )
        # add new the search term adjustment
        if key not in _SEARCH_TERM_ADJUSTMENTS:
            _SEARCH_TERM_ADJUSTMENTS[ key ] = vals
        else:
            # found a multiple definition - try to do something sensible
            logger.warning( "  - Duplicate search alias: %s\n- current aliases = %s\n- new aliases = %s", key,
                _SEARCH_TERM_ADJUSTMENTS[key], vals
            )
            if isinstance( _SEARCH_TERM_ADJUSTMENTS[key], str ):
                _SEARCH_TERM_ADJUSTMENTS[ key ] = vals
            else:
                assert isinstance( _SEARCH_TERM_ADJUSTMENTS[key], set )
                _SEARCH_TERM_ADJUSTMENTS[ key ].update( vals )

    # load the search replacements
    def load_search_replacements( fname, ftype ):
        if not os.path.isfile( fname ):
            return
        logger.info( "Loading search replacements: %s", fname )
        try:
            with open( fname, "r", encoding="utf-8" ) as fp:
                data = json.load( fp )
        except Exception as ex: #pylint: disable=broad-except
            startup_msgs.warning( "Can't load {} search replacements.".format( ftype ), str(ex) )
            return
        nitems = 0
        for key, val in data.items():
            if key.startswith( "_" ):
                continue # nb: ignore comments
            logger.debug( "- %s -> %s", key, val )
            add_search_term_adjustment( key, val )
            nitems += 1
        logger.info( "- Loaded %s.", plural(nitems,"search replacement","search replacements") )
    load_search_replacements( make_config_path( "search-replacements.json" ), "default" )
    load_search_replacements( make_data_path( "search-replacements.json" ), "user" )

    # load the search aliases
    def load_search_aliases( fname, ftype ):
        if not os.path.isfile( fname ):
            return
        logger.info( "Loading search aliases: %s", fname )
        try:
            with open( fname, "r", encoding="utf-8" ) as fp:
                data = json.load( fp )
        except Exception as ex: #pylint: disable=broad-except
            startup_msgs.warning( "Can't load {} search aliases.".format( ftype ), str(ex) )
            return
        nitems = 0
        for keys, aliases in data.items():
            if keys.startswith( "_" ):
                continue # nb: ignore comments
            logger.debug( "- %s -> %s", keys, " ; ".join(aliases) )
            for key in keys.split( "/" ):
                add_search_term_adjustment( key, set( itertools.chain( aliases, [key] ) ) )
            nitems += 1
        logger.info( "- Loaded %s.", plural(nitems,"search aliases","search aliases") )
    load_search_aliases( make_config_path( "search-aliases.json" ), "default" )
    load_search_aliases( make_data_path( "search-aliases.json" ), "user" )

    # load the search synonyms
    def load_search_synonyms( fname, ftype ):
        if not os.path.isfile( fname ):
            return
        logger.info( "Loading search synonyms: %s", fname )
        try:
            with open( fname, "r", encoding="utf-8" ) as fp:
                data = json.load( fp )
        except Exception as ex: #pylint: disable=broad-except
            startup_msgs.warning( "Can't load {} search synonyms.".format( ftype ), str(ex) )
            return
        nitems = 0
        for synonyms in data:
            if isinstance( synonyms, str ):
                continue # nb: ignore comments
            logger.debug( "- %s", " ; ".join(synonyms) )
            synonyms = set( synonyms )
            for term in synonyms:
                add_search_term_adjustment( term, synonyms )
            nitems += 1
        logger.info( "- Loaded %s.", plural(nitems,"search synonym","search synonyms") )
    load_search_synonyms( make_config_path( "search-synonyms.json" ), "default" )
    load_search_synonyms( make_data_path( "search-synonyms.json" ), "user" )

# ---------------------------------------------------------------------

def _get_row_count( conn, table_name ):
    """Get the number of rows in a table."""
    cur = conn.execute( "SELECT count(*) FROM {}".format( table_name ) )
    return cur.fetchone()[0]
