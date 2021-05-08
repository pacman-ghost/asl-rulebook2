""" Test preparing the data files. """

import os
import json
import zipfile
import io
import base64

import pytest

from asl_rulebook2.tests.utils import for_each_easlrb_version
from asl_rulebook2.webapp.tests import pytest_options
from asl_rulebook2.webapp.tests.utils import init_webapp, \
    find_child, find_children, wait_for, wait_for_elem

# ---------------------------------------------------------------------

@pytest.mark.skipif( not pytest_options.enable_prepare, reason="Prepare tests are not enabled." )
def test_prepare_logging( webapp, webdriver ):
    """Test logging during the prepare process."""

    # initialize
    # NOTE: We load the webapp without setting a data directory first.
    init_webapp( webapp, webdriver,
        test=1, npasses=50, warnings="25,27,42", errors="39,43", delay=0
    )

    # generate some progress messages, check the results
    find_child( "#upload-panel button" ).click()
    def check_progress():
        progress = _unload_progress()
        return progress == [
            [ "Status #1", [] ],
            [ "Status #2", [] ],
            [ "Status #3", [
                [ "warning.png", "Progress 25: warning" ],
                [ "warning.png", "Progress 27: warning" ],
            ] ],
            [ "Status #4", [
                [ "error.png", "Progress 39: error" ]
            ] ],
            [ "Status #5", [
                [ "warning.png", "Progress 42: warning" ],
                [ "error.png", "Progress 43: error" ],
            ] ],
            [ "All done.", [] ]
        ]
    wait_for( 2, check_progress )

# ---------------------------------------------------------------------

@pytest.mark.skipif( not pytest_options.enable_prepare, reason="Prepare tests are not enabled." )
@pytest.mark.skipif( not pytest_options.easlrb_path, reason="eASLRB not available." )
def test_full_prepare( webapp, webdriver ):
    """Test the full prepare process."""

    def do_test( dname ):

        # initialize
        # NOTE: We load the webapp without setting a data directory first.
        init_webapp( webapp, webdriver )

        # load the PDF file data into the web page (since we can't manipulate the "Open File" dialog)
        fname = os.path.join( dname, "eASLRB.pdf" )
        with open( fname, "rb" ) as fp:
            zip_data = fp.read()
        testing_zip_data = find_child( "#testing-zip-data", webdriver )
        webdriver.execute_script( "arguments[0].value = arguments[1]", testing_zip_data,
            base64.b64encode( zip_data ).decode( "ascii" )
        )

        # start the prepare process, and wait for it to finish
        # NOTE: It will have auto-started because we passed in a filename to the webapp.
        find_child( "button#upload-proxy" ).click()
        wait_for_elem( 30*60, "#download-panel" )

        # get the results
        find_child( "button#download" ).click()
        zip_data = wait_for( 20, lambda: testing_zip_data.get_attribute( "value" ) )
        zip_data = base64.b64decode( zip_data )

        # check the results
        with zipfile.ZipFile( io.BytesIO( zip_data ) ) as zip_file:
            assert set( zip_file.namelist() ) == set( [
                "ASL Rulebook.pdf", "ASL Rulebook.index",
                "ASL Rulebook.targets", "ASL Rulebook.chapters", "ASL Rulebook.footnotes", "ASL Rulebook.vo-notes"
            ] )
            assert zip_file.getinfo( "ASL Rulebook.pdf" ).file_size > 40*1000
            for ftype in [ "index", "targets", "chapters", "footnotes" ]:
                fname = os.path.join( dname, ftype+".json" )
                expected = json.load( open( fname, "r" ) )
                fdata = zip_file.read( "ASL Rulebook.{}".format( ftype ) )
                assert json.loads( fdata ) == expected

    # run the test
    for_each_easlrb_version( do_test )

# ---------------------------------------------------------------------

def _unload_progress():
    """Unload the progress messages."""

    def unload_status_block( root ):
        """Unload a status block and its progress messages."""
        caption = find_child( ".caption", root ).text
        msgs = [
            unload_msg( row )
            for row in find_children( "tr", root )
            if row.is_displayed()
        ]
        return [ caption, msgs ]

    def unload_msg( row ):
        """Unload a single progress message."""
        cells = find_children( "td", row )
        assert len(cells) == 2
        img = find_child( "img", cells[0] )
        url = img.get_attribute( "src" )
        return [ os.path.basename(url), cells[1].text ]

    # unload each status block
    progress_panel = find_child( "#progress-panel" )
    return [
        unload_status_block( elem )
        for elem in find_children( ".status", progress_panel )
    ]
