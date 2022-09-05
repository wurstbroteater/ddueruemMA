"""
This file provides default configuration values.
"""

# ------------------------------------------------------------------------------
# External imports #-----------------------------------------------------------
from os import path

# ------------------------------------------------------------------------------


# Directories
DIR_ROOT = "/tmp/ddueruem"
DIR_ARCHIVES = path.join(DIR_ROOT, "archives")
DIR_CACHE = path.join(DIR_ROOT, "cache")
DIR_TOOLS = path.join(DIR_ROOT, "tools")
DIR_OUT = path.join(DIR_ROOT, "out")

# Command-Line Interface
DEBUG = True
SILENT = False
