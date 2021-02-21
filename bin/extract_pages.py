#!/usr/bin/env python3
""" Extract pages from a PDF. """

import click
from pikepdf import Pdf, Page, OutlineItem, Encryption, make_page_destination

from asl_rulebook2.pdf import PdfDoc
from asl_rulebook2.utils import parse_page_numbers

# ---------------------------------------------------------------------

@click.command()
@click.argument( "pdf_file", nargs=1, type=click.Path(exists=True,dir_okay=False) )
@click.option( "--output","-o","output_fname", required=True, type=click.Path(dir_okay=False), help="Output PDF file" )
@click.option( "--pages","-p", help="Page(s) to dump (e.g. 2,5,9-15)." )
def main( pdf_file, output_fname, pages ):
    """Extract pages from a PDF."""

    # NOTE: This extracts pages from the eASLRB, so we can work on specific parts of it without having to load
    # the entire document each time. In particular, it maintains the internal PDF strucuture of each page.
    # The files as small as you might expect (e.g. extracting a single page results in a file only about half
    # the size), but processing them are significantly faster.

    # process the command-line arguments
    pages = parse_page_numbers( pages, offset=-1 )

    print( "Loading PDF:", pdf_file )
    with Pdf.open( pdf_file ) as pdf:

        # delete the TOC
        print( "Removing the TOC..." )
        with pdf.open_outline() as outline:
            while outline.root:
                del outline.root[-1]

        # extract the specified pages
        print( "Extracting pages:", ", ".join( str(p) for p in sorted(pages) ) )
        for page_no in range( len(pdf.pages)-1, -1, -1 ):
            if page_no not in pages:
                del pdf.pages[ page_no ]

        # save the new PDF
        print( "Saving file:", output_fname )
        pdf.save( output_fname )

# ---------------------------------------------------------------------

if __name__ == "__main__":
    main() #pylint: disable=no-value-for-parameter
