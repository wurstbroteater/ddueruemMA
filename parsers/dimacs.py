"""

"""

# ------------------------------------------------------------------------------
# External imports #-----------------------------------------------------------
from os import path
import re

# ------------------------------------------------------------------------------
# Internal imports #-----------------------------------------------------------
from util.exceptions import MalformedInputException
from util.formats import CNF
from util.util import hash_hex

# ------------------------------------------------------------------------------
# Plugin Properties #----------------------------------------------------------
STUB = "dimacs"

name = "DIMACS Parser"
parses = [".dimacs", ".cnf"]

# ------------------------------------------------------------------------------
# RegEx Patterns #-------------------------------------------------------------
P_comment = re.compile(r"c\s+(?P<var_id>\d+)[^\s]*\s+(?P<var_name>.+)$")
P_descriptor = re.compile(r"p\s+([cC][nN][fF])\s+(?P<n_variables>\d+)\s+(?P<n_clauses>\d+)\s*$")


# ------------------------------------------------------------------------------


def parse(filename, remove_tautologies=True):
    n_variables = None
    n_clauses = None
    variables = {}

    ext2int = {}

    clauses_raw = []
    clauses_clean = []

    var_id_int = 1

    passed_descriptor = False

    meta = {}

    meta["input-filename"] = path.basename(filename)
    meta["input-filepath"] = filename
    meta["input-filehash"] = hash_hex(filename)

    with open(filename) as file:
        for line in file.readlines():
            if m := P_comment.match(line):
                if passed_descriptor:
                    raise MalformedInputException("context comments after descriptor in DIMACS")

                var_id_ext = int(m["var_id"])
                var_name = m["var_name"]

                variables[var_id_int] = {
                    "ID": var_id_ext,
                    "desc": var_name
                }

                ext2int[var_id_ext] = var_id_int
                var_id_int += 1

            elif m := P_descriptor.match(line):
                if passed_descriptor:
                    raise MalformedInputException("Multiple p-lines in DIMACS")
                passed_descriptor = True

                n_variables = int(m["n_variables"])
                n_clauses = int(m["n_clauses"])

            else:
                if not passed_descriptor:
                    raise MalformedInputException(f"p-line missing in DIMACS ({filename})")

                parts = re.split(r"[\s]+", line)
                parts = [int(x) for x in parts if x != ""]

                if parts[-1] != 0:
                    raise MalformedInputException("Last value in DIMACS entry is not a zero")

                parts = parts[:-1]
                clauses_raw.append(parts)

    cache = dict()

    for clause in clauses_raw:
        clause = sorted(clause, key=lambda x: abs(x))
        clause = [ext2int[x] if x >= 0 else -ext2int[abs(x)] for x in clause]

        if str(clause) in cache:
            continue

        if (l := [(x, y) for (x, y) in zip(clause, clause[1:]) if abs(x) == abs(y)]):
            continue

        clauses_clean.append(clause)
        cache[str(clause)] = ()

    return CNF(clauses_clean, variables, meta)
