"""

"""

# ------------------------------------------------------------------------------
# External imports #-----------------------------------------------------------
from copy import copy
from collections import deque
import re

from os import linesep

# Internal imports #-----------------------------------------------------------
# ------------------------------------------------------------------------------#
from util.ast import *

# Internal imports #-----------------------------------------------------------
# ------------------------------------------------------------------------------#
u8neg = u"\u00AC"
u8and = u"\u2227"
u8or = u"\u2228"


# ------------------------------------------------------------------------------#


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

    def save_dimacs(self, output_file):
        out = []

        for k, v in self.variables.items():
            line = f"c {k} {v['desc']}"
            out.append(line)

        line = f"p cnf {len(self.variables)} {len(self.clauses)}"
        out.append(line)

        for clause in self.clauses:
            line = " ".join([str(x) for x in clause]) + " 0"
            out.append(line)

        out = linesep.join(out)

        with open(output_file, "w+") as file:
            file.write(out)
            file.write(linesep)


class FM():

    def __init__(self, root, ctcs=[], meta={}):
        self.meta = meta
        self.root = root
        self.features = self.enumerate_features()
        self.variables = self.features
        self.features2id = self.dict_features2id()
        self.ctcs = ctcs
        self.clauses = []
        self.ctcs_min = self.minify_ctcs()
        self.hcs = self.gen_hierarchy_constraints()

    def gen_hierarchy_constraints(self):

        features2id = self.features2id

        stack = deque()
        stack.append(self.root)

        hcs = []

        hcs.append(features2id[self.root.name])

        while stack:
            feature = stack.popleft()

            fid = features2id[feature.name]

            if not feature.has_or_group and not feature.has_alternative_group:
                for m in feature.mandatory_childs:
                    mid = features2id[m.name]
                    hcs.append(Iff(fid, mid))
                    self.clauses.append([fid, mid])

                    stack.append(m)

                for o in feature.optional_childs:
                    oid = features2id[o.name]
                    hcs.append(Implies(oid, fid))
                    self.clauses.append([oid, fid])

                    stack.append(o)

            else:
                acc = Not(fid)
                accl = [fid]

                for c in feature.grouped_childs:
                    stack.append(c)
                    cid = features2id[c.name]

                    hcs.append(Implies(cid, fid))
                    self.clauses.append([cid, fid])

                    acc = Or(cid, acc)
                    accl.append(cid)

                hcs.append(acc)
                self.clauses.append(accl)

                if feature.has_alternative_group:
                    for i, a in enumerate(feature.grouped_childs):
                        aid = features2id[a.name]

                        for b in feature.grouped_childs[i + 1:]:
                            bid = features2id[b.name]

                            # hcs.append(Or(Not(fid), Or(Not(aid), Not(bid))))
                            hcs.append(Or(Not(aid), Not(bid)))
                            self.clauses.append([fid, aid, bid])

        return hcs

    def enumerate_features(self):
        features = []
        stack = [self.root]

        while stack:
            feature = stack.pop(0)

            features.append(feature)
            stack.extend(feature.mandatory_childs)
            stack.extend(feature.optional_childs)
            stack.extend(feature.grouped_childs)

        return [(i + 1, x) for i, x in enumerate(features)]

    def dict_features2id(self):

        features2id = dict()

        for i, feature in self.features:
            features2id[feature.name] = i

        return features2id

    def minify_ctcs(self):

        features2id = self.features2id

        out = []

        for ctc in self.ctcs:
            ctc = copy(ctc)

            ctc, variables = self.substitute(ctc)

            out.append(ctc)
            self.clauses.append(variables)

        return out

    def get_no_variables(self):
        return len(self.features)

    def get_order(self):
        features2id = self.features2id

        root = self.root

        ordering = []

        for feature in root.grouped_childs:
            ordering.extend(self.get_sub_order(feature))

        ordering.append(features2id[root.name])

        for feature in root.mandatory_childs:
            ordering.extend(self.get_sub_order(feature))

        for feature in root.optional_childs:
            ordering.extend(self.get_sub_order(feature))

        return ordering

    def get_sub_order(self, node):

        ordering = []
        features2id = self.features2id

        for feature in node.grouped_childs:
            ordering.extend(self.get_sub_order(feature))

        ordering.append(features2id[node.name])

        for feature in node.mandatory_childs:
            ordering.extend(self.get_sub_order(feature))

        for feature in node.optional_childs:
            ordering.extend(self.get_sub_order(feature))

        return ordering

    def substitute(self, ctc):

        features2id = self.features2id
        variables = set()

        if type(ctc) == Not:
            if type(ctc.t) == str:
                ctc.t = features2id[ctc.t]
                variables.update([ctc.t])
            else:
                ctc.t, subvars = self.substitute(ctc.t)
                variables.update(subvars)

        else:
            if type(ctc.l) == str:
                ctc.l = features2id[ctc.l]
                variables.update([ctc.l])
            else:
                ctc.l, subvars = self.substitute(ctc.l)
                variables.update(subvars)

            if type(ctc.r) == str:
                ctc.r = features2id[ctc.r]
                variables.update([ctc.r])
            else:
                ctc.r, subvars = self.substitute(ctc.r)
                variables.update(subvars)

        return ctc, list(variables)


class Feature:

    def __init__(self, name):
        self.name = name
        self.mandatory_childs = []
        self.optional_childs = []
        self.grouped_childs = []
        self.has_alternative_group = False
        self.has_or_group = False

    def __str__(self):
        return f"({self.name}, {self.mandatory_childs}, {self.optional_childs}, {self.grouped_childs})"

    def __repr__(self):
        return f"({self.name}, {self.mandatory_childs}, {self.optional_childs}, {self.grouped_childs})"

    def add_mandatory_child(self, child):
        if self.has_alternative_group or self.has_or_group:
            raise AttributeError(f"{self.name} has grouped children, clashes with mandatory children")

        self.mandatory_childs.append(child)

    def add_optional_child(self, child):
        if self.has_alternative_group or self.has_or_group:
            raise AttributeError(f"{self.name} has grouped children, clashes with optional children")

        self.optional_childs.append(child)

    def add_alternative_child(self, child):
        if self.has_or_group:
            raise AttributeError(f"{self.name} has children in an or group, clashes with alternative children")

        self.has_alternative_group = True
        self.grouped_childs.append(child)

    def add_or_child(self, child):
        if self.has_alternative_group:
            raise AttributeError(f"{self.name} has children in an alternative group, clashes with or children")

        self.has_or_group = True
        self.grouped_childs.append(child)
