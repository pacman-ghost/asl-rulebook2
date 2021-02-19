#!/usr/bin/env python3
""" Dump a PDF file. """

import click

from asl_rulebook2.pdf import PdfDoc
from asl_rulebook2.utils import parse_page_numbers

# ---------------------------------------------------------------------

@click.command()
@click.argument( "pdf_file", nargs=1, type=click.Path(exists=True,dir_okay=False) )
@click.option( "--toc","dump_toc", is_flag=True, default=False, help="Dump the TOC." )
@click.option( "--pages","-p", help="Page(s) to dump (e.g. 2,5,9-15)." )
def main( pdf_file, dump_toc, pages ):
    """Dump a PDF file."""

    # process the command-line arguments
    pages = parse_page_numbers( pages )

    # dump the PDF file
    with PdfDoc( pdf_file ) as pdf:
        pdf.dump_pdf( dump_toc=dump_toc, pages=pages )

# ---------------------------------------------------------------------

if __name__ == "__main__":
    main() #pylint: disable=no-value-for-parameter
