#!/usr/bin/env python3
""" Extract everything we need from the MMP eASLRB. """

import os
import json
import re
import importlib

import click

from asl_rulebook2.pdf import PdfDoc
from asl_rulebook2.extract.base import ExtractBase, log_msg_stderr
from asl_rulebook2.extract.index import ExtractIndex
from asl_rulebook2.extract.content import ExtractContent

# ---------------------------------------------------------------------

class ExtractAll( ExtractBase ):
    """Extract everything from the eASLRB."""

    def __init__( self, args, log=None ):
        super().__init__( None, None, log )
        self._args = args
        self.extract_index = None
        self.extract_content = None

    def extract_all( self, pdf ):
        """Extract everything from the eASLRB."""

        # initialize
        default_args = {}
        for mod in ( "index", "content" ):
            mod = importlib.import_module( "asl_rulebook2.extract." + mod )
            default_args.update( getattr( mod, "_DEFAULT_ARGS" ) )

        # extract the index
        self.log_msg( "progress",  "\nExtracting the index..." )
        args = ExtractBase.parse_args( self._args, default_args )
        self.extract_index = ExtractIndex( args, self._log )
        self.extract_index.extract_index( pdf )

        # extract the content
        self.log_msg( "progress",  "\nExtracting the content..." )
        args = ExtractBase.parse_args( self._args, default_args )
        self.extract_content = ExtractContent( args, self._log )
        self.extract_content.extract_content( pdf )

        # verify the index targets
        self._check_targets()

    def _check_targets( self ):
        """Cross-check ruleid's and ruleref's in the index against targets in the main content."""

        # build an index of known targets
        targets = {}
        for ruleid, target in self.extract_content.targets.items():
            assert ruleid not in targets
            targets[ ruleid ] = target["caption"]

        # load the list of known missing targets
        known_strings, known_regexes = set(), set()
        fname = os.path.join( os.path.dirname(__file__), "data/known-missing-ruleids.json" )
        with open( fname, "r", encoding="utf-8" ) as fp:
            data = json.load( fp )
            for chapter in data["chapters"]:
                known_regexes.add( re.compile( "^{}[0-9.]+[A-Ea-e]?$".format( chapter ) ) )
            known_strings.update( data["strings"] )
            known_regexes.update(
                re.compile( regex ) for regex in data["regexes"]
            )

        def is_known_ruleid( ruleid ):
            ruleid = re.sub( r"-[A-Z]?\.?\d+$", "", ruleid ) # e.g. "A1.23-.45" -> "A1.23"
            if ruleid.endswith( " EX" ):
                ruleid = ruleid[:-3]
            if ruleid in targets:
                return True
            if ruleid in known_strings:
                return True
            if any( regex.search( ruleid ) for regex in known_regexes ):
                return True
            return False

        # check each index entry
        first = True
        for index_entry in self.extract_index.index_entries:

            errors = []

            # check the index entry's ruleid's
            for ruleid in index_entry.get( "ruleids", [] ):
                if not is_known_ruleid( ruleid ):
                    errors.append( "Unknown ruleid: {}".format( ruleid ) )

            # check the index entry's ruleref's
            for ruleref in index_entry.get( "rulerefs", [] ):
                if not ruleref["ruleids"]:
                    continue
                # check each ruleref
                if ", ".join( r for r in ruleref["ruleids"] ) in known_strings:
                    # NOTE: This is some free-form text that has been split up because it contains commas.
                    continue
                for ruleid in ruleref["ruleids"]:
                    if not is_known_ruleid( ruleid ):
                        errors.append( "Unknown ruleref target: {} => [{}]".format( ruleref["caption"], ruleid ) )

            # log any errors
            if errors:
                if first:
                    self.log_msg( "warning", "\n=== Unknown targets ===\n" )
                    first = False
                errors = [ "- {}".format( e ) for e in errors ]
                self.log_msg( "warning", "{}:\n{}",
                    index_entry["caption"], "\n".join(errors)
                )

# ---------------------------------------------------------------------

@click.command()
@click.argument( "pdf_file", nargs=1, type=click.Path(exists=True,dir_okay=False) )
@click.option( "--arg","args", multiple=True, help="Configuration parameter(s) (key=val)." )
@click.option( "--progress/--no-progress", is_flag=True, default=False, help="Log progress messages." )
@click.option( "--format","-f","output_fmt", default="json", type=click.Choice(["raw","text","json"]),
    help="Output format."
)
@click.option( "--save-index","save_index_fname", required=True, help="Where to save the extracted index." )
@click.option( "--save-targets","save_targets_fname", required=True, help="Where to save the extracted targets." )
@click.option( "--save-footnotes","save_footnotes_fname", required=True, help="Where to save the extracted footnotes." )
def main( pdf_file, args, progress, output_fmt, save_index_fname, save_targets_fname, save_footnotes_fname ):
    """Extract everything we need from the MMP eASLRB."""

    # extract everything
    def log_msg( msg_type, msg ):
        if msg_type == "progress" and not progress:
            return
        log_msg_stderr( msg_type, msg )
    extract = ExtractAll( args, log_msg )
    extract.log_msg( "progress",  "Loading PDF: {}", pdf_file )
    with PdfDoc( pdf_file ) as pdf:
        extract.extract_all( pdf )

    # save the results
    with open( save_index_fname, "w", encoding="utf-8" ) as index_out, \
         open( save_targets_fname, "w", encoding="utf-8" ) as targets_out, \
         open( save_footnotes_fname, "w", encoding="utf-8" ) as footnotes_out:
        getattr( extract.extract_index, "save_as_"+output_fmt )( index_out )
        getattr( extract.extract_content, "save_as_"+output_fmt )( targets_out, footnotes_out )

if __name__ == "__main__":
    main() #pylint: disable=no-value-for-parameter
