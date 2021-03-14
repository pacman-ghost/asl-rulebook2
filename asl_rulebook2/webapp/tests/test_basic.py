""" Test basic functionality. """

from asl_rulebook2.webapp.tests.utils import init_webapp

# ---------------------------------------------------------------------

def test_hello( webapp, webdriver ):
    """Test basic functionality."""

    init_webapp( webapp, webdriver )
