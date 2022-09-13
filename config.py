"""
This file provides default configuration values.
"""

# ------------------------------------------------------------------------------
# External imports #-----------------------------------------------------------
from os import path
import pathlib
# ------------------------------------------------------------------------------


# Directories
#ROOT = "/home/eric/Uni/MA/ddueruemMA"
ROOT = str(pathlib.Path(__file__).parent)
DIR_ROOT = path.join(ROOT, "parsed")
DIR_ARCHIVES = path.join(DIR_ROOT, "archives")
DIR_CACHE = path.join(DIR_ROOT, "cache")
DIR_TOOLS = path.join(DIR_ROOT, "tools")
DIR_OUT = path.join(DIR_ROOT, "out")

# Command-Line Interface
DEBUG = False
SILENT = False
