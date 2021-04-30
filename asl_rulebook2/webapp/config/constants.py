""" Application constants. """

import os

APP_NAME = "ASL Rulebook 2"
APP_VERSION = "v0.1" # nb: also update setup.py
APP_DESCRIPTION = "Search engine for the ASL Rulebook."

BASE_DIR = os.path.abspath( os.path.join( os.path.dirname(__file__), ".." ) )
CONFIG_DIR = os.path.join( BASE_DIR, "config" )
