""" Manage the search engine. """

import os
import shutil
import threading
import sqlite3
import hashlib
import io
import json
import re
import itertools
import string
import copy
import time
import tempfile
import logging
import traceback

from flask import request, jsonify
import lxml.html

from asl_rulebook2.utils import plural
from asl_rulebook2.webapp import app
from asl_rulebook2.webapp import startup as webapp_startup
from asl_rulebook2.webapp.content import tag_ruleids
from asl_rulebook2.webapp.utils import make_config_path, make_data_path, split_strip

_searchdb_fname = None
_cached_searchdb_fname = None
_fts_index = None
_fixup_content_lock = threading.Lock()

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

# NOTE: This regex identifies highlight markers that SQLite has inadvertently inserted *inside* an HTML tag,
# because it is treating the searchable content as plain-text, and not HTML. There could be multiple cases
# of this within a single tag, so we identify any such tag first, then do a simple search-and-replace
# to remove the highlight markers.
# NOTE: The content has cases of naked <'s e.g. "move < 2 MP", so we need to be careful not to get tripped up
# by these.
_HILITES_INSIDE_HTML_TAG_REGEX = re.compile(
    r"\<\S[^>]*?{}.*?\>".format( _BEGIN_HIGHLIGHT )
)

# these are used to separate ruleref's in the FTS table
_RULEREF_SEPARATOR = "-:-"

# these are used to separate Q+A fields in the FTS table
_QA_CONTENT_SEPERATOR = " !=! "
_QA_FIELD_SEPARATOR = " :-: "
_NO_QA_QUESTION = "_??_"

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
    # NOTE: We can't use the search index nor in-memory data structures if the startup tasks thread
    # is still running (and possible updating them, as it fixes up content). However, the tasks running
    # in that thread relinquish the lock regularly, to give the user a chance to jump in and grab it here,
    # if they want to do a search while that thread is still running.
    with _fixup_content_lock:
        try:
            return _do_search( args )
        except Exception as exc: #pylint: disable=broad-except
            msg = str( exc )
            if msg.startswith( "fts5: " ):
                msg = msg[5:] # nb: this is a sqlite3.OperationalError
            _logger.warning( "SEARCH ERROR: %s\n%s", args, traceback.format_exc() )
            return jsonify( { "error": msg } )

def _do_search( args ):

    # run the search
    query_string = args[ "queryString" ].strip()
    if query_string == "!:simulated-error:!":
        raise RuntimeError( "Simulated error." ) # nb: for the test suite
    if not query_string:
        raise RuntimeError( "Missing query string." )
    fts_query_string, search_terms = _make_fts_query_string( query_string )
    _logger.debug( "FTS query string: %s", fts_query_string )
    conn = sqlite3.connect( _searchdb_fname )
    def highlight( n ):
         # NOTE: highlight() is an FTS extension function, and takes column numbers :-/
        return "highlight(searchable,{},'{}','{}')".format( n, _BEGIN_HIGHLIGHT, _END_HIGHLIGHT )
    sql = "SELECT rowid, sr_type, cset_id, rank, {}, {}, {}, {} FROM searchable".format(
        highlight(2), highlight(3), highlight(4), highlight(5)
    )
    sql += " WHERE searchable MATCH ?"
    sql += " ORDER BY rank"
    curs = conn.execute( sql,
        ( "{title subtitle content rulerefs}: " + fts_query_string, )
    )

    def remove_bad_hilites( val ):
        # remove highlight markers that SQLite may have incorrectly inserted into a value
        if val is None:
            return None
        matches = list( _HILITES_INSIDE_HTML_TAG_REGEX.finditer( val ) )
        for mo in reversed( matches ):
            match = mo.group().replace( _BEGIN_HIGHLIGHT, "" ).replace( _END_HIGHLIGHT, "" )
            val = val[:mo.start()] + match + val[mo.end():]
        return val

    # get the results
    results = []
    for row in curs:
        row = list( row )
        for col_no in range( 4, 7+1 ):
            row[col_no] = remove_bad_hilites( row[col_no] )
        if row[1] == "index":
            result = _unload_index_sr( row )
        elif row[1] == "qa":
            result = _unload_qa_sr( row )
        elif row[1] == "errata":
            result = _unload_anno_sr( row, "errata" )
        elif row[1] == "user-anno":
            result = _unload_anno_sr( row, "user-anno" )
        elif row[1] == "asop-entry":
            result = _unload_asop_entry_sr( row )
        else:
            _logger.error( "Unknown searchable row type (rowid=%d): %s", row[0], row[1] )
            continue
        if not result:
            continue
        result.update( {
            "sr_type": row[1],
            "_score": - row[3],
        } )
        results.append( result )

    # fixup the results
    results = _fixup_results_for_hash_terms( results, search_terms )

    # adjust the sort order
    results = _adjust_sort_order( results )

    # return the results
    if _logger.isEnabledFor( logging.DEBUG ):
        _logger.debug( "Search results:" if len(results) > 0 else "Search results: none" )
        for result in results:
            title = result.get( "title", result.get("caption","???") )
            _logger.debug( "- %s: %s (%.3f)",
                result["_fts_rowid"],
                title.replace( _BEGIN_HIGHLIGHT, "" ).replace( _END_HIGHLIGHT, "" ),
                result["_score"]
            )
    return jsonify( results )

def _unload_index_sr( row ):
    """Unload an index search result from the database."""
    index_entry = _fts_index["index"][ row[0] ] # nb: our copy of the index entry (must remain unchanged)
    result = copy.deepcopy( index_entry ) # nb: the index entry we will return to the caller
    result[ "cset_id" ] = row[2]
    _get_result_col( result, "title", row[4] )
    _get_result_col( result, "subtitle", row[5] )
    _get_result_col( result, "content", row[6] )
    rulerefs = split_strip( row[7], _RULEREF_SEPARATOR ) if row[7] else []
    assert len(rulerefs) == len(index_entry.get("rulerefs",[]))
    if rulerefs:
        result[ "rulerefs" ] = []
        for i, ruleref in enumerate(rulerefs):
            ruleref2 = {}
            if "caption" in index_entry["rulerefs"][i]:
                assert ruleref.replace( _BEGIN_HIGHLIGHT, "" ).replace( _END_HIGHLIGHT, "" ) \
                       == index_entry["rulerefs"][i]["caption"].strip()
                ruleref2["caption"] = _fixup_text( ruleref )
            if "ruleids" in index_entry["rulerefs"][i]:
                ruleref2["ruleids"] = index_entry["rulerefs"][i]["ruleids"]
            assert ruleref2
            result["rulerefs"].append( ruleref2 )
    return result

def _unload_qa_sr( row ):
    """Unload a Q+A search result from the database."""
    qa_entry = _fts_index["qa"][ row[0] ] # nb: our copy of the Q+A entry (must remain unchanged)
    result = copy.deepcopy( qa_entry ) # nb: the Q+A entry we will return to the caller (will be changed)
    # replace the content in the Q+A entry we will return to the caller with the values
    # from the search index (which will have search term highlighting)
    if row[4]:
        result["caption"] = row[4]
    sr_content = split_strip( row[6], _QA_CONTENT_SEPERATOR ) if row[6] else []
    qa_entry_content = qa_entry.get( "content", [] )
    if len(sr_content) != len(qa_entry_content):
        _logger.error( "Mismatched # content's for Q+A entry: %s", qa_entry )
        return None
    for content_no, content in enumerate( qa_entry_content ):
        fields = split_strip( sr_content[content_no], _QA_FIELD_SEPARATOR )
        answers = content.get( "answers", [] )
        if len(fields) - 1 != len(answers): # nb: fields = question + answer 1 + answer 2 + ...
            _logger.error( "Mismatched # answers for content %d: %s\n- answers = %s", content_no, qa_entry, answers )
            return None
        if fields[0] != _NO_QA_QUESTION:
            result["content"][content_no]["question"] = fields[0]
        for answer_no, _ in enumerate(answers):
            result["content"][content_no]["answers"][answer_no][0] = fields[ 1+answer_no ]
    return result

def _unload_anno_sr( row, atype ):
    """Unload an annotation search result from the database."""
    anno = _fts_index[atype][ row[0] ] # nb: our copy of the annotation (must remain unchanged)
    result = copy.deepcopy( anno ) # nb: the annotation we will return to the caller (will be changed)
    _get_result_col( result, "content", row[6] )
    return result

def _unload_asop_entry_sr( row ):
    """Unload an ASOP entry search result from the database."""
    section = _fts_index["asop-entry"][ row[0] ][0] # nb: our copy of the ASOP section (must remain unchanged)
    result = copy.deepcopy( section ) # nb: the ASOP section we will return to the caller (will be changed)
    _get_result_col( result, "content", row[6] )
    return result

def _fixup_text( val ):
    """Fix-up a text value retrieved from the search index."""
    if val is None:
        return None
    for regex in _FIXUP_TEXT_REGEXES:
        val = regex[0].sub( regex[1], val )
    return val

def _get_result_col( sr, key, val ):
    """Get a column from a search result."""
    if val:
        sr[ key ] = _fixup_text( val )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

PASSTHROUGH_REGEXES = set([
    re.compile( r"\bAND\b" ),
    re.compile( r"\bOR\b" ),
    re.compile( r"\bNOT\b" ), # nb: this is a binary operator i.e. x NOT y = x && !x
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
    We correct highlighted search terms in _fixup_text(), but searching for e.g. "US#"
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
    def extract_sr( func, force=False ):
        # move results that pass the filter function to the new list
        i = 0
        while True:
            if i >= len(results):
                break
            # NOTE: We don't want to prefer useless entries e.g. those that only contain a "see also".
            nruleids = len( results[i].get( "ruleids", [] ) )
            nrulerefs = len( results[i].get( "rulerefs", [] ) )
            if func( results[i] ) and ( force or nruleids > 0 or nrulerefs > 0 ):
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
    # prefer user annotations
    extract_sr(
        lambda sr: get(sr,"sr_type") == "user-anno",
        force = True
    )
    # prefer errata
    extract_sr(
        lambda sr: get(sr,"sr_type") == "errata",
        force = True
    )
    # prefer rules
    extract_sr(
        lambda sr: get(sr,"sr_type") == "index",
        force = True
    )

    # include any remaining search results
    results2.extend( results )

    return results2

# ---------------------------------------------------------------------

def init_search( content_sets, #pylint: disable=too-many-arguments
    qa, qa_fnames,
    errata, errata_fnames,
    user_anno, user_anno_fname,
    asop, asop_preambles, asop_content, asop_fnames,
    startup_msgs, logger
):
    """Initialize the search engine."""

    # initialize
    global _fts_index
    _fts_index = { "index": {}, "qa": {}, "errata": {}, "user-anno": {}, "asop-entry": {} }

    # locate the database
    global _searchdb_fname
    _searchdb_fname = app.config.get( "SEARCHDB" )
    if not _searchdb_fname:
        # FUDGE! We should be able to create a shared, in-memory database using this:
        #   file::XYZ:?mode=memory&cache=shared
        # but it doesn't seem to work (on Linux) and ends up creating a file with this name :-/
        # We manually create a temp file, which has to have the same name each time, so that we don't
        # keep creating a new database each time we start up. Sigh...
        _searchdb_fname = os.path.join( tempfile.gettempdir(), "asl-rulebook2.searchdb" )

    def init_searchdb():
        _init_searchdb( content_sets,
            qa, qa_fnames,
            errata, errata_fnames,
            user_anno, user_anno_fname,
            asop, asop_preambles, asop_content, asop_fnames,
            logger
        )

    # check if we should force the database to be built from a cached version
    # NOTE: This should only be done for running tests (to ensure that database was built correctly).
    if app.config.get( "FORCE_CACHED_SEARCHDB" ):
        # initialize the database using a new cache file (this will force the creation of the cached version)
        fname = os.path.join( tempfile.gettempdir(), "asl-rulebook2.searchdb-forced_cache" )
        if os.path.isfile( fname ):
            os.unlink( fname )
        app.config[ "CACHED_SEARCHDB" ] = fname
        assert webapp_startup._startup_tasks == [] #pylint: disable=protected-access
        init_searchdb()
        webapp_startup._do_startup_tasks( False ) #pylint: disable=protected-access
        webapp_startup._startup_tasks = [] #pylint: disable=protected-access
        # NOTE: When we continue on from here, the database will be initialized again, using the cached version.

    # initialize the database
    init_searchdb()

    # load the search config
    load_search_config( startup_msgs, logger )

def _init_searchdb( content_sets, #pylint: disable=too-many-arguments
    qa, qa_fnames,
    errata, errata_fnames,
    user_anno, user_anno_fname,
    asop, asop_preambles, asop_content, asop_fnames,
    logger
):
    """Initialize the search database."""

    # NOTE: Building the database can be a slow process if there is a lot of content (e.g. Q+A), since we are
    # runnning many regex's over them, to identify ruleid's that should be converted to links. So, we offer
    # the option to take a copy of the database after it has been built, and use that the next time we run.
    # However, the initialization process is complicated, and we can't just use that cached database (e.g. because
    # we also need to update in-memory objects), so instead, we build the database in the normal way, but where
    # we would normally run the regex's, we instead grab the result from the cached database, and update
    # the in-memory objects as required (see _fixup_searchable_content()). This gives significantly faster times
    # for the startup tasks:
    #                   rebuild cached
    #   vm-linux-dev2   2:04    0:01
    #   Raspberry Pi 4  4:11    0:01
    #   Banana Pi       17:59   0:08

    # check if there is a cached database
    global _cached_searchdb_fname
    _cached_searchdb_fname = None
    fname = app.config.get( "CACHED_SEARCHDB" )
    # NOTE: We treat an empty file as being not present since files must exist to be able to mount them
    # into Docker (run-container.sh creates the file if it is being created for this first time).
    if fname and os.path.isfile( fname ) and os.path.getsize( fname ) > 0:
        # yup - compare the file hashes
        logger.debug( "Checking cached search database: %s", fname )
        with sqlite3.connect( fname ) as conn:
            conn.row_factory = sqlite3.Row
            curs = conn.cursor()
            query = curs.execute( "SELECT * from file_hash" )
            old_file_hashes = [ dict(row) for row in query ]
            logger.debug( "- cached hashes:\n%s", _dump_file_hashes( old_file_hashes, prefix="  " ) )
            curr_file_hashes = _make_file_hashes(
                content_sets, qa_fnames, errata_fnames, user_anno_fname, asop_fnames
            )
            logger.debug( "- curr. hashes:\n%s", _dump_file_hashes( curr_file_hashes, prefix="  " ) )
            if old_file_hashes == curr_file_hashes:
                # the file hashes are the same - flag that we should use the cached database
                logger.info( "Using cached search database: %s", fname )
                _cached_searchdb_fname = fname

    # initialize the database
    if os.path.isfile( _searchdb_fname ):
        os.unlink( _searchdb_fname )
    logger.info( "Creating the search index: %s", _searchdb_fname )
    conn = sqlite3.connect( _searchdb_fname )
    conn.execute( "PRAGMA journal = memory" )
    # NOTE: Storing everything in a single table allows FTS to rank search results based on
    # the overall content, and also lets us do AND/OR queries across all searchable content.
    conn.execute(
        "CREATE VIRTUAL TABLE searchable USING fts5"
        " ( sr_type, cset_id, title, subtitle, content, rulerefs, tokenize='porter unicode61' )"
    )

    # initialize the search index
    logger.info( "Building the search index..." )
    curs = conn.cursor()
    if content_sets:
        _init_content_sets( conn, curs, content_sets, logger )
    if qa:
        _init_qa( curs, qa, logger )
    if errata:
        _init_errata( curs, errata, logger )
    if user_anno:
        _init_user_anno( curs, user_anno, logger )
    if asop:
        _init_asop( curs, asop, asop_preambles, asop_content, logger )
    conn.commit()

    # save the file hashes
    logger.info( "Calculating file hashes..." )
    conn.execute( "CREATE TABLE file_hash ( ftype, fname, hash )" )
    file_hashes = _make_file_hashes(
        content_sets, qa_fnames, errata_fnames, user_anno_fname, asop_fnames
    )
    for fh in file_hashes:
        logger.debug( "- %s/%s = %s", fh["ftype"], fh["fname"], fh["hash"] )
        conn.execute( "INSERT INTO file_hash"
            " ( ftype, fname, hash )"
            " VALUES ( :ftype, :fname, :hash )",
            fh
        )
    conn.commit()

    # register a task for post-fixup processing
    fname = app.config.get( "CACHED_SEARCHDB" )
    if fname:
        def on_post_fixup():
            # check if the database was built using the cached version
            if _cached_searchdb_fname:
                # yup - validate what we built
                _check_searchdb( logger )
            else:
                # nope - save a copy of what we built (for next time)
                # NOTE: While VACUUM INTO is nice, it doesn't seem to work inside a Docker container,
                # and we can't use it anyway, since it may change rowid's :-(
                # NOTE: While SQLite sometimes creates additional files associated with the database:
                #   https://sqlite.org/tempfiles.html
                # I don't think any of these cases apply here, and we can just copy the database file itself.
                logger.info( "Saving a copy of the search database: %s", fname )
                shutil.copyfile( _searchdb_fname, fname )
        from asl_rulebook2.webapp.startup import _add_startup_task
        _add_startup_task( "post-fixup processing", on_post_fixup )

def _check_searchdb( logger ):
    """Compare the newly-built search database with the cached one."""

    with sqlite3.connect( _searchdb_fname ) as conn, sqlite3.connect( _cached_searchdb_fname ) as conn2:

        # check the number of rows
        nrows = _get_row_count( conn, "searchable" )
        nrows2 = _get_row_count( conn2, "searchable" )
        if nrows != nrows2:
            logger.error( "Searchable row count mismatch: got %d, expected %d", nrows, nrows2 )

        # check the row content
        query = "SELECT rowid, * FROM searchable ORDER BY rowid"
        curs = conn.execute( query )
        curs2 = conn2.execute( query )
        for _ in range( nrows ):
            row = curs.fetchone()
            row2 = curs2.fetchone()
            if row != row2:
                logger.error( "Search row mismatch:\n- got: %s\n- expected: %s", row, row2 )

    # NOTE: It would be nice to show an error balloon if we detected any problems here, but since
    # we are running in a startup task, it's too late (the UI will have already called $/startup-msgs).

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _init_content_sets( conn, curs, content_sets, logger ):
    """Add the content sets to the search index."""

    def make_fields( index_entry ):
        return {
            "subtitle": index_entry.get( "subtitle" ),
            "content": index_entry.get( "content" ),
        }

    # add the index entries to the search index
    # IMPORTANT! The insert order must be stable (so that we can match rows in the cached database by rowid).
    sr_type = "index"
    for cset_id in sorted( content_sets.keys() ):
        cset = content_sets[ cset_id ]
        logger.info( "- Adding index file: %s", cset["index_fname"] )
        nrows = 0
        assert isinstance( cset["index"], list )
        for index_entry in cset["index"]:
            rulerefs = _RULEREF_SEPARATOR.join( r.get("caption","") for r in index_entry.get("rulerefs",[]) )
            # NOTE: We should really strip content before adding it to the search index, otherwise any HTML tags
            # will need to be included in search terms. However, this means that the content returned by a query
            # will be this stripped content. We could go back to the original data to get the original HTML content,
            # but that means we would lose the highlighting of search terms that SQLite gives us. We opt to insert
            # the original content, since none of it should contain HTML, anyway.
            fields = make_fields( index_entry )
            curs.execute(
                "INSERT INTO searchable"
                " ( sr_type, cset_id, title, subtitle, content, rulerefs )"
                " VALUES ( ?, ?, ?, ?, ?, ? )", (
                    sr_type, cset["cset_id"],
                    index_entry.get("title"), fields["subtitle"], fields["content"], rulerefs
            ) )
            _fts_index[sr_type][ curs.lastrowid ] = index_entry
            index_entry["_fts_rowid"] = curs.lastrowid
            nrows += 1
        logger.info( "  - Added %s.", plural(nrows,"index entry","index entries"),  )
    assert len(_fts_index[sr_type]) == _get_row_count( conn, "searchable" )

    # register a task to fixup the content
    def fixup_row( rowid, cset_id ):
        index_entry = _fts_index[ sr_type ][ rowid ]
        _tag_ruleids_in_field( index_entry, "subtitle", cset_id )
        _tag_ruleids_in_field( index_entry, "content", cset_id )
        return index_entry
    from asl_rulebook2.webapp.startup import _add_startup_task
    _add_startup_task( "fixup index searchable content",
        lambda: _fixup_searchable_content( sr_type, fixup_row, make_fields )
    )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _init_qa( curs, qa, logger ):
    """Add the Q+A to the search index."""

    def make_fields( qa_entry ):
        buf = []
        for content in qa_entry.get( "content", [] ):
            buf2 = []
            buf2.append( content.get( "question", _NO_QA_QUESTION ) )
            # NOTE: We don't really want to index answers, since they are mostly not very useful (e.g. "Yes."),
            # but we do so in order to get highlighting for those cases where they contain a search term.
            for answer in content.get( "answers", [] ):
                buf2.append( answer[0] )
            buf.append( _QA_FIELD_SEPARATOR.join( buf2 ) )
        return {
            "title": qa_entry.get( "caption" ),
            "content": _QA_CONTENT_SEPERATOR.join( buf ),
        }

    def unload_fields( qa_entry, fields ):
        """Unload the Q+A entry's fields from the cached search database."""
        qa_entry["caption"] = fields["title"]
        contents = fields["content"].split( _QA_CONTENT_SEPERATOR )
        for content_no, content in enumerate( contents ):
            fields = content.split( _QA_FIELD_SEPARATOR )
            if fields[0] != _NO_QA_QUESTION:
                qa_entry["content"][content_no]["question"] = fields[0]
            for field_no in range( 1, len(fields) ):
                qa_entry["content"][content_no]["answers"][field_no-1][0] = fields[ field_no ]

    logger.info( "- Adding the Q+A." )
    nrows = 0
    sr_type = "qa"
    # IMPORTANT! The insert order must be stable (so that we can match rows in the cached database by rowid).
    for qa_key in sorted( qa.keys() ):
        qa_entries = qa[ qa_key ]
        assert isinstance( qa_entries, list )
        for qa_entry in qa_entries:
            fields = make_fields( qa_entry )
            curs.execute(
                "INSERT INTO searchable ( sr_type, title, content ) VALUES ( ?, ?, ? )", (
                sr_type, fields["title"], fields["content"]
            ) )
            _fts_index[sr_type][ curs.lastrowid ] = qa_entry
            qa_entry["_fts_rowid"] = curs.lastrowid
            nrows += 1
    logger.info( "  - Added %s.", plural(nrows,"Q+A entry","Q+A entries"),  )

    # register a task to fixup the content
    def fixup_row( rowid, cset_id ):
        qa_entry = _fts_index[ sr_type ][ rowid ]
        _tag_ruleids_in_field( qa_entry, "caption", cset_id )
        for content in qa_entry.get( "content", [] ):
            _tag_ruleids_in_field( content, "question", cset_id )
            for answer in content.get( "answers", [] ):
                _tag_ruleids_in_field( answer, 0, cset_id )
        return qa_entry
    from asl_rulebook2.webapp.startup import _add_startup_task
    _add_startup_task( "fixup Q+A searchable content",
        lambda: _fixup_searchable_content( sr_type, fixup_row, make_fields, unload_fields=unload_fields )
    )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _init_errata( curs, errata, logger ):
    """Add the errata to the search index."""
    logger.info( "- Adding the errata." )
    nrows = _do_init_anno( curs, errata, "errata" )
    logger.info( "  - Added %s.", plural(nrows,"errata entry","errata entries"),  )

def _init_user_anno( curs, user_anno, logger ):
    """Add the user-defined annotations to the search index."""
    logger.info( "- Adding the annotations." )
    nrows = _do_init_anno( curs, user_anno, "user-anno" )
    logger.info( "  - Added %s.", plural(nrows,"annotation","annotations"),  )

def _do_init_anno( curs, anno, atype ):
    """Add annotations to the search index."""

    def make_fields( anno ):
        return {
            "content": anno.get( "content" ),
        }

    # add the annotations to the search index
    # IMPORTANT! The insert order must be stable (so that we can match rows in the cached database by rowid).
    nrows = 0
    sr_type = atype
    for ruleid in sorted( anno, key=str ):
        assert isinstance( anno[ruleid], list )
        for a in anno[ruleid]:
            fields = make_fields( a )
            curs.execute(
                "INSERT INTO searchable ( sr_type, content ) VALUES ( ?, ? )", (
                sr_type, fields["content"]
            ) )
            _fts_index[sr_type][ curs.lastrowid ] = a
            a["_fts_rowid"] = curs.lastrowid
            nrows += 1

    # register a task to fixup the content
    def fixup_row( rowid, cset_id ):
        anno = _fts_index[ sr_type ][ rowid ]
        _tag_ruleids_in_field( anno, "content", cset_id )
        return anno
    from asl_rulebook2.webapp.startup import _add_startup_task
    _add_startup_task( "fixup {} searchable content".format( atype ),
        lambda: _fixup_searchable_content( sr_type, fixup_row, make_fields )
    )

    return nrows

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _init_asop( curs, asop, asop_preambles, asop_content, logger ):
    """Add the ASOP to the search index."""

    logger.info( "- Adding the ASOP." )
    sr_type = "asop-entry"
    fixup_sections = []
    nentries = 0
    # IMPORTANT! The insert order must be stable (so that we can match rows in the cached database by rowid).
    for chapter in asop.get( "chapters", [] ):
        for section in chapter.get( "sections", [] ):
            content = asop_content.get( section["section_id"] )
            if not content:
                continue
            fixup_sections.append( section )
            entries = _extract_section_entries( content )
            # NOTE: The way we manage the FTS index for ASOP entries is a little different to normal,
            # since they don't exist as individual entities (this is the only place where they do,
            # so that we can return them as individual search results). Each database row points
            # to the parent section, and the section has a list of FTS rows for its child entries.
            section[ "_fts_rowids" ] = []
            assert isinstance( entries, list )
            for entry in entries:
                curs.execute(
                    "INSERT INTO searchable ( sr_type, content ) VALUES ( ?, ? )", (
                    sr_type, entry
                ) )
                _fts_index[sr_type][ curs.lastrowid ] = [ section, entry ]
                section[ "_fts_rowids" ].append( curs.lastrowid )
            nentries += 1
    logger.info( "  - Added %s.", plural(nentries,"entry","entries") )

    # register a task to fixup the content
    def fixup_content():
        _fixup_searchable_content( sr_type, fixup_row, make_fields )
        # we also need to fixup the in-memory data structures
        if _cached_searchdb_fname is None:
            cset_id = None
            # NOTE: ASOP sections are divided up into individual entries, and each entry stored as a separate
            # searchable row, which means that we would have to reconstitute the sections from these rows
            # when they are read back from a cached database. While it's maybe possible to do this, it's safer
            # to just stored the fixed-up sections verbatim.
            with sqlite3.connect( _searchdb_fname ) as conn:
                conn.execute( "CREATE TABLE fixedup_asop_preamble ( chapter_id, content )" )
                conn.execute( "CREATE TABLE fixedup_asop_section ( section_id, content )" )
                for chapter_id in asop_preambles:
                    _tag_ruleids_in_field( asop_preambles, chapter_id, cset_id )
                    conn.execute( "INSERT INTO fixedup_asop_preamble ( chapter_id, content ) VALUES ( ?, ? )", (
                        chapter_id, asop_preambles[chapter_id]
                    ) )
                for section in fixup_sections:
                    section_id = section["section_id"]
                    _tag_ruleids_in_field( asop_content, section_id, cset_id )
                    conn.execute( "INSERT INTO fixedup_asop_section ( section_id, content ) VALUES ( ?, ? )", (
                        section_id, asop_content[section_id]
                    ) )
                conn.commit()
        else:
            # restore the fixed-up ASOP content into the in-memory objects
            with sqlite3.connect( _cached_searchdb_fname ) as conn:
                for row in conn.execute( "SELECT chapter_id, content FROM fixedup_asop_preamble" ):
                    asop_preambles[ row[0] ] = row[1]
                for row in conn.execute( "SELECT section_id, content FROM fixedup_asop_section" ):
                    asop_content[ row[0] ] = row[1]

    def fixup_row( rowid, cset_id ):
        entry = _fts_index[ sr_type ][ rowid ].pop()
        entry = tag_ruleids( entry, cset_id )
        return entry
    def make_fields( entry ):
        return { "content": entry }
    from asl_rulebook2.webapp.startup import _add_startup_task
    _add_startup_task( "fixup ASOP searchable content", fixup_content )

def _extract_section_entries( content ):
    """Separate out each entry from the section's content."""
    entries = []
    fragment = lxml.html.fragment_fromstring(
        "<div> {} </div>".format( content )
    )
    for elem in fragment.xpath( ".//div[contains(@class,'entry')]" ):
        if "entry" not in elem.attrib["class"].split():
            continue
        entry = lxml.html.tostring( elem )
        entries.append( entry.decode( "utf-8" ) )
    if not entries:
        # NOTE: If the content hasn't been divided into entries, we return the whole thing as
        # one big entry, which will kinda suck as a search result if it's big, but it's better
        # than not seeing anything at all.
        return [ content ]
    return entries

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _make_file_hashes( content_sets, qa_fnames, errata_fnames, user_anno_fname, asop_fnames ):
    """Generate hashes for the files that are used to populate the search index."""

    file_hashes = []
    def add_file( fh_type, fname ):
        with open( fname, "rb" ) as fp:
            hashval = hashlib.md5( fp.read() ).hexdigest()
        file_hashes.append( {
            "ftype": fh_type,
            "fname": os.path.basename( fname ),
            "hash": hashval
        } )

    # add each file to the table
    if content_sets:
        for cset_id, cset in content_sets.items():
            add_file( "index:{}".format(cset_id), cset["index_fname"] )
    if qa_fnames:
        for fname in qa_fnames:
            add_file( "q+a", fname )
    if errata_fnames:
        for fname in errata_fnames:
            add_file( "errata", fname )
    if user_anno_fname:
        add_file( "user-anno", user_anno_fname )
    if asop_fnames:
        for fname in asop_fnames:
            add_file( "asop", fname )

    file_hashes.sort(
        key = lambda row: ( row["ftype"], row["fname"] )
    )
    return file_hashes

def _dump_file_hashes( file_hashes, prefix="" ):
    """Dump file hashes."""
    if not file_hashes:
        return ""
    max_ftype_len = max( len(fh["ftype"]) for fh in file_hashes )
    max_fname_len = max( len(fh["fname"]) for fh in file_hashes )
    fmt = prefix + "{ftype:<%d} | {fname:<%d} | {hash}" % ( max_ftype_len, max_fname_len )
    buf = io.StringIO()
    for fh in file_hashes:
        print( fmt.format( **fh ), file=buf )
    return buf.getvalue().rstrip()

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
        if fname is None or not os.path.isfile( fname ):
            return
        logger.info( "Loading %s search replacements: %s", ftype, fname )
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
        if fname is None or not os.path.isfile( fname ):
            return
        logger.info( "Loading %s search aliases: %s", ftype, fname )
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
        if fname is None or not os.path.isfile( fname ):
            return
        logger.info( "Loading %s search synonyms: %s", ftype, fname )
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

def _fixup_searchable_content( sr_type, fixup_row, make_fields, unload_fields=None ):
    """Fixup the searchable content for the specified search result type."""

    # initialize
    conn = sqlite3.connect( _searchdb_fname )
    conn.row_factory = sqlite3.Row
    curs = conn.cursor()

    # check if we have a cached database to retrieve values from
    cached_searchdb_conn = None
    if _cached_searchdb_fname:
        cached_searchdb_conn = sqlite3.connect( _cached_searchdb_fname )
        cached_searchdb_conn.row_factory = sqlite3.Row

    # update the searchable content in each row
    nrows = 0
    last_commit_time = time.time()
    query = conn.execute( "SELECT rowid, cset_id FROM searchable WHERE sr_type=?",
        ( sr_type, )
    )
    for row in query:

        # prepare the row
        row = dict( row )
        nrows += 1

        # fixup the searchable row
        if cached_searchdb_conn:
            # find the corresponding row in the cached database
            # IMPORTANT! This relies on the 2 rows having the same rowid.
            cached_row = dict( cached_searchdb_conn.execute(
                "SELECT * FROM searchable WHERE rowid=?", (row["rowid"],)
            ).fetchone() )
            _restore_cached_searchable_row( row, sr_type, make_fields, unload_fields, cached_row, curs )
        else:
            _fixup_searchable_row( row, fixup_row, make_fields, curs )

        # commit the changes regularly (so that they are available to the front-end)
        if time.time() - last_commit_time >= 1:
            conn.commit()
            last_commit_time = time.time()

    # commit the last block of updates
    conn.commit()

    return plural( nrows, "row", "rows" )

def _fixup_searchable_row( row, fixup_row, make_fields, curs ):
    """Fix up a single row in the searchable table."""

    # NOTE: The fixup_row() callback will usually be using _tag_ruleids_in_field(), which manages
    # the lock; otherwise the callback needs to do it itself. We don't want to invoke this callback
    # inside the lock since it can be quite slow; _tag_ruleids_in_field() holds the lock for the
    # minimum amount of time.
    new_row = fixup_row( row["rowid"], row["cset_id"] )

    with _fixup_content_lock:

        # NOTE: The make_fields() callback will usually be accessing the fields we want to fixup,
        # so we need to protect them with the lock.
        fields = make_fields( new_row )

        # NOTE: We update the row inside the lock to prevent "database is locked" errors, if the user
        # tries to do a search while this is happening.
        query = "UPDATE searchable SET {} WHERE rowid={}".format(
            ", ".join( "{}=?".format( f ) for f in fields ),
            row["rowid"]
        )
        curs.execute( query, tuple(fields.values()) )

def _restore_cached_searchable_row( row, sr_type, make_fields, unload_fields, cached_row, curs ):
    """Restore a searchable row from the cached database."""

    # get the in-memory object corresponding to the next searchable row
    obj = _fts_index[ sr_type ][ row["rowid"] ]
    fields = make_fields( obj )

    # figure out which fields need to be updated
    if sr_type == "asop-entry":
        # flag that the content field in the searchable row needs to be updated
        assert list( fields.keys() ) == [ "content" ]
        update_fields = { "content": cached_row["content"] }
        # NOTE: We can't update the in-memory ASOP sections here (since the searchable rows contain
        # individual section entries that have been separated out - see _extract_section_entries()),
        # so we do this in the "fixup asop" task.
    else:
        update_fields = [
            f for f in fields
            if obj.get( f ) != cached_row[f]
        ]

    # update the fields
    if update_fields:
        # NOTE: We need to update the in-memory objects to support $/rule-info.
        if sr_type in ("errata", "qa", "user-anno"):
            if unload_fields:
                # let the caller update the in-memory object
                unload_fields( obj, { f: cached_row[f] for f in fields } )
            else:
                # update the in-memory object ourself
                for field in update_fields:
                    obj[ field ] = cached_row[ field ]
        # update the searchable row
        with _fixup_content_lock:
            query = "UPDATE searchable SET {} WHERE rowid={}".format(
                ", ".join( "{}=?".format( f ) for f in update_fields ),
                row["rowid"]
            )
            curs.execute( query, tuple(
                cached_row[f] for f in update_fields
            ) )

_last_sleep_time = 0

def _tag_ruleids_in_field( obj, key, cset_id ):
    """Tag ruleid's in an optional field."""
    if not isinstance( key, int ) and key not in obj:
        return
    # NOTE: The data structures we use to manage all the in-memory objects never change after
    # they have been loaded, so the only thread-safety we need to worry about is when we read
    # the original value from an object, and when we update it with a new value. The actual process
    # of tagging ruleid's in a piece of content is done outside the lock, since it's quite slow.
    with _fixup_content_lock:
        val = obj[key]
    new_val = tag_ruleids( val, cset_id )
    with _fixup_content_lock:
        obj[key] = new_val
    # FUDGE! Give other threads a chance to run :-/
    global _last_sleep_time
    if time.time() - _last_sleep_time > 1:
        time.sleep( 0.1 )
        _last_sleep_time = time.time()

def _get_row_count( conn, table_name ):
    """Get the number of rows in a table."""
    cur = conn.execute( "SELECT count(*) FROM {}".format( table_name ) )
    return cur.fetchone()[0]
