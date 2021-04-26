""" Test eASLRB extraction. """

import os
import io

import pytest

from asl_rulebook2.pdf import PdfDoc
from asl_rulebook2.extract.index import ExtractIndex
from asl_rulebook2.extract.content import ExtractContent
from asl_rulebook2.extract.all import ExtractAll
from asl_rulebook2.tests import pytest_options
from asl_rulebook2.tests.utils import for_each_easlrb_version

# ---------------------------------------------------------------------

@pytest.mark.skipif( not pytest_options.easlrb_path, reason="eASLRB not available." )
@pytest.mark.skipif( pytest_options.short_tests, reason="--short-tests specified." )
def test_extract_index():
    """Test extracting the index."""

    def do_test( dname ):

        # extract the index
        fname = os.path.join( dname, "eASLRB.pdf" )
        with PdfDoc( fname ) as pdf:
            extract = ExtractIndex( args={}, log=_check_log_msg )
            extract.extract_index( pdf )
        buf = io.StringIO()
        extract.save_as_text( buf )
        buf = buf.getvalue()

        # check the results
        fname = os.path.join( dname, "index.txt" )
        assert open( fname, "r", encoding="utf-8" ).read() == buf

    # run the test
    for_each_easlrb_version( do_test )

# ---------------------------------------------------------------------

@pytest.mark.skipif( not pytest_options.easlrb_path, reason="eASLRB not available." )
@pytest.mark.skipif( pytest_options.short_tests, reason="--short-tests specified." )
def test_extract_content():
    """Test extracting content."""

    def do_test( dname ):

        # extract the content
        fname = os.path.join( dname, "eASLRB.pdf" )
        with PdfDoc( fname ) as pdf:
            extract = ExtractContent( args={}, log=_check_log_msg )
            extract.extract_content( pdf )
        targets_buf, chapters_buf, footnotes_buf = io.StringIO(), io.StringIO(), io.StringIO()
        extract.save_as_text( targets_buf, chapters_buf, footnotes_buf )
        targets_buf = targets_buf.getvalue()
        chapters_buf = chapters_buf.getvalue()
        footnotes_buf = footnotes_buf.getvalue()

        # check the results
        fname2 = os.path.join( dname, "targets.txt" )
        assert open( fname2, "r", encoding="utf-8" ).read() == targets_buf
        fname2 = os.path.join( dname, "chapters.txt" )
        assert open( fname2, "r", encoding="utf-8" ).read() == chapters_buf
        fname2 = os.path.join( dname, "footnotes.txt" )
        assert open( fname2, "r", encoding="utf-8" ).read() == footnotes_buf

    # run the test
    for_each_easlrb_version( do_test )

# ---------------------------------------------------------------------

@pytest.mark.skipif( not pytest_options.easlrb_path, reason="eASLRB not available." )
@pytest.mark.skipif( pytest_options.short_tests, reason="--short-tests specified." )
def test_extract_all():
    """Test extracting everything."""

    def do_test( dname ):

        # extract everything
        fname = os.path.join( dname, "eASLRB.pdf" )
        with PdfDoc( fname ) as pdf:
            extract = ExtractAll( args={}, log=_check_log_msg )
            extract.extract_all( pdf )
        index_buf = io.StringIO()
        extract.extract_index.save_as_json( index_buf )
        index_buf = index_buf.getvalue()
        targets_buf, chapters_buf, footnotes_buf = io.StringIO(), io.StringIO(), io.StringIO()
        extract.extract_content.save_as_json( targets_buf, chapters_buf, footnotes_buf )
        targets_buf = targets_buf.getvalue()
        chapters_buf = chapters_buf.getvalue()
        footnotes_buf = footnotes_buf.getvalue()

        # check the results
        fname2 = os.path.join( dname, "index.json" )
        assert open( fname2, "r", encoding="utf-8" ).read() == index_buf
        fname2 = os.path.join( dname, "targets.json" )
        assert open( fname2, "r", encoding="utf-8" ).read() == targets_buf
        fname2 = os.path.join( dname, "chapters.json" )
        assert open( fname2, "r", encoding="utf-8" ).read() == chapters_buf
        fname2 = os.path.join( dname, "footnotes.json" )
        assert open( fname2, "r", encoding="utf-8" ).read() == footnotes_buf

    # run the test
    for_each_easlrb_version( do_test )

# ---------------------------------------------------------------------

def _check_log_msg( msg_type, msg ):
    """Check a log message."""
    assert msg_type not in ( "warning", "error" ), \
        "Unexpected {}: {}".format( msg_type, msg )
