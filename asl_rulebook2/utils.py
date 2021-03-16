""" Miscellaneous utilities. """

import os
import pathlib
import tempfile
import re
import math
from io import StringIO
from html.parser import HTMLParser

# ---------------------------------------------------------------------

class TempFile:
    """Manage a temp file that can be closed while it's still being used."""

    def __init__( self, mode="wb", extn=None, encoding=None ):
        self.mode = mode
        self.extn = extn
        self.encoding = encoding
        self.temp_file = None
        self.name = None

    def open( self ):
        """Allocate a temp file."""
        if self.encoding:
            encoding = self.encoding
        else:
            encoding = "utf-8" if "b" not in self.mode else None
        assert self.temp_file is None
        self.temp_file = tempfile.NamedTemporaryFile(
            mode = self.mode,
            encoding = encoding,
            suffix = self.extn,
            delete = False
        )
        self.name = self.temp_file.name

    def close( self, delete ):
        """Close the temp file."""
        self.temp_file.close()
        if delete:
            os.unlink( self.temp_file.name )

    def write( self, data ):
        """Write data to the temp file."""
        self.temp_file.write( data )

    def __enter__( self ):
        """Enter the context manager."""
        self.open()
        return self

    def __exit__( self, exc_type, exc_val, exc_tb ):
        """Exit the context manager."""
        self.close( delete=True )

# ---------------------------------------------------------------------

def strip_html( val ):
    """Strip HTML."""

    if not val:
        return val

    buf = StringIO()
    class StripHtml( HTMLParser ):
        """Strip HTML."""
        def __init__( self ):
            super().__init__()
            self.strict = False
        def handle_data( self, data ):
            buf.write( data )
        def error( self, message ):
            pass

    # strip HTML
    html_stripper = StripHtml()
    html_stripper.feed( val )
    return buf.getvalue()

# ---------------------------------------------------------------------

def fixup_text( val ):
    """Fixup special characters in a string."""

    # fixup smart quotes, dashes and other non-ASCII characters
    def replace_chars( val, ch, targets ):
        for target in targets:
            val = val.replace( target, ch )
        return val
    val = replace_chars( val, '"', [ "\u00ab", "\u00bb", "\u201c", "\u201d", "\u201e", "\u201f", "\u02dd" ] )
    val = replace_chars( val, "'", [ "\u2018", "\u2019", "\u201a", "\u201b", "\u2039", "\u203a" ] )
    val = replace_chars( val, " - ", [ "\u2013", "\u2014" ] )
    val = replace_chars( val, "-", [ "\u2022" ] ) # nb: bullet
    val = replace_chars( val, "&le;", [ "\u2264" ] )
    val = replace_chars( val, "&ge;", [ "\u2265" ] )
    val = replace_chars( val, "&#9651;", [ "\u2206" ] ) # nb: "no leadership DRM" triangle
    val = replace_chars( val, "&reg;", [ "\u00ae" ] ) # nb: circled R
    val = replace_chars( val, "&deg;", [ "\u00b0" ] ) # nb: degree sign
    val = replace_chars( val, "&auml;", [ "\u00e4" ] )

    # replace fractions with their corresponding HTML entity
    for frac in [ (1,2), (1,3), (2,3), (3,8), (5,8) ]:
        val = re.sub(
            r"\b{}/{}(?=(\"| MF| MP))".format( frac[0], frac[1] ),
            "&frac{}{};".format( frac[0], frac[1] ),
            val
        )
    return val

def extract_parens_content( val ):
    """Extract content in parenthesis (including nested parentheses)."""
    assert val[0] == "("
    nesting = 0
    for pos, ch in enumerate(val):
        if ch == "(":
            nesting += 1
        elif ch == ")":
            nesting -= 1
            if nesting <= 0:
                return val[1:pos], val[pos+1:]
    return val # nb: if we get here, we have unclosed parantheses :-/

# ---------------------------------------------------------------------

def parse_page_numbers( val, offset=0 ):
    """Parse a list of page numbers.

    We recognize a list of page numbers, and/or ranges e.g. 1,2,5-9,13.
    """
    vals = set()
    if val:
        for v in str(val).split( "," ):
            mo = re.search( r"^(\d+)-(\d+)$", v )
            if mo:
                vals.update( range( int(mo.group(1)), int(mo.group(2))+1 ) )
            else:
                vals.add( int(v) )
    return [ v+offset for v in vals ]

# ---------------------------------------------------------------------

def jsonval( val ):
    """Return a value in a JSON-safe format."""
    if val is None:
        return "null"
    if isinstance( val, int ):
        return val
    if isinstance( val, list ):
        if not val:
            return "[]"
        vals = [ jsonval(v) for v in val ]
        return "[ {} ]".format( ", ".join( vals ) )
    if isinstance( val, str ):
        val = "".join(
            ch if 32 <= ord(ch) <= 127 else r"\u{:04x}".format(ord(ch))
            for ch in val
        )
        return '"{}"'.format( val.replace('"',r'\"') )
    assert False, "Unknown JSON data type: {}".format( type(val) )
    return '"???"'

def change_extn( fname, extn ):
    """Change a filename's extension."""
    return pathlib.Path( fname ).with_suffix( extn )

def append_text( buf, new ):
    """Append text to a buffer."""
    if buf:
        if buf[-1] == "-":
            return buf[:-1] + new # nb: join hyphenated words
        if buf[-1] != "/":
            buf += " "
    return buf + new

def plural( n, name1, name2 ):
    """Return the singular/plural form of a string."""
    return "{} {}".format( n, name1 if n == 1 else name2 )

def remove_quotes( val ):
    """Remove enclosing quotes from a string."""
    if val[0] in ('"',"'") and val[-1] == val[0]:
        val = val[1:-1]
    return val

def remove_trailing( val, ch ):
    """Remove a trailing character from a string."""
    if val.endswith( ch ):
        val = val[:-1]
    return val

def roundf( val, ndigits ):
    """Round a floating-point value."""
    pow10 = math.pow( 10, ndigits )
    return int( pow10 * val + 0.5 ) / pow10
