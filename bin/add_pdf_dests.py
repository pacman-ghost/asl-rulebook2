#!/usr/bin/env python3
""" Add named destinations to a PDF file. """

import subprocess
import json
import time
import datetime

import click

from asl_rulebook2.utils import TempFile

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
@click.option( "--gs","gs_path", default="gs",  help="Path to the Ghostscript executable." )
def main( pdf_file, title, targets_fname, yoffset, output_fname, gs_path ):
    """Add named destinations to a PDF file."""

    # load the targets
    with open( targets_fname, "r" ) as fp:
        targets = json.load( fp )

    with TempFile( mode="w" ) as temp_file:

        # generate the pdfmarks
        print( "Generating the pdfmarks..." )
        if title:
            print( "[ /Title ({})".format( title ), file=temp_file )
        else:
            print( "[", file=temp_file )
        print( "  /DOCINFO pdfmark", file=temp_file )
        print( file=temp_file )
        for ruleid, target in targets.items():
            xpos, ypos = target["pos"]
            print( "[ /Dest /{} /Page {} /View [/XYZ {} {}] /DEST pdfmark".format(
                ruleid, target["page_no"], xpos, ypos+yoffset
            ), file=temp_file )
        print( file=temp_file )
        temp_file.close( delete=False )

        # generate the pdfmark'ed document
        print( "Generating the pdfmark'ed document..." )
        print( "- {} => {}".format( pdf_file, output_fname ) )
        args = [ gs_path, "-q", "-dBATCH", "-dNOPAUSE", "-sDEVICE=pdfwrite" ]
        args.extend( [ "-o", output_fname ] )
        args.extend( [ "-f", pdf_file ] )
        args.append( temp_file.name )
        start_time = time.time()
        subprocess.run( args, check=True )
        elapsed_time = time.time() - start_time
        print( "- Elapsed time: {}".format( datetime.timedelta(seconds=int(elapsed_time)) ) )

# ---------------------------------------------------------------------

if __name__ == "__main__":
    main() #pylint: disable=no-value-for-parameter
