#!/usr/bin/env python3
""" Add named destinations to a PDF file. """

import subprocess
import json
import time
import datetime

import click

from asl_rulebook2.utils import TempFile

# NOTE: "screen" gives significant savings (~65%) but scanned PDF's become very blurry. The main MMP eASLRB
# is not too bad, but some images are also a bit unclear. "ebook" gives no savings for scanned PDF's, but
# the main MMP eASLRB is quite usable, and only slightly larger (43 MB vs. 35 MB), so we use that.
_COMPRESSION_CHOICES = [
    "screen", # 72 dpi
    "ebook", # 150 dpi
    "printer", # 300 dpi
    "prepress", # 300 dpi, color preserving
    "none"
]

# ---------------------------------------------------------------------

@click.command()
@click.argument( "pdf_file", nargs=1, type=click.Path(exists=True,dir_okay=False) )
@click.option( "--title", help="Document title." )
@click.option( "--targets","-t","targets_fname", required=True, type=click.Path(dir_okay=False),
    help="Target definition file."
)
@click.option( "--yoffset", default=5, help="Offset to add to y co-ordinates." )
@click.option( "--output","-o","output_fname", required=True, type=click.Path(dir_okay=False),
    help="Output PDF file."
)
@click.option( "--compression", type=click.Choice(_COMPRESSION_CHOICES), default="ebook",
    help="Level of compression."
)
@click.option( "--gs","gs_path", default="gs",  help="Path to the Ghostscript executable." )
def main( pdf_file, title, targets_fname, yoffset, output_fname, compression, gs_path ):
    """Add named destinations to a PDF file."""

    # load the targets
    with open( targets_fname, "r" ) as fp:
        targets = json.load( fp )

    with TempFile(mode="w") as compressed_file, TempFile(mode="w") as pdfmarks_file:

        # compress the PDF
        if compression and compression != "none":
            print( "Compressing the PDF ({})...".format( compression ) )
            compressed_file.close( delete=False )
            args = [ gs_path, "-sDEVICE=pdfwrite", "-dNOPAUSE", "-dQUIET", "-dBATCH",
                "-dPDFSETTINGS=/{}".format( compression ),
                "-sOutputFile={}".format( compressed_file.name ),
                pdf_file
            ]
            start_time = time.time()
            subprocess.run( args, check=True )
            elapsed_time = time.time() - start_time
            print( "- Elapsed time: {}".format( datetime.timedelta(seconds=int(elapsed_time)) ) )
            pdf_file = compressed_file.name

        # generate the pdfmarks
        print( "Generating the pdfmarks..." )
        if title:
            print( "[ /Title ({})".format( title ), file=pdfmarks_file )
        else:
            print( "[", file=pdfmarks_file )
        print( "  /DOCINFO pdfmark", file=pdfmarks_file )
        print( file=pdfmarks_file )
        for ruleid, target in targets.items():
            xpos, ypos = target.get( "pos", ["null","null"] )
            if isinstance( ypos, int ):
                ypos += yoffset
            if " " in ruleid:
                # NOTE: We are supposed to be able to quote things using parentheses (e.g. "(foo bar)"
                # but it doesn't seem to work here :-(
                raise RuntimeError( "PDF destinations cannot have spaces." )
            print( "[ /Dest /{} /Page {} /View [/XYZ {} {}] /DEST pdfmark".format(
                ruleid, target["page_no"], xpos, ypos
            ), file=pdfmarks_file )
        print( file=pdfmarks_file )
        pdfmarks_file.close( delete=False )

        # generate the pdfmark'ed document
        print( "Generating the pdfmark'ed document..." )
        print( "- {} => {}".format( pdf_file, output_fname ) )
        args = [ gs_path, "-q", "-dBATCH", "-dNOPAUSE", "-sDEVICE=pdfwrite" ]
        args.extend( [ "-o", output_fname ] )
        args.extend( [ "-f", pdf_file ] )
        args.append( pdfmarks_file.name )
        start_time = time.time()
        subprocess.run( args, check=True )
        elapsed_time = time.time() - start_time
        print( "- Elapsed time: {}".format( datetime.timedelta(seconds=int(elapsed_time)) ) )

# ---------------------------------------------------------------------

if __name__ == "__main__":
    main() #pylint: disable=no-value-for-parameter
