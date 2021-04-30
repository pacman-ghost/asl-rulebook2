""" Analyze the MMP eASLRB PDF and prepare the data files. """

import threading
import zipfile
import io
import time
import base64
import traceback
import logging

from flask import request, send_file, abort, url_for

from asl_rulebook2.extract.all import ExtractAll
from asl_rulebook2.bin.prepare_pdf import prepare_pdf
from asl_rulebook2.bin.fixup_mmp_pdf import fixup_mmp_pdf
from asl_rulebook2.pdf import PdfDoc
from asl_rulebook2.utils import TempFile
from asl_rulebook2.webapp import app, globvars
from asl_rulebook2.webapp.utils import get_gs_path

_zip_data_download = None

_logger = logging.getLogger( "prepare" )

# ---------------------------------------------------------------------

@app.route( "/prepare", methods=["POST"] )
def prepare_data_files():
    """Prepare the data files."""

    # initialize
    args = dict( request.json )
    download_url = url_for( "download_prepared_data" )

    # initialize the socketio server
    sio = globvars.socketio_server
    if not sio:
        raise RuntimeError( "The socketio server has not been started." )
    @sio.on( "start" )
    def on_start( data ): #pylint: disable=unused-variable,unused-argument
        # start the worker thread that prepares the data files
        # NOTE: We don't do this when the POST request comes in, but wait until the client
        # tells us it's ready (otherwise, it might miss the first event or two).
        def worker():
            try:
                _do_prepare_data_files( args, download_url )
            except Exception as ex: #pylint: disable=broad-except
                _logger.error( "PREPARE ERROR: %s\n%s", ex, traceback.format_exc() )
                globvars.socketio_server.emit( "error", str(ex) )
        threading.Thread( target=worker, daemon=True ).start()

    return "ok"

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _do_prepare_data_files( args, download_url ):

    # initialize
    sio = globvars.socketio_server
    pdf_data = args.get( "pdfData" )
    if not pdf_data:
        # no data was sent - this is a test of logging progress messages.
        del args["pdfData"]
        _test_progress( **args )
        return
    pdf_data = base64.b64decode( pdf_data )

    def on_done( zip_data ):
        global _zip_data_download
        _zip_data_download = zip_data
        sio.emit( "done", download_url )

    # check if we should just return a pre-prepared ZIP file (for testing porpoises)
    fname = app.config.get( "PREPARED_ZIP" )
    if fname:
        with open( fname, "rb" ) as fp:
            on_done( fp.read() )
        return

    with TempFile() as input_file, TempFile() as prepared_file:

        # save the PDF file data
        input_file.write( pdf_data )
        input_file.close( delete=False )
        _logger.info( "Saved PDF file (#bytes=%d): %s", len(pdf_data), input_file.name )

        # initialize logging
        msg_types = set()
        def log_msg( msg_type, msg ):
            msg = msg.lstrip()
            if msg_type == "status":
                _logger.info( "[STATUS]: %s", msg )
            elif msg_type == "warning":
                _logger.warning( "[WARNING]: %s", msg )
            elif msg_type == "error":
                _logger.error( "[ERROR]: %s", msg )
            else:
                _logger.debug( "[%s] %s", msg_type, msg )
            if msg.startswith( "- " ):
                msg = msg[2:]
            sio.emit( msg_type, msg )
            msg_types.add( msg_type )

        # NOTE: The plan was to allow the user to change the default parameters in the UI,
        # but this can be done (ahem) later. For now, if they really need to change something,
        # they can prepare the data files from the command-line.
        args = []

        # extract everything we need from the PDF
        log_msg( "status", "Opening the PDF..." )
        extract = ExtractAll( args, log_msg )
        with PdfDoc( input_file.name ) as pdf:
            extract.extract_all( pdf )
        index_buf = io.StringIO()
        extract.extract_index.save_as_json( index_buf )
        targets_buf, chapters_buf, footnotes_buf = io.StringIO(), io.StringIO(), io.StringIO()
        extract.extract_content.save_as_json( targets_buf, chapters_buf, footnotes_buf )
        file_data = {
            "index": index_buf.getvalue(),
            "targets": targets_buf.getvalue(),
            "chapters": chapters_buf.getvalue(),
            "footnotes": footnotes_buf.getvalue(),
        }

        # prepare the PDF
        gs_path = get_gs_path()
        if not gs_path:
            raise RuntimeError( "Ghostscript is not available." )
        with TempFile( mode="w", encoding="utf-8" ) as targets_file:
            log_msg( "status", "Preparing the final PDF..." )
            # save the extracted targets
            targets_file.temp_file.write( file_data["targets"] )
            targets_file.close( delete=False )
            # prepare the PDF
            prepared_file.close( delete=False )
            prepare_pdf( input_file.name,
                "ASL Rulebook",
                targets_file.name, 5,
                prepared_file.name, "ebook",
                gs_path,
                log_msg
            )

        # fixup the PDF
        with TempFile() as fixedup_file:
            log_msg( "status", "Fixing up the final PDF..." )
            fixedup_file.close( delete=False )
            fixup_mmp_pdf( prepared_file.name,
                fixedup_file.name,
                False, True, True,
                log_msg
            )
            # read the final PDF data
            with open( fixedup_file.name, "rb" ) as fp:
                pdf_data = fp.read()

    # prepare the ZIP for the user to download
    log_msg( "status", "Preparing the download ZIP..." )
    zip_data = io.BytesIO()
    with zipfile.ZipFile( zip_data, "w", zipfile.ZIP_DEFLATED ) as zip_file:
        fname_stem = "ASL Rulebook"
        zip_file.writestr( fname_stem+".pdf", pdf_data )
        for key in file_data:
            fname = "{}.{}".format( fname_stem, key )
            zip_file.writestr( fname, file_data[key] )
    zip_data = zip_data.getvalue()

    # notify the front-end that we're done
    on_done( zip_data )
    _logger.debug( "Message types seen: %s",
        " ; ".join( sorted( str(mt) for mt in msg_types ) )
    )

    # NOTE: We don't bother shutting down the socketio server, since the user
    # has to restart the server, using the newly-prepared data files.

# ---------------------------------------------------------------------

@app.route( "/prepare/download" )
def download_prepared_data():
    """Download the prepared data ZIP file."""
    if not _zip_data_download:
        abort( 404 )
    return send_file(
        io.BytesIO( _zip_data_download ),
        as_attachment=True, attachment_filename="asl-rulebook2.zip"
    )

# ---------------------------------------------------------------------

def _test_progress( npasses=100, status=10, warnings=None, errors=None, delay=0.1 ):
    """Test progress messages."""

    # initialize
    warnings = [ int(w) for w in warnings.split(",") ] if warnings else []
    errors = [ int(e) for e in errors.split(",") ] if errors else []

    # generate progress messages
    sio = globvars.socketio_server
    status_no = 0
    for i in range( int(npasses) ):
        # check if we should start a new status block
        if i % status == 0:
            status_no += 1
            sio.emit( "status", "Status #{}".format( status_no ) )
        # issue the next progress message
        if 1+i in warnings:
            sio.emit( "warning", "Progress {}: warning".format( 1+i ) )
        if 1+i in errors:
            sio.emit( "error", "Progress {}: error".format( 1+i ) )
        else:
            sio.emit( "progress", "Progress {}.".format( 1+i ) )
        time.sleep( float( delay ) )
    sio.emit( "done" )
