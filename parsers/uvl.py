"""

"""

# ------------------------------------------------------------------------------
# External imports #-----------------------------------------------------------
from collections import deque
from os import path
import re

# ------------------------------------------------------------------------------
# Internal imports #-----------------------------------------------------------
from util.ast import *
from util.exceptions import MalformedInputException
from util.formats import FM, Feature
from util.util import hash_hex

# ------------------------------------------------------------------------------
# Plugin Properties #----------------------------------------------------------
STUB = "uvl"

name = "UVL Parser"
parses = [".uvl"]


# ------------------------------------------------------------------------------


def parse(filename):
    re_empty = re.compile(r"^[\s]*$")
    re_indent = re.compile(r"[\s]*")
    re_content = re.compile(r"^(?P<indent>[\s\t]+)?(?P<content>(\w|\d|[+-/])+)[^\n\r]*[\n\r]$")

    with open(filename) as file:
        raw = file.readlines()

    ctc_start = -1

    feature_diagram = []

    for i, line in enumerate(raw):

        if re_empty.match(line):
            continue

        if line.startswith("namespace"):
            continue

        if line.startswith("features"):
            continue

        if line.startswith("constraints"):
            ctc_start = i
            break

        if m := re_content.match(line):

            indent_size = 0

            if m["indent"]:
                mi = re_indent.match(m["indent"])
                indent_size = mi.end() - mi.start()

            feature_diagram.append((indent_size, m["content"]))

        else:
            raise MalformedInputException(f"Could not parse line {i} of input, beeing: \"{line}\"")

    for i, entry in enumerate(feature_diagram):
        indent, content = entry

        if content in ["mandatory", "optional", "alternative", "or"]:
            continue

        feature_diagram[i] = (indent, Feature(content))

    indent, root = feature_diagram.pop(0)
    root = populate_feature(indent, root, feature_diagram)

    ctcs = []
    if ctc_start >= 0:
        ctcs = raw[ctc_start + 1:]
        ctcs = [x.strip() for x in ctcs]

        for i, ctc in enumerate(ctcs):
            ctcs[i] = parse_ctc(ctc)

    return FM(root, ctcs)


def populate_feature(indent_major, current, list):
    t = None

    while list and list[0][0] > indent_major:
        indent, content = list[0]

        if t is None or indent == indent_major + 1:
            indent, t = list.pop(0)
            t = t.lower()

            if indent != indent_major + 1:
                raise AttributeError("Indendation mismatch")

            if t not in ["mandatory", "optional", "or", "alternative"]:
                raise AttributeError(f"Feature type unknown ({t})")

        elif indent == indent_major + 2:
            indent, feature = list.pop(0)

            if isinstance(feature, str):
                raise AttributeError("Expected feature but found {feature}")

            feature = populate_feature(indent, feature, list)

            if t == "mandatory":
                current.add_mandatory_child(feature)
            elif t == "optional":
                current.add_optional_child(feature)
            elif t == "or":
                current.add_or_child(feature)
            elif t == "alternative":
                current.add_alternative_child(feature)

    return current


def parse_ctc(ctc):
    """ not > and > or > implies > iff """
    level = 0
    current = ""

    elements = deque()

    for char in ctc:

        if current.strip().endswith("<=>"):
            elements.append((level, current.strip()[:-3].strip()))
            elements.append((level, "<=>"))
            current = ""

        if current.strip().endswith("=>"):
            elements.append((level, current.strip()[:-2].strip()))
            elements.append((level, "=>"))
            current = ""

        if char == "!":
            if c := current.strip():
                elements.append((level, c))

            elements.append((level, "!"))
            current = ""

        elif char == "&":
            if c := current.strip():
                elements.append((level, c))

            elements.append((level, "&"))
            current = ""

        elif char == "|":
            if c := current.strip():
                elements.append((level, c))

            elements.append((level, "|"))
            current = ""

        elif char == "(":
            if c := current.strip():
                elements.append((level, c))

            level += 1
            current = ""
        elif char == ")":
            if c := current.strip():
                elements.append((level, c))

            level -= 1
            current = ""
        else:
            current += char

    if c := current.strip():
        elements.append((level, c))

    if len(elements) > 1:
        elements = replace_nots(elements)
        elements = replace_biops(elements)

    return elements[0][1]


def replace_nots(elements):
    out = deque()

    while elements:

        l, t = elements.popleft()

        if t != "!":
            out.append((l, t))
            continue

        scope = deque()

        while elements:
            if (l2 := elements[0][0]) >= l:
                if l2 == l and len(scope) > 0:
                    break
                else:
                    scope.append(elements.popleft())
            else:
                break

        if len(scope) > 1:
            scope = replace_nots(scope)
            scope = replace_biops(scope)

        scope = scope[0][1]
        out.append((l, Not(scope)))

    return out


def wrap_biop(op, lhs, rhs):
    if len(lhs) > 1:
        lhs = replace_nots(lhs)
        lhs = replace_biops(lhs)

    lhs = lhs[0][1]

    if len(rhs) > 1:
        rhs = replace_nots(rhs)
        rhs = replace_biops(rhs)

    rhs = rhs[0][1]

    if op == "&":
        return And(lhs, rhs)
    elif op == "|":
        return Or(lhs, rhs)
    elif op == "=>":
        return Implies(lhs, rhs)
    elif op == "<=>":
        return Iff(lhs, rhs)


def replace_biops(elements):
    for op in ["<=>", "=>", "|", "&"]:
        out = deque()

        collecting = False
        op_l = -1

        lhs = deque()
        rhs = deque()

        for i, (l, t) in enumerate(elements):
            if collecting:
                if l < op_l:
                    out.append((l, wrap_biop(op, lhs, rhs)))
                    lhs = deque()
                    rhs = deque()
                    collecting = False
                else:
                    rhs.append((l, t))

                continue

            if t != op:
                out.append((l, t))
                continue

            while out:
                l2, t2 = out[-1]

                if l2 < l:
                    break

                out.pop()
                lhs.insert(0, (l2, t2))

            collecting = True
            op_l = l

        if collecting:
            out.append((l, wrap_biop(op, lhs, rhs)))

        elements = out

    return out
