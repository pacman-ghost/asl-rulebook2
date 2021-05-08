#!/usr/bin/env python3
""" Extract content from the MMP eASLRB. """

import os
import json
import re
import math
from collections import defaultdict

import click
from pdfminer.layout import LTChar

from asl_rulebook2.extract.base import ExtractBase
from asl_rulebook2.pdf import PdfDoc, PageIterator, PageElemIterator
from asl_rulebook2.utils import parse_page_numbers, fixup_text, append_text, remove_trailing, jsonval, log_msg_stderr

# NOTE: Characters are laid out individually on the page, and we generally want to process them top-to-bottom,
# left-to-right, but in some cases, alignment is messed up (e.g. the bounding boxes don't line up properly
# and e.g. the first part of a sentence is infintesimally lower down than the rest of the sentence, and so
# appears later in the sort order), and we get better results if we process characters in the order in which
# they appear in the PDF document.
_DISABLE_SORT_ITEMS = [
    "B40", # nb: to detect B31.1 NARROW STREET
    "A16",
    "A58","A59","A60", # Chapter A footnotes (nb: page A61 is a mess wrt element order :-/)
    "B1",
    "B45", "B46", # Chapter B footnotes
    "C25", "C26", # Chapter C footnotes
    "D27", # Chapter D footnotes
    "E28", "E29", "E30", # Chapter E footnotes
    "F20", "F21", # Chapter F footnotes
    "G48", "G49", "G50", # Chapter G footnotes
    "H9", # Chapter H footnotes
    429,431,432,433,434,435, # Italian vehicle notes
    436,437,438,439, # Italian ordnance notes
]

_DEFAULT_ARGS = {
    "chapter-a": "42-102", "chapter-b": "109-154", "chapter-c": "158-183", "chapter-d": "187-213",
    "chapter-e": "216-245", "chapter-f": "247-267", "chapter-g": "270-319", "chapter-h": "322-324,326-330",
    "chapter-j": "593",
    "chapter-w": "647-664",
    "content_vp_left": 0, "content_vp_right": 565, "content_vp_top": 715, "content_vp_bottom": 28, # viewport
    "disable-sort-items": ",".join( str(si) for si in _DISABLE_SORT_ITEMS )
}

# NOTE: The exact mappings here are actually not that important. What's important is:
# - the order of the nationality + V/O types
# - the page numbers themselves (so that they get parsed)
_VO_NOTE_SECTIONS = [
    [ "german", "vehicles", "330,332,334-343", True ],
    [ "german", "ordnance", "344-348", True ],
    [ "russian", "vehicles", "348,350-355", True ],
    [ "russian", "ordnance", "356-358", True ],
    [ "russian", "vehicles", "362,364-368", False ],
    [ "russian", "ordnance", "369", False ],
    [ "american", "vehicles", "371,373-383", True ],
    [ "american", "ordnance", "385-389", True ],
    [ "british", "vehicles", "395,398-417", True ],
    [ "british", "ordnance", "419-423", True ],
    [ "italian", "vehicles", "429,431-435", True ],
    [ "italian", "ordnance", "436-439", True ],
    [ "japanese", "vehicles", "443-448", True ],
    [ "japanese", "ordnance", "448-452", True ],
    [ "chinese", "vehicles", "456-459", True ],
    [ "chinese", "ordnance", "459-463", True ],
    [ "landing-craft", "vehicles", "467-468", True ],
    [ "french", "vehicles", "470,472-480", True ],
    [ "french", "ordnance", "482-487", True ],
    [ "allied-minor", "vehicles", "492-493,495-500", True ],
    [ "allied-minor", "ordnance", "501-504", True ],
    [ "axis-minor", "vehicles", "506,508-515", True ],
    [ "axis-minor", "ordnance", "516,518-527", True ],
    [ "finnish", "vehicles", "536,538-541", True ],
    [ "finnish", "ordnance", "543,545-549", True ],
    [ "un-forces", "vehicles", "554,556-565", True ],
    [ "un-forces", "ordnance", "567-570", True ],
    [ "communist-forces", "vehicles", "580", True ],
    [ "communist-forces", "ordnance", "581-585", True ],
]

# ---------------------------------------------------------------------

class ExtractContent( ExtractBase ):
    """Extract content from the MMP eASLRB."""

    def __init__( self, args, log=None ):
        super().__init__( args, _DEFAULT_ARGS, log )
        self.targets = {}
        self._chapters = []
        self._footnotes = {}
        self._vo_notes = self._prev_vo_note_id = None
        self._curr_vo_note_section = 0
        self._curr_chapter = self._curr_footnote = self._curr_pageid = None
        self._prev_elem = self._top_left_elem = None
        # prepare to fixup problems in the content
        def load_fixup( fname ):
            fname = os.path.join( os.path.dirname(__file__), "data/", fname )
            with open( fname, "r", encoding="utf-8" ) as fp:
                return json.load( fp )
        self._target_fixups = load_fixup( "target-fixups.json" )
        self._chapter_fixups = load_fixup( "chapter-fixups.json" )
        self._footnote_fixups = load_fixup( "footnote-fixups.json" )
        self._vo_note_fixups = load_fixup( "vo-note-fixups.json" )

    def extract_content( self, pdf ):
        """Extract content from the MMP eASLRB."""

        # figure out which pages to process
        chapter_pages = {} # maps chapters to page numbers
        page_index = {} # maps page numbers to chapter
        for key, val in self._args.items():
            if key.startswith( "chapter-" ):
                page_nos = parse_page_numbers( val )
                assert len(key) == 9
                chapter = key[8].upper()
                chapter_pages[ chapter ] = page_nos
                for page_no in page_nos:
                    page_index[ page_no ] = chapter
        disable_sort_items = set( self._args["disable-sort-items"].split( "," ) )

        # include the pages for the Chapter H vehicle/ordnance notes
        for _, _, page_nos, _ in _VO_NOTE_SECTIONS:
            page_nos = parse_page_numbers( page_nos )
            for page_no in page_nos:
                page_index[ page_no ] = "H"

        # initialize
        self._curr_chapter = None
        curr_chapter_pageno = None
        self._curr_footnote = None

        # NOTE: The parsing code works in two modes.
        # - We start off extracting content, and detect the start of a new rule by bold text near the start of the line.
        # - When we see the footnotes header (e.g. "CHAPTER A FOOTNOTES"), we switch into footnotes mode, and detect
        #   the start of a footnote by a bold number near the start of the line.

        # process each page
        for page_no, _, lt_page in PageIterator( pdf ):

            # prepare to process the next page
            if page_no > max( page_index.keys() ):
                break
            if page_no not in page_index:
                self.log_msg( "progress", "- Skipping page {}.", page_no )
                if curr_chapter_pageno is not None:
                    curr_chapter_pageno += 1
                continue
            if not self._curr_chapter or self._curr_chapter != page_index[page_no]:
                # we've found the start of a new chapter
                self._save_footnote() # nb: save the last footnote of the previous chapter
                self._curr_chapter = page_index[ page_no ]
                curr_chapter_pageno = 1
            else:
                curr_chapter_pageno += 1
            self._curr_pageid = "{}{}".format( # nb: this is the ASL page# (e.g. "A42"), not the PDF page#
                self._curr_chapter, curr_chapter_pageno
            )
            # NOTE: There have been so many extra pages added to Chapter H, there's no easy way to calculate
            # the page ID. We could set up a table mapping physical page numbers to page ID's, but that's
            # far more trouble than it's worth.
            self.log_msg( "progress", "- Analyzing page {}{}.",
                page_no, " ({})".format( self._curr_pageid ) if not self._curr_pageid.startswith("H") else ""
            )

            # process each element on the page
            curr_caption = None
            self._top_left_elem = self._prev_elem = None
            elem_filter = lambda e: isinstance( e, LTChar )
            sort_elems = self._curr_pageid not in disable_sort_items and str(page_no) not in disable_sort_items
            for _, elem in PageElemIterator( lt_page, elem_filter=elem_filter, sort_elems=sort_elems ):

                # skip problematic elements
                if elem.fontname == "OYULKV+MyriadPro-Regular":
                    # FUDGE! Some symbols are represented as characters, which can sometimes cause problems
                    # (e.g. in v1.05, the diamond for A7.8 PIN broke caption parsing), and the easiest way
                    # to work-around this is to just ignore those characters.
                    continue

                # keep track of the top-left-most bold element
                if self._is_bold( elem ):
                    if self._top_left_elem is None \
                       or elem.x0 < self._top_left_elem.x0 and elem.y1 > self._top_left_elem.y1:
                        self._top_left_elem = elem

                # check if we should ignore this element
                if not self._in_viewport( elem, "content" ):
                    continue

                # check if we're currently extracting footnotes
                if self._curr_footnote is not None:
                    self._on_footnote_elem( elem, lt_page, page_no )
                    self._prev_elem = elem
                    continue

                # figure out what we've got
                is_bold = self._is_bold( elem )
                ch = curr_caption[0] if curr_caption else None #pylint: disable=unsubscriptable-object
                if is_bold and ch and ch.isdigit() and 1 < elem.y1 - self._prev_elem.y0 < elem.height/2:
                    # the previous bold character looks like a footnote superscript - ignore it
                    curr_caption = None
                if curr_caption and elem.get_text() == " ":
                    # FUDGE! Some captions are in a bold font, but the spaces are not :-/
                    is_bold = True
                if is_bold:
                    if curr_caption:
                        # NOTE: We stop collecting bold characters at the end of the line, even if they continue on
                        # to the next line. This is to handle the case of a major heading (e.g. "1. PERSONNEL COUNTERS")
                        # being followed by a lesser heading ("1.1"). However, we want to handle captions that span
                        # multiple lines, so we check the vertical distance between the lines to see if it looks like
                        # two separate headings, or a single caption that has spread over multiple lines.
                        if self._prev_elem.y0 - elem.y1 > 0.25*elem.height:
                            # we've found the start of a new rule - save the old one, start collecting the new caption
                            self._save_target( curr_caption, page_no, lt_page, elem )
                            curr_caption = [ elem.get_text(), ( elem.x0, elem.y1 ) ]
                        else:
                            # continue collecting the caption
                            if self._prev_elem.y0 - elem.y0 > 1:
                                # nb: we just started a new line
                                curr_caption[0] = append_text( #pylint: disable=unsupported-assignment-operation
                                    curr_caption[0], elem.get_text() #pylint: disable=unsubscriptable-object
                                )
                            else:
                                curr_caption[0] += elem.get_text() #pylint: disable=unsupported-assignment-operation
                    else:
                        # check if this is the first character of the line
                        if self._is_start_of_line( elem, lt_page ):
                            # yup - start collecting the caption
                            curr_caption = [ elem.get_text(), ( elem.x0, elem.y1 ) ]
                else:
                    # check if we're currently collecting a caption
                    if curr_caption:
                        # yup - we've just found the end of it, save it
                        self._save_target( curr_caption, page_no, lt_page, elem )
                        curr_caption = None

                # loop back to process the next element
                self._prev_elem = elem

        # add the last caption/footnote (if they haven't already been done)
        self._save_footnote()
        if curr_caption:
            self._save_target( curr_caption, page_no, None, None )

        # check for unused fixups
        if self._target_fixups:
            self.log_msg( "warning", "Unused fixups: {}", self._target_fixups )
        if self._footnote_fixups:
            self.log_msg( "warning", "Unused fixups: {}", self._footnote_fixups )
        if self._vo_note_fixups:
            self.log_msg( "warning", "Unused fixups: {}", self._vo_note_fixups )

        # extract the chapters
        self._extract_chapters()

    def _save_target( self, caption, page_no, lt_page, elem ):
        """Save a parsed target."""

        # initialize
        orig_caption = caption[0]
        caption_text = re.sub( r"\s+", " ", caption[0] ).strip()
        if len(caption_text) <= 1:
            # NOTE: We're finding text that is part of an image (e.g. the "E" for an Elite MMC),
            # perhaps because the pages were OCR'ed, so we ignore these.
            return

        # check if we've found the start of the chapter's footnotes
        if "FOOTNOTES" in caption_text :
            # yup - notify the main loop
            self._curr_footnote = []
            if elem:
                self._on_footnote_elem( elem, lt_page, page_no )
            return

        # check if the entry needs to be fixed up
        fixup = self._target_fixups.get( self._curr_pageid, {} ).get( caption_text )
        if fixup:
            # yup - make it so
            fixup[ "instances" ] = fixup.get("instances",1) - 1
            if fixup["instances"] <= 0:
                self._target_fixups[ self._curr_pageid ].pop( caption_text )
                if not self._target_fixups[ self._curr_pageid ]:
                    del self._target_fixups[ self._curr_pageid ]
            ruleid = fixup.get( "new_ruleid" )
            if not ruleid:
                return
            caption_text = fixup.get( "new_caption" )
        else:
            # nope - use what was parsed
            # FUDGE! There are a lot of layout problems with things like "12.CONCEALMENT" (i.e. missing space),
            # and it's tricky to detect these and not get tripped up by things like "12.C blah", so we handle it
            # as a separate case.
            mo = re.search( r"^(\d+\.\d*)([^ 0-9].+)", caption_text )
            if mo:
                ruleid, caption_text = mo.group(1), mo.group(2).strip()
            else:
                # check if the caption text starts with something that looks like a ruleid
                # NOTE: A leading "*" indicates an optional rule.
                mo = re.search( r"^\*?([A-Z]\.?)?[1-9][0-9.-]*[A-F]?", caption_text )
                if not mo:
                    return
                ruleid, caption_text = mo.group(), caption_text[mo.end():].strip()
                if ruleid.startswith( "*" ):
                    ruleid = ruleid[1:]
            ruleid = remove_trailing( ruleid, "." )
            caption_text = remove_trailing( caption_text, ":" )

        # save the new target
        if not ruleid.startswith( self._curr_chapter ):
            ruleid = self._curr_chapter + ruleid
        if ruleid in self.targets:
            self.log_msg( "warning", "Ignoring duplicate ruleid: {} (from \"{}\").",
                ruleid, caption[0]
            )
            return
        if caption_text == "\u2014":
            caption_text = "-" # nb: for A7.306 :-/
        self.targets[ ruleid ] = {
            "caption": fixup_text(caption_text), "page_no": page_no, "pos": caption[1],
            "raw_caption": orig_caption
        }

    def _on_footnote_elem( self, elem, lt_page, page_no ):
        """Process an element while we're parsing footnotes."""
        # check if we've found the start of a new footnote
        if self._is_bold( elem ):
            if elem.get_text().isdigit() and self._is_start_of_line( elem, lt_page ):
                # yup - save the current footnote, start collecting the new one
                self._save_footnote()
                elem_pos = ( elem.x0, elem.y1 )
                self._curr_footnote = [ elem.get_text(), "", page_no, elem_pos ]
            else:
                if self._curr_footnote[1]:
                    # FUDGE! Some footnote content has bold text hard-up at the left margin,
                    # so we collect that as normal content.
                    self._curr_footnote[1] += elem.get_text()
                else:
                    # we're still collecting the footnote's ID
                    # NOTE: Older chapters have only the footnote ID in bold text, while newer chapters have
                    # both the ID and caption in bold. We figure out what's going on later, in _save_footnote().
                    self._curr_footnote[0] += elem.get_text()
        else:
            # nope - we're still collecting the footnote's content
            if not self._prev_elem or elem.x0 < self._prev_elem.x0 or elem.y0 - self._prev_elem.y0 > lt_page.height/2:
                # nb: we just started a new line
                self._curr_footnote[1] = append_text( self._curr_footnote[1], elem.get_text() )
            else:
                self._curr_footnote[1] += elem.get_text()

    def _save_footnote( self ): #pylint: disable=too-many-branches
        """Save a parsed footnote."""

        if not self._curr_footnote:
            return

        # initialize
        if self._curr_chapter not in self._footnotes:
            # start saving footnotes for the chapter
            self._footnotes[ self._curr_chapter ] = []
        orig_content = self._curr_footnote[1]

        # separate the footnote ID, referenced rule, and content
        if self._curr_chapter in ( "F", "G", "W" ):
            # NOTE: Chapter F/G footnote captions are also bold.
            mo = re.search( r"^\d{1,2}\.", self._curr_footnote[0] )
            if mo:
                parts = mo.group(), self._curr_footnote[0][mo.end():]
                self._curr_footnote[0] = parts[0]
                self._curr_footnote[1] = parts[1].strip() + " " + self._curr_footnote[1].strip()
            else:
                self.log_msg( "warning", "Couldn't split Chapter F footnote caption: {}", self._curr_footnote[0] )
        footnote_id = remove_trailing( self._curr_footnote[0].strip(), "." )
        content = self._curr_footnote[1].strip()
        mo = re.search( r"^(F\.1B|W\.\d+[AB]|[A-Z]?[0-9.]+)", content )
        if mo:
            ruleid, content = mo.group(), content[mo.end():]
            if not ruleid.startswith( self._curr_chapter ):
                ruleid = self._curr_chapter + ruleid
            ruleid = remove_trailing( ruleid, "." )
        else:
            ruleid = None
        if self._curr_chapter == "C":
            # FUDGE! The "29." for Chapter C's footnote #29 is misaligned, and is extracted as two separate
            # footnotes "2" and "9". There isn't really any way to fix this via the normal data-driven mechanism,
            # so we do it in the code here :-/
            footnote_ids = [ f["footnote_id"] for f in self._footnotes[self._curr_chapter] ]
            if footnote_id == "2" and "2" in footnote_ids:
                return
            if footnote_id == "9" and "9" in footnote_ids:
                footnote_id = "29"

        if self._curr_chapter == "H":
            # check if we've gone past the end of the Chapter H footnotes
            if self._vo_notes is None and len(footnote_id) > 1:
                # yup - start collecting vehicle/ordnance notes
                self._vo_notes = defaultdict( lambda: defaultdict( list ) )
            # check if we're collecting Chapter H vehicle/ordnance notes
            if self._vo_notes is not None:
                # yup - save the next entry (the "footnote" is actually a vehicle/ordnance note)
                self._save_vo_note( footnote_id, self._curr_footnote[2], self._curr_footnote[3] )
                self._curr_footnote = None
                return

        # clean up the content
        content = re.sub( r"\s+", " ", content ).strip()
        content = fixup_text( content )
        mo = re.search( r"^[A-Z ]+:\S", content )
        if mo:
            content = content[:mo.end()-1] + " " + content[mo.end()-1:]

        # check for any fixups
        captions = []
        fixups = self._footnote_fixups.get( self._curr_chapter, {} ).get( footnote_id )
        if fixups:
            if isinstance( fixups, list ):
                # NOTE: A simple search-and-replace is, by far, the most common fixup, so we provide
                # a simplified way of specifying these in the fixup file
                fixups = { "replace": [ ( sr[0], sr[1] ) for sr in fixups ] }
            errors = []
            # do any search-replace's
            if "replace" in fixups:
                failed_sr = []
                for sr in fixups["replace"]:
                    prev_content = content
                    content = content.replace( sr[0], sr[1] )
                    if content == prev_content:
                        self.log_msg( "warning", "Footnote fixup for \"{}:{}\" had no effect: {}",
                            self._curr_chapter, footnote_id, sr[0]
                        )
                        failed_sr.append( sr )
                if failed_sr:
                    fixups["replace"] = failed_sr
                else:
                    del fixups["replace"]
            # replace the captions
            if "captions" in fixups:
                captions = fixups.pop( "captions" )
            # check that all fixups were successfully applied
            if fixups:
                errors.append( fixups )
            if errors:
                self._footnote_fixups[ self._curr_chapter ][ footnote_id ] = errors
            else:
                del self._footnote_fixups[ self._curr_chapter ][ footnote_id ]
                if not self._footnote_fixups[ self._curr_chapter ]:
                    del self._footnote_fixups[ self._curr_chapter ]
            content = content.strip()

        # extract the footnote's caption
        if not captions:
            pos = content.find( ":" )
            if pos >= 0:
                captions.append( ( ruleid, content[:pos] ) )
                content = content[pos+1:].strip()
            else:
                self.log_msg( "warning", "Can't extract footnote caption: {}:{} - {}",
                    self._curr_chapter, footnote_id, content
                )

        # check for the credits at the end of the Chapter F footnotes
        if self._curr_chapter == "F":
            pos = content.find( "WEST OF ALAMEIN CREDITS" )
            if pos > 0:
                content = content[:pos]
        # check for the start of the vehicle notes at the end of the Chapter H footnotes
        if self._curr_chapter == "H":
            pos = content.find( "GERMAN VEHICLE NOTES" )
            if pos > 0:
                content = content[:pos]

        # save the footnote
        self._footnotes[ self._curr_chapter ].append( {
            "footnote_id": footnote_id,
            "captions": captions,
            "content": content,
            "raw_content": orig_content
        } )
        self._curr_footnote = None

    def _save_vo_note( self, caption, page_no, page_pos ):
        """Save an extracted vehicle/ordnance note."""

        # NOTE: Some pieces of text cause the parsing code to go wonky (typically because it's seen
        # a "1" and so thinks it's found the start of a new section), so we manually skip over these.
        skips = self._vo_note_fixups.get( "skips", {} ).get( str(page_no) )
        if skips:
            for i, target in enumerate(skips):
                if self._check_string( caption, target ):
                    # we've got a caption that should be skipped - remove it from the list, and return
                    del skips[i]
                    if not skips:
                        del self._vo_note_fixups["skips"][ str(page_no) ]
                        if not self._vo_note_fixups["skips"]:
                            del self._vo_note_fixups["skips"]
                    return
        if caption.isdigit() and page_no not in (354, 417):
            return

        def apply_fixups( vo_note_id, caption ):
            nat, vo_type, _, _ = _VO_NOTE_SECTIONS[ self._curr_vo_note_section ]
            fixup = self._vo_note_fixups.get( nat, {} ).get( vo_type, {} ).get( vo_note_id )
            if fixup:
                if self._check_string( caption, fixup["old_caption"] ):
                    # remove the fixup
                    del self._vo_note_fixups[ nat ][ vo_type ][ vo_note_id ]
                    cleanup_fixups( nat, vo_type )
                    # apply the fixup
                    if "new_vo_note_id" in fixup:
                        vo_note_id = fixup["new_vo_note_id"]
                    if "new_caption" in fixup:
                        caption = fixup["new_caption"]
            return vo_note_id, caption

        def cleanup_fixups( nat, vo_type ):
            if nat not in self._vo_note_fixups:
                return
            if vo_type in self._vo_note_fixups[nat] and not self._vo_note_fixups[ nat ][ vo_type ]:
                del self._vo_note_fixups[ nat ][ vo_type ]
                if nat in self._vo_note_fixups and not self._vo_note_fixups[ nat ]:
                    del self._vo_note_fixups[ nat ]

        # extract the note number and caption
        mo = re.search( r"^[1-9][0-9.]*", caption )
        if not mo:
            return
        vo_note_id = mo.group()
        caption = caption[ mo.end() : ].strip()
        if vo_note_id.endswith( "." ):
            vo_note_id = vo_note_id[:-1]
        if caption.endswith( ":" ):
            caption = caption[:-1].strip()
        if caption.startswith( ( "cm ", "mm ", "pdr", "-cwt" ) ):
            # FUDGE! Things like "5.1 2.2cm Big Gun" are getting parsed as "5.12.2: + "cm Big Gun" :-/
            pos = vo_note_id.find( "." )
            if pos >= 0:
                caption = vo_note_id[pos+1:] + caption
                vo_note_id = vo_note_id[:pos]

        # check for any fixups
        vo_note_id, caption = apply_fixups( vo_note_id, caption )

        # compare the note ID with the previous one
        nat, vo_type, _, check_seq = _VO_NOTE_SECTIONS[ self._curr_vo_note_section ]
        def get_base_note_id( val ):
            pos = val.find( "." )
            return int( val[:pos] if pos >= 0 else val )
        base_note_id = get_base_note_id( vo_note_id )
        if self._prev_vo_note_id:
            # check if we've found the start of the next section
            if base_note_id == 1:
                # yup - add any extra entries to the current section
                add_vo_entries = self._vo_note_fixups.get( nat, {} ).get( vo_type, {} ).pop( "add", [] )
                for vo_entry in add_vo_entries:
                    self._vo_notes[ nat ][ vo_type ].append( vo_entry )
                cleanup_fixups( nat, vo_type )
                # get the next nationality + V/O type
                self._curr_vo_note_section += 1
                nat, vo_type, _, _ = _VO_NOTE_SECTIONS[ self._curr_vo_note_section ]
                # check for any fixups
                vo_note_id, caption = apply_fixups( vo_note_id, caption )
            elif check_seq:
                # compare the note ID with the previous one
                prev_base_note_id = get_base_note_id( self._prev_vo_note_id )
                if base_note_id == prev_base_note_id + 1:
                    pass # nb: this is the normal case, we've found the next V/O note
                elif base_note_id == prev_base_note_id and "." in vo_note_id:
                    pass # nb: this is to allow things like "9.1" following "9"
                else:
                    return # nb: we got some junk that can be ignored

        # save the V/O note
        self._vo_notes[ nat ][ vo_type ].append( {
            "vo_note_id": vo_note_id, "caption": caption,
            "page_no": page_no, "page_pos": page_pos
        } )
        if nat == "allied-minor" and vo_type == "ordnance" and vo_note_id == "19":
            # FUDGE! Because we're not seing Allied Minor Ordnance Note 20 :-/
            self._prev_vo_note_id = "20"
        else:
            self._prev_vo_note_id = vo_note_id

    def _extract_chapters( self ):
        """Extract the chapters and their sections."""

        # FUDGE! Extracting the index at the start of each chapter from the PDF would be horribly complicated,
        # since they are laid out as a 2-column table, but the PDF elements run left-to-right across the entire table,
        # and things get very messy when the section title spans multiple lines :-/
        # We fudge around this by doing things as a post-processing step, looking for targets that have a ruleid
        # that match a particular form.

        # initialize
        self._chapters = []
        fixup_regexes = [
            ( re.compile( r"\b{}\b".format( word.title() ) ), word )
            for word in self._chapter_fixups["capitalize_words"]
        ]

        # process each chapter
        for arg, val in self._args.items():
            mo = re.search( r"^chapter-([a-z])$", arg )
            if not mo:
                continue
            chapter_id = mo.group(1).upper()
            ruleid_regex = re.compile( r"^{}(\d+)$".format( chapter_id ) )
            page_nos = parse_page_numbers( val )
            # look for ruleid's that mark the start of a section
            sections = []
            for ruleid, target in self.targets.items():
                mo = ruleid_regex.search( ruleid )
                if not mo:
                    continue
                # found one - add it to the list
                fixup = self._chapter_fixups.get( "replace", {} ).pop( ruleid, None )
                if fixup:
                    caption = target["caption"]
                    if caption != fixup[0]:
                        self.log_msg( "warning", "Unexpected chapter fixup caption ({}): {}",
                            ruleid, caption
                        )
                    caption = fixup[1]
                else:
                    caption = target["caption"].title()
                for fixup in fixup_regexes:
                    caption = fixup[0].sub( fixup[1], caption )
                sections.append( {
                    "caption": "{}. {}".format( mo.group(1), caption ),
                    "ruleid": ruleid,
                } )
            # FUDGE! Chapter titles often span across the width of the page i.e. across both columns
            # of the 2-column layout, which makes them messy to parse. There are not too many of them,
            # so it's easier just to specify them manually :-/
            title = self._chapter_fixups.get( "titles", {} ).get(
                chapter_id, "Chapter "+chapter_id
            )
            self._chapters.append( {
                "chapter_title": title,
                "chapter_id": chapter_id,
                "page_no": min( page_nos ),
                "sections": sections
            } )

        # check for unused search-and-replace fixups
        fixups = self._chapter_fixups.get( "replace" )
        if fixups:
            self.log_msg( "warning", "Unused chapter fixup: {}", fixups )

    def _is_start_of_line( self, elem, lt_page ):
        """Check if the element is at the start of its line."""
        # NOTE: We can't just check the element's x co-ordinate, since there is sometimes a floating image
        # that pushes the text right (e.g. A.12).
        if self._prev_elem is None:
            return True
        if elem.y0 < self._prev_elem.y0:
            return True
        if self._prev_elem.x0 < lt_page.width/2 and elem.x0 > lt_page.width/2:
            return True # the element is at the top of the right column
        return False

    def save_as_raw( self, targets_out, chapters_out, footnotes_out, vo_notes_out ):
        """Save the raw results."""
        self._save_as_raw_or_text( targets_out, chapters_out, footnotes_out, vo_notes_out, True )

    def save_as_text( self, targets_out, chapters_out, footnotes_out, vo_notes_out ):
        """Save the results as plain-text."""
        self._save_as_raw_or_text( targets_out, chapters_out, footnotes_out, vo_notes_out, False )

    def _save_as_raw_or_text( self, targets_out, chapters_out, footnotes_out, vo_notes_out, raw ):
        """Save the results as raw or plain-text."""

        # save the targets
        curr_page_no = None
        for ruleid, target in self.targets.items():
            if target["page_no"] != curr_page_no:
                if curr_page_no:
                    print( file=targets_out )
                print( "=== p{} ===".format( target["page_no"] ), file=targets_out )
                curr_page_no = target["page_no"]
            xpos, ypos = self._get_page_pos( target["pos"] )
            if raw:
                print( "[{},{}] = {}".format(
                    xpos, ypos, target["raw_caption"]
                ), file=targets_out )
            else:
                print( "{} => {} @ p{}:[{},{}]".format(
                    ruleid, target["caption"], target["page_no"], xpos, ypos
                ), file=targets_out )

        # save the chapters
        for chapter_no, chapter in enumerate(self._chapters):
            if chapter_no > 0:
                print( file=chapters_out )
            print( "=== {}: {} (p{}) ===\n".format(
                chapter["chapter_id"], chapter["chapter_title"], chapter["page_no"]
            ), file=chapters_out )
            for section in chapter["sections"]:
                print( "{} => {}".format(
                    section["caption"], section["ruleid"],
                ), file=chapters_out )

        # save the footnotes
        def make_caption( caption ):
            buf = []
            if caption[1]:
                buf.append( caption[1] )
                if caption[0]:
                    buf.append( "[{}]".format( caption[0] ) )
            elif caption[0]:
                buf.append( caption[0] )
            return " ".join( buf )
        for chapter, footnotes in self._footnotes.items():
            if chapter != "A":
                print( file=footnotes_out )
            print( "=== CHAPTER {} FOOTNOTES {}".format( chapter, 80*"=" )[:80], file=footnotes_out )
            for footnote in footnotes:
                print( file=footnotes_out )
                print( "--- Footnote {} ---".format( footnote["footnote_id"] ), file=footnotes_out )
                if raw:
                    print( footnote["raw_content"], file=footnotes_out )
                else:
                    print( " ; ".join( make_caption(c) for c in footnote["captions"] ), file=footnotes_out )
                    print( footnote["content"], file=footnotes_out )

        # save the vehicle/ordnance notes
        first = True
        for nat, vo_types in self._vo_notes.items():
            for vo_type, vo_entries in vo_types.items():
                if first:
                    first = False
                else:
                    print( file=vo_notes_out )
                print( "=== {} ===".format(
                    nat if nat == "landing-craft" else "{} {}".format( nat, vo_type )
                ), file=vo_notes_out )
                for vo_entry in vo_entries:
                    if "page_pos" in vo_entry:
                        xpos, ypos = ExtractContent._get_page_pos( vo_entry["page_pos"] )
                        page_pos = "[{},{}]".format( xpos, ypos )
                    else:
                        page_pos = None
                    print( "{:<5} {} @p{}{}".format(
                        vo_entry["vo_note_id"]+":", vo_entry["caption"], vo_entry["page_no"],
                        ":"+page_pos if page_pos else ""
                    ), file=vo_notes_out )

    def save_as_json( self, targets_out, chapters_out, footnotes_out, vo_notes_out ):
        """Save the results as JSON."""

        # save the targets
        targets, curr_chapter = [], None
        for ruleid, target in self.targets.items():
            xpos, ypos = self._get_page_pos( target["pos"] )
            targets.append( "{}: {{ \"caption\": {}, \"page_no\": {}, \"pos\": [{},{}] }}".format(
                jsonval( ruleid ),
                jsonval(target["caption"]), target["page_no"], xpos, ypos
            ) )
            if ruleid[0] != curr_chapter:
                targets[-1] = "\n" + targets[-1]
                curr_chapter = ruleid[0]
        print( "{{\n{}\n\n}}".format(
            ",\n".join( targets )
        ), file=targets_out )

        # save the chapters
        chapters = []
        for chapter in self._chapters:
            sections = []
            for section in chapter["sections"]:
                sections.append( "    {{ \"caption\": {}, \"ruleid\": {} }}".format(
                    jsonval(section["caption"]), jsonval(section["ruleid"])
                ) )
            chapters.append(
                "{{ \"title\": {},\n  \"chapter_id\": {},\n  \"page_no\": {},\n  \"sections\": [\n{}\n] }}".format(
                jsonval(chapter["chapter_title"]), jsonval(chapter["chapter_id"]), jsonval(chapter["page_no"]),
                ",\n".join( sections )
            ) )
        print( "[\n\n{}\n\n]".format(
            ",\n\n".join( chapters )
        ), file=chapters_out )

        # save the footnotes
        def make_caption( caption ):
            return "{{ \"caption\": {}, \"ruleid\": {} }}".format(
                jsonval(caption[1]), jsonval(caption[0])
            )
        chapters = []
        for chapter in self._footnotes:
            footnotes = []
            for footnote in self._footnotes[chapter]:
                footnotes.append( "{}: {{\n  \"captions\": {},\n  \"content\": {}\n}}".format(
                    jsonval( footnote["footnote_id"] ),
                    "[ {} ]".format( ", ".join( make_caption(c) for c in footnote["captions"] ) ),
                    jsonval( footnote["content"] )
                ) )
            chapters.append( "{}: {{\n\n{}\n\n}}".format(
                jsonval( chapter ),
                ",\n".join( footnotes )
            ) )
        print( "{{\n\n{}\n\n}}".format(
            ",\n\n".join( chapters )
        ), file=footnotes_out )

        # save the vehicle/ordnance notes
        vo_notes = []
        for nat in self._vo_notes:
            vo_types = []
            for vo_type, vo_entries in self._vo_notes[nat].items():
                entries = []
                for vo_entry in vo_entries:
                    val = "{}: {{ \"caption\": {}, \"page_no\": {}".format(
                        jsonval(vo_entry["vo_note_id"]), jsonval(vo_entry["caption"]), jsonval(vo_entry["page_no"])
                    )
                    if "page_pos" in vo_entry:
                        xpos, ypos = self._get_page_pos( vo_entry["page_pos"] )
                        val += ", \"pos\": [{},{}]".format( xpos, ypos )
                    val += " }"
                    entries.append( "    {}".format( val ) )
                if nat == "landing-craft":
                    vo_types.append( ",\n".join( entries ) )
                else:
                    vo_types.append( "{}: {{\n{}\n}}".format(
                        jsonval(vo_type), ",\n".join( entries )
                    ) )
            vo_notes.append( "{}: {{\n{}\n}}".format(
                jsonval(nat), ",\n".join( vo_types )
            ) )
        print( "{{\n\n{}\n\n}}".format(
            ",\n\n".join( vo_notes )
        ), file=vo_notes_out )

    @staticmethod
    def _check_string( val, target ):
        """Check if a string matches a target."""
        if target.startswith( "^" ):
            return val.startswith( target[1:] )
        else:
            return val == target

    @staticmethod
    def _get_page_pos( pos ):
        """Return a X/Y position on the page."""
        return math.floor( pos[0] ), math.ceil( pos[1] )

# ---------------------------------------------------------------------

@click.command()
@click.argument( "pdf_file", nargs=1, type=click.Path(exists=True,dir_okay=False) )
@click.option( "--arg","args", multiple=True, help="Configuration parameter(s) (key=val)." )
@click.option( "--progress/--no-progress", is_flag=True, default=False, help="Log progress messages." )
@click.option( "--format","-f","output_fmt", default="json", type=click.Choice(["raw","text","json"]),
    help="Output format."
)
@click.option( "--save-targets","save_targets_fname", required=True, help="Where to save the extracted targets." )
@click.option( "--save-chapters","save_chapters_fname", required=True, help="Where to save the extracted chaopters." )
@click.option( "--save-footnotes","save_footnotes_fname", required=True, help="Where to save the extracted footnotes." )
@click.option( "--save-vo-notes","save_vo_notes_fname", required=True,
    help="Where to save the extracted vehicle/ordnance notes."
)
def main( pdf_file, args, progress, output_fmt,
  save_targets_fname, save_chapters_fname, save_footnotes_fname, save_vo_notes_fname
):
    """Extract content from the MMP eASLRB."""

    # initialize
    args = ExtractBase.parse_args( args, _DEFAULT_ARGS )

    # extract the content
    def log_msg( msg_type, msg ):
        if msg_type == "progress" and not progress:
            return
        log_msg_stderr( msg_type, msg )
    extract = ExtractContent( args, log_msg )
    extract.log_msg( "progress",  "Loading PDF: {}", pdf_file )
    with PdfDoc( pdf_file ) as pdf:
        extract.extract_content( pdf )

    # save the results
    with open( save_targets_fname, "w", encoding="utf-8" ) as targets_out, \
         open( save_chapters_fname, "w", encoding="utf-8" ) as chapters_out, \
         open( save_footnotes_fname, "w", encoding="utf-8" ) as footnotes_out, \
         open( save_vo_notes_fname, "w", encoding="utf-8" ) as vo_notes_out:
        getattr( extract, "save_as_"+output_fmt, )( targets_out, chapters_out, footnotes_out, vo_notes_out )

if __name__ == "__main__":
    main() #pylint: disable=no-value-for-parameter
