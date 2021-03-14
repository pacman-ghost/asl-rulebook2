""" Global variables. """

from asl_rulebook2.webapp import app
from asl_rulebook2.webapp.config.constants import APP_NAME, APP_VERSION

cleanup_handlers = []

# ---------------------------------------------------------------------

@app.context_processor
def inject_template_params():
    """Inject template parameters into Jinja2."""
    web_debug = app.config.get( "WEB_DEBUG" )
    return {
        "APP_NAME": APP_NAME,
        "APP_VERSION": APP_VERSION,
        "WEB_DEBUG": web_debug,
        "WEB_DEBUG_MIN": "" if web_debug else ".min",
    }
