#!/usr/bin/env python3
""" Prepare the MMP eASLRB PDF. """

import subprocess
import json
import time
import datetime

import click

from asl_rulebook2.utils import TempFile, log_msg_stderr

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

def prepare_pdf( pdf_file,
    title, targets_fname, vo_notes_fname, yoffset,
    output_fname, compression,
    gs_path,
    log_msg, relinq=None
):
    """Prepare the MMP eASLRB PDF."""

    # load the targets
    with open( targets_fname, "r" ) as fp:
        targets = json.load( fp )
    if vo_notes_fname:
        with open( vo_notes_fname, "r" ) as fp:
            vo_notes_targets = json.load( fp )
    else:
        vo_notes_targets = None

    with TempFile(mode="w") as compressed_file, TempFile(mode="w") as pdfmarks_file:

        # compress the PDF
        if compression and compression != "none":
            log_msg( "progress", "Compressing the PDF ({})...".format( compression ) )
            compressed_file.close( delete=False )
            args = [ gs_path, "-sDEVICE=pdfwrite", "-dNOPAUSE", "-dQUIET", "-dBATCH",
                "-dPDFSETTINGS=/{}".format( compression ),
                "-sOutputFile={}".format( compressed_file.name ),
                pdf_file
            ]
            start_time = time.time()
            _run_subprocess( args, "compression", relinq )
            elapsed_time = time.time() - start_time
            log_msg( "timestamp", "- Elapsed time: {}".format(
                datetime.timedelta( seconds=int(elapsed_time) ) )
            )
            pdf_file = compressed_file.name

        def add_vo_notes_dests( key, vo_entries, yoffset, out ):
            for vo_note_id, vo_entry in vo_entries.items():
                dest = "{}:{}".format( key, vo_note_id )
                xpos, ypos = vo_entry.get( "pos", ["null","null"] )
                if isinstance( ypos, int ):
                    ypos += yoffset
                print( "[ /Dest /{} /Page {} /View [/XYZ {} {}] /DEST pdfmark".format(
                    dest, vo_entry["page_no"], xpos, ypos
                ), file=out )

        # generate the pdfmarks
        log_msg( "progress", "Generating the pdfmarks..." )
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
        if vo_notes_targets:
            print( file=pdfmarks_file )
            for nat in vo_notes_targets:
                if nat == "landing-craft":
                    add_vo_notes_dests( nat, vo_notes_targets[nat], yoffset, pdfmarks_file )
                    continue
                for vo_type, vo_entries in vo_notes_targets[nat].items():
                    key = "{}_{}".format( nat, vo_type )
                    add_vo_notes_dests( key, vo_entries, yoffset, pdfmarks_file )
        pdfmarks_file.close( delete=False )

        # generate the pdfmark'ed document
        log_msg( "progress", "Adding targets to the PDF..." )
        args = [ gs_path, "-q", "-dBATCH", "-dNOPAUSE", "-sDEVICE=pdfwrite" ]
        args.extend( [ "-o", output_fname ] )
        args.extend( [ "-f", pdf_file ] )
        args.append( pdfmarks_file.name )
        start_time = time.time()
        _run_subprocess( args, "pdfmarks", relinq )
        elapsed_time = time.time() - start_time
        log_msg( "timestamp", "- Elapsed time: {}".format(
            datetime.timedelta( seconds=int(elapsed_time) ) )
        )

# ---------------------------------------------------------------------

def _run_subprocess( args, caption, relinq ):
    """Run an external process."""
    proc = subprocess.Popen( args )
    try:
        pass_no = 0
        while True:
            pass_no += 1
            # check if the external process has finished
            rc = proc.poll()
            if rc is not None:
                # yup - check its exit code
                if rc != 0:
                    raise RuntimeError( "Sub-process \"{}\" failed: rc={}".format( caption, rc ) )
                break
            # delay for a bit before checking again
            if relinq:
                relinq( "Waiting for {}: {}".format( caption, pass_no ), delay=1 )
            else:
                time.sleep( 1 )
    except ( Exception, KeyboardInterrupt ):
        # NOTE: We want to kill the child process if something goes wrong, and while it's not
        # 100%-guaranteed that we will get here (e.g. if we get killed), it's good enuf.
        proc.terminate()
        raise

# ---------------------------------------------------------------------

@click.command()
@click.argument( "pdf_file", nargs=1, type=click.Path(exists=True,dir_okay=False) )
@click.option( "--title", help="Document title." )
@click.option( "--targets","-t","targets_fname", required=True, type=click.Path(dir_okay=False),
    help="Target definition file."
)
@click.option( "--vo-notes","vo_notes_fname", required=False, type=click.Path(dir_okay=False),
    help="Vehicle/ordnance notes definition file."
)
@click.option( "--yoffset", default=5, help="Offset to add to y co-ordinates." )
@click.option( "--output","-o","output_fname", required=True, type=click.Path(dir_okay=False),
    help="Output PDF file."
)
@click.option( "--compression", type=click.Choice(_COMPRESSION_CHOICES), default="ebook",
    help="Level of compression."
)
@click.option( "--gs","gs_path", default="gs",  help="Path to the Ghostscript executable." )
@click.option( "--progress","-p", is_flag=True, default=False, help="Log progress." )
def main( pdf_file, title, targets_fname, vo_notes_fname, yoffset, output_fname, compression, gs_path, progress ):
    """Prepare the MMP eASLRB PDF."""

    # initialize
    def log_msg( msg_type, msg ):
        if msg_type in ("progress", "start", "timestamp", None) and not progress:
            return
        log_msg_stderr( msg_type, msg )

    # prepare the PDF
    prepare_pdf(
        pdf_file, title,
        targets_fname, vo_notes_fname, yoffset,
        output_fname, compression,
        gs_path,
        log_msg
    )

if __name__ == "__main__":
    main() #pylint: disable=no-value-for-parameter
