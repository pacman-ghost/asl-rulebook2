""" Miscellaneous utilities. """

import re

# ---------------------------------------------------------------------

def parse_page_numbers( val ):
    """Parse a list of page numbers.

    We recognize a list of page numbers, and/or ranges e.g. 1,2,5-9,13.
    """
    vals = set()
    if val:
        for v in val.split( "," ):
            mo = re.search( r"^(\d+)-(\d+)$", v )
            if mo:
                vals.update( range( int(mo.group(1)), int(mo.group(2))+1 ) )
            else:
                vals.add( int(v) )
    return vals
