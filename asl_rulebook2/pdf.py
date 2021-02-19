""" Parse and process a PDF. """

import collections

import click
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfdocument import PDFDocument, PDFNoOutlines
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.converter import PDFPageAggregator
from pdfminer.layout import LAParams, LTContainer
from pdfminer.pdfpage import PDFPage

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

    def dump_pdf( self, dump_toc=True, pages=None, elem_filter=None, out=None ):
        """Dump the PDF document."""

        # dump the TOC
        if dump_toc:
            self._dump_toc( out=out )

        # dump each page
        max_page_no = max( pages ) if pages else None
        first_page = not dump_toc
        for page_no, page in PageIterator( self ):

            # parse the next page
            self.interp.process_page( page )
            if pages and page_no not in pages:
                continue
            lt_page = self.device.get_result()

            # dump the page details
            if first_page:
                first_page = False
            else:
                click.echo( file=out )
            click.secho( "--- PAGE {} {}".format( page_no, 80*"-" )[:80], fg="bright_cyan", file=out )
            click.echo( "lt_page = {}".format( lt_page ), file=out )
            click.echo( file=out )

            # dump each element on the page
            for depth, elem in PageElemIterator( lt_page ):
                if elem_filter and not elem_filter( elem ):
                    continue
                click.echo( "{}- {}".format( depth*"  ", elem ), file=out )

            # check if we're done
            if max_page_no and page_no >= max_page_no:
                break

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
            title = repr( title ).strip()
            if title[0] in ('"',"'") and title[-1] == title[0]:
                title = title[1:-1]
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
        self._page_no = 0

    def __iter__( self ):
        return self

    def __next__( self ):
        """Return the next page."""
        page = next( self._pages )
        self._page_no += 1
        return self._page_no, page

# ---------------------------------------------------------------------

class PageElemIterator:
    """Iterate over each element in a page."""

    def __init__( self, lt_page ):
        self.lt_page = lt_page
        # collect all the elements (so that they can be sorted)
        self._elems = collections.deque()
        def walk( elem, depth ):
            for child in elem:
                self._elems.append( ( depth, child ) )
                if isinstance( child, LTContainer ):
                    walk( child, depth+1 )
        walk( lt_page, 0 )

    def __iter__( self ):
        return self

    def __next__( self ):
        """Return the next element on the page."""
        if not self._elems:
            raise StopIteration()
        return self._elems.popleft()

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
