"""

"""

# ------------------------------------------------------------------------------
# External imports #-----------------------------------------------------------
from os import path
from pathlib import Path
from svo import svo

# ------------------------------------------------------------------------------
# Internal imports #-----------------------------------------------------------
from util.util import hash_hex

# ------------------------------------------------------------------------------
# Plugin Properties #----------------------------------------------------------


STUB = "order"

name = "Order(s) Parser"
parses = [".order", ".orders"]


def parse(file):
    out = []
    o = svo.parse_orders(file)
    for nested in o:
        out.append(nested)
    return [out, {"input-filename": path.basename(file), "input-filehash": hash_hex(file)}]
