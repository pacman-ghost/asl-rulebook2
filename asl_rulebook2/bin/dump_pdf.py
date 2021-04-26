#!/usr/bin/env python3
""" Dump a PDF file. """

import click

from asl_rulebook2.pdf import PdfDoc
from asl_rulebook2.utils import parse_page_numbers

# ---------------------------------------------------------------------

@click.command()
@click.argument( "pdf_file", nargs=1, type=click.Path(exists=True,dir_okay=False) )
@click.option( "--toc","dump_toc", is_flag=True, default=False, help="Dump the TOC." )
@click.option( "--pages","-p","page_nos", help="Page(s) to dump (e.g. 2,5,9-15)." )
@click.option( "--sort","-s","sort_elems", is_flag=True, default=False, help="Sort elements within each page." )
def main( pdf_file, dump_toc, page_nos, sort_elems ):
    """Dump a PDF file."""

    # dump the PDF file
    page_nos = parse_page_numbers( page_nos )
    with PdfDoc( pdf_file ) as pdf:
        pdf.dump_pdf( dump_toc=dump_toc, page_nos=page_nos, sort_elems=sort_elems )

# ---------------------------------------------------------------------

if __name__ == "__main__":
    main() #pylint: disable=no-value-for-parameter
