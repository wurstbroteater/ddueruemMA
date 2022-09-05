#!/usr/bin/env python3

"""

"""

# ------------------------------------------------------------------------------
# External imports #-----------------------------------------------------------
import os
from os import path

import sys

# ------------------------------------------------------------------------------
# Internal imports #-----------------------------------------------------------
import config
from cli import cli, argparser

from parsers import parsers
from svo import svo


# ------------------------------------------------------------------------------


def main():
    bootstrap()

    args = sys.argv
    cli.debug(args)
    files, actions = argparser.parse(args)

    cli.debug("files", files)
    cli.debug("actions", actions)

    exprs = []

    for file in files:
        parser = parsers.by_filename(file)
        expr = parser.parse(file)
        exprs.append(expr)

    cli.debug("exprs", exprs)

    if "SVO" in actions:
        cli.say("Computing static variable orders...")
        for expr in exprs:
            svo.compute(expr, actions["SVO"])
        cli.say("Finished static variable ordering.")


def bootstrap():
    # Verify existence or create directories
    dirs = [config.DIR_ROOT, config.DIR_ARCHIVES, config.DIR_CACHE, config.DIR_TOOLS, config.DIR_OUT]

    for dir in dirs:
        verify_or_create_dir(dir)


def verify_or_create_dir(dir):
    """Creates the directory `dir` if it does not already exist."""

    if not path.exists(dir):
        # cli.debug("Directory", cli.highlight(dir), "does not exist, creating")

        try:
            os.mkdir(dir)
        except OSError as ose:
            cli.error("error_create_directory_failed", cli.highlight(dir))
    else:
        pass
        # cli.debug("Verified existence of directory", cli.highlight(dir))


if __name__ == '__main__':
    main()
