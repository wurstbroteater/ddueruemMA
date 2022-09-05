from os import path

from . import *
from util import plugin

plugins = plugin.filter([globals()[x] for x in dir()], ["parse", "parses"])


def by_filename(filename):
    _, extension = path.splitext(filename)

    for _, parser in plugins.items():
        if extension.lower() in parser.parses:
            return parser
