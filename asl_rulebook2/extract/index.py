#!/usr/bin/env python3
""" Extract the index from the MMP eASLRB. """

import os
import json
import re

import click
from pdfminer.layout import LTChar

from asl_rulebook2.extract.base import ExtractBase
from asl_rulebook2.pdf import PdfDoc, PageIterator, PageElemIterator
from asl_rulebook2.utils import parse_page_numbers, fixup_text, extract_parens_content, jsonval, log_msg_stderr

# ---------------------------------------------------------------------

_DEFAULT_ARGS = {
    "pages": "10-41",
    "index_vp_left": 0, "index_vp_right": 565, "index_vp_top": 715, "index_vp_bottom": 20, # viewport
    "first_title": "a", "last_title": "X#", # first/last index entries
}

# ---------------------------------------------------------------------

class ExtractIndex( ExtractBase ):
    """Extract the index from the MMP eASLRB."""

    def __init__( self, args, log=None ):
        super().__init__( args, _DEFAULT_ARGS, log )
        self.index_entries = None
        self._prev_y0 = None
        # prepare to fixup problems in the index content
        fname2 = os.path.join( os.path.dirname(__file__), "data/index-fixups.json" )
        with open( fname2, "r", encoding="utf-8" ) as fp:
            self._fixups = json.load( fp )

    def extract_index( self, pdf ):
        """Extract the index from the MMP eASLRB."""

        # initialize
        page_nos = parse_page_numbers( self._args["pages"] )
        curr_title = curr_content = None

        # process each page in the index
        for page_no, _, lt_page in PageIterator( pdf ):

            if page_no > max( page_nos ):
                break
            if page_no not in page_nos:
                self.log_msg( "progress", "- Skipping page {}.", page_no )
                continue
            self.log_msg( "progress", "- Analyzing page {}.", page_no )

            # process each element on the page
            self._prev_y0 = 99999
            elem_filter = lambda e: isinstance( e, LTChar )
            for _, elem in PageElemIterator( lt_page, elem_filter=elem_filter ):

                # check if we should ignore this element
                if not self._in_viewport( elem, "index" ):
                    continue
                if self._is_ignore( elem ):
                    continue

                # NOTE: We identify the start of a new index entry by bold text at the start of a line.
                # We then collect the remaining bold text as the index entry's title, until we see some
                # non-bold text. This is collected as the index entry's content, until we see the start
                # of the next index entry.

                # figure out what we've got
                if self._is_bold( elem ):
                    if curr_content is not None:
                        # we've found the start of a new index entry
                        if curr_title:
                            # save the index entry we've just finished collecting
                            self._save_index_entry( curr_title, curr_content )
                            if curr_title == self._args["last_title"]:
                                curr_title = curr_content = None
                                break # nb: that was the last one - we're all done
                        curr_title = curr_content = None
                    if curr_title is None:
                        # start collecting the title
                        curr_title = elem.get_text()
                    else:
                        # continue collecting the title
                        curr_title += elem.get_text()
                else:
                    if curr_content is None:
                        # start collecting the content text
                        curr_content = elem.get_text()
                    else:
                        # continue collecting the content text
                        if elem.y0 - self._prev_y0 < -1 and curr_content.endswith( "-" ):
                            # join up hyphenated words
                            curr_content = curr_content[:-1] #pylint: disable=unsubscriptable-object
                        curr_content += elem.get_text()

                # loop back to process the next element
                self._prev_y0 = elem.y0

        # add the last index entry (if it hasn't already been done)
        if curr_title:
            self._save_index_entry( curr_title, curr_content )

        # check for unused fixups
        if self._fixups:
            self.log_msg( "warning", "Unused fixups: {}", self._fixups )

        # process the content for each index entry
        if not self.index_entries:
            raise RuntimeError( "Didn't find the first title (\"{}\").".format( self._args["first_title"] ) )
        self._process_content()

    def _save_index_entry( self, title, content ):
        """Save a parsed index entry."""

        # check if we've started parsing index entries
        # NOTE: There is some bold text at the start of the index, which we parse as an index title,
        # so we don't save anything until we've actually seen the first index entry.
        if self.index_entries is None:
            if title != self._args["first_title"]:
                return
            self.index_entries = []

        # initialize
        title, content = title.strip(), content.strip()
        if content.startswith( ":" ):
            content = content[1:].strip() # nb: this comes after the title, but we don't need it

        # save the new index entry
        if title == "bold":
            # FUDGE! Some entries have "bold" in their content, using a bold font :-/, which we detect
            # as the start of a new entry. We fix that up here.
            self.index_entries[-1]["content"] = "{} bold {}".format(
                self.index_entries[-1]["content"], fixup_text(content)
            )
        elif title == "C" and self.index_entries[-1]["title"] == "FFE":
            # FUDGE! The colon in the title for "FFE:C" is non-bold, so we parse this as two separate
            # index titles ("FFE" and "C") :-/ We can't fix this up in the normal way, since there is
            # also a real "FFE" entry, so we do it in the code here.
            self.index_entries[-1].update( {
                "title": "FFE:C", "content": fixup_text(content)
            } )
        else:
            # save the new index entry
            index_entry = self._make_index_entry( title, content )
            if index_entry:
                self.index_entries.append( index_entry )
            # FUDGE! EX/EXC are mis-parsed as a single index entry - we correct that in the fixups, and here.
            if title == "EX":
                self.index_entries.append( self._make_index_entry( "EXC", "Exception" ) )

    def _make_index_entry( self, title, content ):
        """Create a new index entry."""

        # initialize
        orig_content = content
        title = fixup_text( title )
        if title.endswith( ":" ):
            title = title[:-1]

        # check for any fixups
        fixup = self._fixups.pop( title, None )
        if fixup:
            # replace the title
            title = fixup.get( "new_title", title )
            # do any search-replace's
            for sr in fixup.get( "replace", [] ):
                new_content = content.replace( sr[0], sr[1] )
                if new_content == content:
                    self.log_msg( "warning", "Content fixup had no effect for \"{}\": {}", title, sr[0] )
                else:
                    content = new_content
            # replace the content
            old_content = fixup.get( "old_content" )
            if old_content:
                if fixup_text( content ) != old_content:
                    self.log_msg( "warning", "Unexpected content for \"{}\" - skipping fixup.", title )
                else:
                    new_content = fixup.get( "new_content" )
                    if not new_content:
                        return None
                    content = new_content

        # FUDGE! There are two "Entry" index entries, but one of them should be "Entry (Offboard)" (the parsing code
        # is actually correct, since the "(Offboard)" is not bold). We can't really fix this via the usual data-driven
        # fixups, so we fix it in the code here.
        if title == "Entry" and content.startswith( "(Offboard): " ):
            title += " (Offboard)"
            content = content[12:]

        return {
            "title": title,
            "content": fixup_text( content ),
            "raw_content": orig_content
        }

    def _process_content( self ):
        """Extract information out of the index entries into a structured form."""

        def fixup_ruleid( ruleid ):
            # FUDGE! The index often refers to the same rule as e.g. "O11.4 CG3" and "OCG3" :-/
            # We translate the former into the latter.
            if ruleid.startswith( "O11.4 CG" ):
                return "O" + ruleid[6:] # nb: Red Barricades
            elif ruleid.startswith( "P8.4 CG" ):
                return "P" + ruleid[5:] # nb: Kampfgruppe Peiper
            elif ruleid.startswith( "Q9.4 CG" ):
                return "Q" + ruleid[5:] # nb: Pegasus Bridge
            elif ruleid.startswith( "R9.4 CG" ):
                return "R" + ruleid[5:] # nb: A Bridge Too Far
            elif ruleid.startswith( "T15.4 CG" ):
                return "T" + ruleid[6:] # nb: Blood Reef Tarawa
            else:
                return ruleid

        for index_entry in self.index_entries:

            # initialize
            content = index_entry[ "content" ]

            # extract any "see also"
            mo = re.search( r"\(see (also )?(.+?)\):?", content )
            if mo:
                see_also = [ sa.strip() for sa in mo.group(2).split(",") ]
                if "SW" in see_also or "Class" in see_also:
                    # FUDGE! See-also's are normally comma-separated, but we don't want to
                    # split things like "Recovery, SW" or "Class, Personnel Types".
                    see_also = [ mo.group(2) ]
                index_entry[ "see_also" ] = see_also
                content = content[:mo.start()] + content[mo.end():]
                content = content.strip()

            # extract any sub-title
            if content.startswith( "(" ):
                pos = content.find( ")" )
                if pos < 0:
                    # FUDGE! Some index entries have the closing ) missing :-/
                    pos = content.find( ":" )
                    subtitle, content = content[1:pos], content[pos+1:]
                else:
                    subtitle, content = extract_parens_content( content )
                index_entry[ "subtitle" ] = subtitle.strip()
                if content.startswith( ":" ):
                    content = content[1:]
                content = content.strip()

            # extract any ruleid's
            ruleids = []
            while True:
                if content == "A./G.":
                    break # nb: special handling for "NCC" (National Capabilities Chart)
                mo = re.search( r"^(SSR )?[A-Z]{1,3}[0-9.-]+[A-Fa-f]?", content )
                if not mo:
                    break
                ruleids.append( mo.group() )
                content = content[mo.end():].strip()
                if content.startswith( "," ):
                    content = content[1:].strip()
                else:
                    break
            if ruleids:
                index_entry[ "ruleids" ] = [ fixup_ruleid( r ) for r in ruleids ]

            # extract any ruleref's
            rulerefs = []
            matches = list( re.finditer( r"\[(.+?)\]", content ) )
            if matches:
                for mo in reversed(matches):
                    val = mo.group(1)
                    # NOTE: We search for the ":" from the right, to avoid picking it up in the ruleref text.
                    pos = val.rfind( ":" )
                    if pos > 0:
                        vals = re.split( "[;,]", val[pos+1:] )
                        ruleids = [ fixup_ruleid( v.strip() ) for v in vals ]
                        val = val[:pos].strip()
                    else:
                        ruleids = None
                    rulerefs.append( { "caption": val, "ruleids": ruleids } )
                    content = content[:mo.start()] + content[mo.end():]
                index_entry[ "rulerefs" ] = list( reversed( rulerefs ) )

            # save the final content
            content = re.sub( r"\s+", " ", content ).strip()
            if content:
                index_entry[ "content" ] = content
            else:
                del index_entry["content"]

    def _is_ignore( self, elem ):
        """Check if we should ignore an element on the page."""
        # check if we have a bold item as the first thing on a line
        if self._is_bold( elem ) and elem.y0 - self._prev_y0 < -1:
            # yup - check if it's near the start of the line
            if self._is_near_start_of_line( elem ):
                # yup - this is the title for an index entry
                return False
            # nope - this is a header that indicates a new section (the index is grouped by letter)
            return True
        return False

    def _is_near_start_of_line( self, elem ):
        """Check if the element is near the start of its line."""
        if self._args["index_vp_left"] <= elem.x0 <= self._args["index_vp_left"]+20:
            # yup (left column)
            return True
        left = self._args["index_vp_left"] + (self._args["index_vp_right"]+1 - self._args["index_vp_left"]) / 2
        if left <= elem.x0 <= left+20:
            # yup (right column)
            return True
        return False

    def save_as_raw( self, out ):
        """Save the raw results."""
        for index_entry in self.index_entries:
            print( "=== {} ===".format( index_entry["title"] ), file=out )
            print( "{}".format( index_entry["raw_content"] ), file=out )
            print( file=out )

    def save_as_text( self, out ):
        """Save the results as plain-text."""
        for index_entry in self.index_entries:
            print( "=== {} ===".format( index_entry["title"] ), file=out )
            if "subtitle" in index_entry:
                print( index_entry["subtitle"], file=out )
            if index_entry.get( "ruleids" ):
                print( "RULEID'S: {}".format(
                    " ; ".join( index_entry["ruleids"] )
                ), file=out )
            if index_entry.get( "see_also" ):
                print( "SEE ALSO: {}".format(
                    " ; ".join( index_entry["see_also"] ),
                ), file=out )
            if index_entry.get( "content" ):
                print( "CONTENT:", index_entry["content"], file=out )
            if index_entry.get( "rulerefs" ):
                print( "RULEREF'S:", file=out )
                for ruleref in index_entry["rulerefs"]:
                    if ruleref["ruleids"]:
                        ruleids = [ "[{}]".format(ri) for ri in ruleref["ruleids"] ]
                        print( "- {} {}".format( ruleref["caption"], " ".join(ruleids) ), file=out )
                    else:
                        print( "- {}".format( ruleref["caption"] ), file=out )
            print( file=out )

    def save_as_json( self, out ):
        """Save the results as JSON."""
        entries = []
        for index_entry in self.index_entries:
            buf = []
            buf.append( "{{ \"title\": {}".format( jsonval(index_entry["title"]) ) )
            if "subtitle" in index_entry:
                buf.append( "  \"subtitle\": {}".format( jsonval(index_entry["subtitle"]) ) )
            if index_entry.get( "ruleids" ):
                buf.append( "  \"ruleids\": {}".format( jsonval(index_entry["ruleids"]) ) )
            if index_entry.get( "see_also" ):
                buf.append( "  \"see_also\": {}".format( jsonval(index_entry["see_also"]) ) )
            if index_entry.get( "content" ):
                buf.append( "  \"content\": {}".format( jsonval(index_entry["content"]) ) )
            if index_entry.get( "rulerefs" ):
                buf2 = []
                for ruleref in index_entry["rulerefs"]:
                    buf2.append( "    {{ \"caption\": {}, \"ruleids\": {} }}".format(
                        jsonval( ruleref["caption"] ),
                        jsonval( ruleref["ruleids"] )
                    ) )
                buf.append( "  \"rulerefs\": [\n{}\n  ]".format( ",\n".join(buf2) ) )
            entries.append( ",\n".join( buf ) + "\n}" )
        print( "[\n\n{}\n\n]".format( ",\n\n".join(entries) ), file=out )

# ---------------------------------------------------------------------

@click.command()
@click.argument( "pdf_file", nargs=1, type=click.Path(exists=True,dir_okay=False) )
@click.option( "--arg","args", multiple=True, help="Configuration parameter(s) (key=val)." )
@click.option( "--progress/--no-progress", is_flag=True, default=False, help="Log progress messages." )
@click.option( "--format","-f","output_fmt", default="json", type=click.Choice(["raw","text","json"]),
    help="Output format."
)
@click.option( "--output","-o","output_fname", required=True, help="Where to save the extracted index." )
def main( pdf_file, args, progress, output_fmt, output_fname ):
    """Extract the index from the MMP eASLRB."""

    # initialize
    args = ExtractBase.parse_args( args, _DEFAULT_ARGS )

    # extract the index
    def log_msg( msg_type, msg ):
        if msg_type == "progress" and not progress:
            return
        log_msg_stderr( msg_type, msg )
    extract = ExtractIndex( args, log_msg )
    extract.log_msg( "progress",  "Loading PDF: {}", pdf_file )
    with PdfDoc( pdf_file ) as pdf:
        extract.extract_index( pdf )

    # save the results
    with open( output_fname, "w", encoding="utf-8" ) as out:
        getattr( extract, "save_as_"+output_fmt )( out )

if __name__ == "__main__":
    main() #pylint: disable=no-value-for-parameter
