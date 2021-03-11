""" Parse and process a PDF. """

import click
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument, PDFNoOutlines
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTContainer
from pdfminer.pdfpage import PDFPage

from asl_rulebook2.utils import remove_quotes, roundf

# ---------------------------------------------------------------------

class PdfDoc:
    """Wrapper around a PDF document."""

    def __init__( self, fname ):
        self.fname = fname
        self._fp = None

    def __enter__( self ):
        self._fp = open( self.fname, "rb" )
        #pylint: disable=attribute-defined-outside-init
        self.parser = PDFParser( self._fp )
        self.doc = PDFDocument( self.parser )
        self.rmgr = PDFResourceManager()
        self.device = PDFPageAggregator( self.rmgr, laparams=LAParams() )
        self.interp = PDFPageInterpreter( self.rmgr, self.device )
        return self

    def __exit__( self, exc_type, exc_value, exc_traceback ):
        if self._fp:
            self._fp.close()

    def dump_pdf( self, dump_toc=True, page_nos=None, sort_elems=False, elem_filter=None, out=None ):
        """Dump the PDF document."""

        # dump the TOC
        if dump_toc:
            self._dump_toc( out=out )

        # dump each page
        first_page = not dump_toc
        for page_no, page, lt_page in PageIterator( self ): #pylint: disable=unused-variable

            if page_nos:
                if page_no > max( page_nos ):
                    break
                if page_no not in page_nos:
                    continue

            # dump the page details
            if first_page:
                first_page = False
            else:
                click.echo( file=out )
            click.secho( "--- PAGE {} {}".format( page_no, 80*"-" )[:80], fg="bright_cyan", file=out )
            click.echo( "lt_page = {}".format( lt_page ), file=out )
            click.echo( file=out )

            # dump each element on the page
            for depth, elem in PageElemIterator( lt_page, elem_filter=elem_filter, sort_elems=sort_elems ):
                click.echo( "{}- {}".format( depth*"  ", elem ), file=out )

    def _dump_toc( self, out=None ):
        """Dump a PDF document's TOC."""

        # initialize
        toc_iter = TocIterator( self )
        if not toc_iter.has_toc():
            click.secho( "No TOC.", fg="red", file=out )
            return

        # dump each TOC entry
        for depth, title, dest in toc_iter:
            if depth > 1:
                bullet = "*" if depth == 2 else "-"
                click.echo( "{}{} ".format( (depth-2)*"  ", bullet ), nl=False, file=out )
            title = remove_quotes( repr( title ).strip() )
            col = "cyan" if depth <= 2 else "green"
            click.echo( "{} => {}".format(
                click.style( title, fg=col ),
                click.style( repr(dest), fg="yellow" )
            ), file=out )

# ---------------------------------------------------------------------

class PageIterator:
    """Iterate over each page in a PDF document."""

    def __init__( self, pdf ):
        self.pdf = pdf
        self._pages = PDFPage.create_pages( pdf.doc )
        self._curr_page_no = 0

    def __iter__( self ):
        return self

    def __next__( self ):
        """Return the next page."""
        while True:
            self._curr_page_no += 1
            page = next( self._pages )
            self.pdf.interp.process_page( page )
            lt_page = self.pdf.device.get_result()
            return self._curr_page_no, page, lt_page

# ---------------------------------------------------------------------

class PageElemIterator:
    """Iterate over each element in a page."""

    def __init__( self, lt_page, elem_filter=None, sort_elems=False ):
        self.lt_page = lt_page
        # collect all the elements (so that they can be sorted)
        self._elems = []
        self._curr_elem_no = -1
        def walk( elem, depth ):
            for child in elem:
                # NOTE: If elements are to be sorted, we ignore anything that is not laid out.
                if not sort_elems or hasattr( child, "x0" ):
                    if not elem_filter or elem_filter( child ):
                        self._elems.append( ( depth, child ) )
                if isinstance( child, LTContainer ):
                    walk( child, depth+1 )
        walk( lt_page, 0 )
        if sort_elems:
            def sort_key( elem ):
                col_no = 0 if elem[1].x0 < lt_page.width/2 else 1
                # NOTE: Some elements that should be aligned are actually misaligned by a miniscule amount (e.g. 10^-5),
                # so to stop this from resulting in the wrong sort order, we truncate the decimal places.
                # NOTE: Characters are often rendered in different fonts, with bounding boxes that don't align neatly.
                # I tried sorting by the centre of the bounding boxes, but superscripts causes problems :-/
                ypos = - roundf( elem[1].y1, 1 )
                xpos = roundf( elem[1].x0, 1 )
                return col_no, ypos, xpos
            self._elems.sort( key=sort_key )

    def __iter__( self ):
        return self

    def __next__( self ):
        """Return the next element on the page."""
        self._curr_elem_no  += 1
        if self._curr_elem_no >= len(self._elems):
            raise StopIteration()
        return self._elems[ self._curr_elem_no ]

# ---------------------------------------------------------------------

class TocIterator():
    """Iterate over the entries in a TOC."""

    def __init__( self, pdf ):
        try:
            self._outlines = pdf.doc.get_outlines()
        except PDFNoOutlines:
            self._outlines = None

    def has_toc( self ):
        """Check if the document has as TOC."""
        return self._outlines is not None

    def __iter__( self ):
        return self

    def __next__( self ):
        """Return the next entry in the TOC."""
        level, title, dest, action, se = next( self._outlines ) #pylint: disable=unused-variable,invalid-name
        return level, title, dest
