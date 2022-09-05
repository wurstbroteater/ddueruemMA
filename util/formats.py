from copy import copy
from collections import deque
import re

# ------------------------------------------------------------------------------#

u8neg = u"\u00AC"
u8and = u"\u2227"
u8or = u"\u2228"


class Expression:

    def __init__(self, clauses, variables={}, meta={}):
        self.meta = meta
        self.clauses = clauses
        self.variables = variables

    def get_meta(self):
        return self.meta

    def get_no_variables(self):
        return len(self.variables)


class CNF(Expression):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stub = "CNF"

    def __str__(self):
        out = []

        for clause in self.clauses:
            h = []
            for x in clause:
                if x < 0:
                    h.append(f"{u8neg}{abs(x)}")
                else:
                    h.append(str(x))

            h = f" {u8or} ".join(h)
            out.append(f"({h})")

        return (f" {u8and} ".join(out)).strip()

    def verbose(self):
        out = str(self)

        for k, v in self.variables.items():
            out = re.sub(str(k), v["desc"], out)

        return out
