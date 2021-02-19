""" Test dumping PDF's. """

import os
import io
import re

from pdfminer.layout import LTTextLineHorizontal

from asl_rulebook2.pdf import PdfDoc

# ---------------------------------------------------------------------

def test_dump():
    """Test dumping PDF's."""

    # dump the PDF
    fname = os.path.join( os.path.dirname(__file__), "fixtures/dump/simple-text.pdf" )
    buf = io.StringIO()
    with PdfDoc( fname ) as pdf:
        pdf.dump_pdf( out=buf,
            elem_filter = lambda e: isinstance( e, LTTextLineHorizontal )
        )
    buf = buf.getvalue()

    # check that no TOC was found
    mo = re.search( r"^No TOC\.$", buf, re.MULTILINE )
    assert mo

    # extract the results
    pages = {}
    curr_page = None
    for line in buf.split( "\n" ):
        # check if we've found the start of a new page
        mo = re.search( r"^--- PAGE (\d+) ---", line, re.MULTILINE )
        if mo:
            if curr_page:
                pages[ curr_page_no ] = curr_page
            curr_page = []
            curr_page_no = int( mo.group(1) )
            continue
        # check if we've found content we're interested in
        mo = re.search( r"<LTTextLineHorizontal .*?'(.*?)'>", line )
        if mo:
            content = mo.group(1).replace( "\\n", "" ).strip()
            if content:
                curr_page.append( content )
    pages[ curr_page_no ] = curr_page
    assert pages == {
        1: [ "This is page 1." ],
        2: [ "This is page 2.", "Another line on page 2." ],
        3: [
            "Line 1a.", "Line 1b.", "Line 1c.", "Line 1d.", "Line 1e.",
            "Line 2a.", "Line 2b.", "Line 2c."
        ]
    }
