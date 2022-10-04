"""

"""

# ------------------------------------------------------------------------------
# External imports #-----------------------------------------------------------
from pathlib import Path
# ------------------------------------------------------------------------------
# Internal imports #-----------------------------------------------------------
from util.util import hash_hex
from svo import svo

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
    return [out, {"input-filename": Path(file), "input-filehash": hash_hex(file)}]
