#!/usr/bin/env python3
""" Fixup issues in the MMP eASLRB. """

import os

from pikepdf import Pdf, Page, OutlineItem, Encryption, make_page_destination
import click

from asl_rulebook2.utils import log_msg_stderr

# ---------------------------------------------------------------------

def fixup_mmp_pdf( fname, output_fname, optimize_web, rotate, log=None ):
    """Fixup the MMP eASLRB PDF."""

    def log_msg( msg_type, msg, *args, **kwargs ):
        if not log:
            return
        if isinstance( msg, list ):
            msg = "\n".join( msg )
        msg = msg.format( *args, **kwargs )
        log( msg_type, msg )

    # NOTE: It would be nice to use the targets file to get the TOC entries and annotations
    # to point to the exact point on the page, but figuring out the text associated with each
    # annotiation is extremely messy (annotations are simply a rectangle on a page, so we need
    # to figure out which elements lie within that rectangle, and since things are not always
    # lined up nicely, this is an unreliable process).

    with Pdf.open( fname ) as pdf:

        log_msg( "start", "Loaded PDF: {}\n- PDF version = {}\n- #pages = {}".format(
            fname, pdf.pdf_version, len(pdf.pages) )
        )
        log_msg( None, "" )

        # fixup bookmarks in the TOC
        log_msg( "progress", "Fixing up the TOC..." )
        def walk_toc( items, depth ):
            for item_no,item in enumerate(items):
                if item.destination[0].Type != "/Page" or item.destination[1] != "/Fit" \
                   or item.page_location is not None or item.page_location_kwargs != {}:
                    log_msg( "warning", "Unexpected TOC item: {}/{}".format( depth, item_no ) )
                    continue
                page = Page( item.destination[0] )
                page_height = page.mediabox[3]
                bullet = "#" if depth <= 1 else "-"
                log_msg( "verbose", "  {}{} {} => p{}",
                    depth*"  ", bullet, item.title, 1+page.index
                )
                walk_toc( item.children, depth+1 )
                new_item = OutlineItem( item.title, page.index, "XYZ", top=page_height )
                new_item.children = item.children
                new_item.is_closed = True
                items[ item_no ] = new_item
        with pdf.open_outline() as outline:
            walk_toc( outline.root, 0 )
            # NOTE: The TOC will be updated when we exit the context manager, and can take some time.
            log_msg( "progress", "Installing the new TOC..." )
        log_msg( None, "" )

        # fixup up each page
        log_msg( "progress", "Fixing up the content..." )
        for page_no, raw_page in enumerate(pdf.pages):
            log_msg( "verbose", "- page {}", 1+page_no )
            if rotate:
                # force pages to be landscape (so that we don't get an h-scrollbar in Firefox
                # when we set the zoom to "fit width").
                if raw_page.get("Rotate",0) == 0 and raw_page.MediaBox[2] > raw_page.MediaBox[3]:
                    raw_page.Rotate = 270
                else:
                    raw_page.Rotate = 0
            page = Page( raw_page )
            page_height = page.mediabox[3]
            for annot in raw_page.get( "/Annots", [] ):
                dest = annot.get( "/Dest" )
                if dest:
                    page_no = Page( dest[0] ).index
                    log_msg( "verbose", "  - {} => p{}",
                        repr(annot.Rect), 1+page_no
                    )
                    annot.Dest = make_page_destination( pdf, page_no, "XYZ", top=page_height )
        log_msg( None, "" )

        # save the updated PDF
        log_msg( "progress", "Saving the fixed-up PDF..." )
        # NOTE: Setting a blank password will encrypt the file, but doesn't require the user to enter a password
        # when opening the file (but it will be marked as "SECURE" in the UI).
        enc = Encryption( owner="", user="" )
        def save_progress( pct ):
            if pct > 0 and pct % 10 == 0:
                log_msg( "verbose", "- Saved {}%.", pct )
        pdf.save( output_fname, encryption=enc, linearize=optimize_web,
            progress = save_progress
        )

        # compare the file sizes
        old_size = os.path.getsize( fname )
        new_size = os.path.getsize( output_fname )
        ratio = round( 100 * float(new_size) / float(old_size) ) - 100
        if ratio == 0:
            log_msg( "verbose", "The updated PDF file is about the same size as the original file." )
        else:
            log_msg( "verbose", "The updated PDF file is about {}% {} than the original file.",
                abs(ratio), "larger" if ratio > 0 else "smaller"
            )

# ---------------------------------------------------------------------

@click.command()
@click.argument( "pdf_file", nargs=1, type=click.Path(exists=True,dir_okay=False) )
@click.option( "--output","-o", required=True, type=click.Path(dir_okay=False), help="Where to save the fixed-up PDF." )
@click.option( "--optimize-web", is_flag=True, default=False, help="Optimize for use in a browser (larger file)." )
@click.option( "--rotate", is_flag=True, default=False, help="Rotate landscape pages." )
@click.option( "--progress","-p", is_flag=True, default=False, help="Log progress." )
@click.option( "--verbose","-v", is_flag=True, default=False, help="Verbose output." )
def main( pdf_file, output, optimize_web, rotate, progress, verbose ):
    """Fixup the eASLRB."""

    def log_msg( msg_type, msg ):
        if msg_type in ("progress", "start", None) and not progress:
            return
        if msg_type == "verbose" and not verbose:
            return
        log_msg_stderr( msg_type, msg )
    fixup_mmp_pdf( pdf_file, output, optimize_web, rotate, log=log_msg )

if __name__ == "__main__":
    main() #pylint: disable=no-value-for-parameter
