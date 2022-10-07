from ctypes import CDLL, Structure, POINTER, c_uint, c_double, c_ulong, byref, c_int
from enum import IntEnum
import os
import re
import sys

import subprocess

from . import manager
import config

from util.util import ms2s

STUB        = "buddy"
FULL        = "BuDDy 2.4"

url         = "https://sourceforge.net/projects/buddy/files/buddy/BuDDy%202.4/buddy-2.4.tar.gz/download"
archive     = "buddy-2.4.tar.gz"
archive_md5 = "3b59cb073bcb3f26efdb851d617ef2ed"
sources_dir = f"{config.DIR_ARCHIVES}/buddy-2.4"

shared_lib  = "libbuddy.so"

configure_settings = "CFLAGS=-fPIC -std=c99"

make_append = f"BUDDY_SRC={sources_dir}/src"

hint_install = "./ddueruem.py --install buddy"

has_zero_based_indizes = True
requires_variable_count_advertisement = True


class DVO(IntEnum):
    OFF             = 0
    
    WIN2            = 1
    WIN2C           = 2

    SIFT            = 3
    SIFTC           = 4

    WIN3            = 5
    WIN3C           = 6

    random          = 7

    def __str__(self):
        return self.name


#---- Setup and CDLL Helpers --------------------------------------------------#

def configure():
    proc = subprocess.run(['./configure', configure_settings], cwd = sources_dir, capture_output=True)
    ec = proc.returncode
    stdout = proc.stdout.decode("utf-8")
    stderr = proc.stderr.decode("utf-8")

    return ec, stdout, stderr


def install_post():
    pass


def declare(f, argtypes, restype = None):
    x = f
    x.argtypes = argtypes

    if restype:
        x.restype = restype

    return x


def format2file(filename, meta = {}):        
    with open(filename, "r") as file:
        content = file.read()

    lines = re.split("[\n\r]",content)

    n_nodes, n_vars = re.split(r"\s+", lines[0].strip())
    var2order = [int(x) for x in re.split(r"\s+", lines[1].strip())]

    order = [0 for _ in range(0, len(var2order))]
    for i,x in enumerate(var2order):
        order[x] = i+1

    nodes = {}
    root = None

    for line in lines[2:]:
        m = re.match(r"(?P<id>\d+) (?P<var>\d+) (?P<low>\d+) (?P<high>\d+)", line)
        if m:
            nodes[int(m["id"])] = (int(m["var"]), int(m["low"]), int(m["high"]))
            root = int(m["id"])

    ids = sorted([x for x in nodes.keys()])

    content = []
    meta["n_nodes"] = n_nodes
    meta["root"] = f"0:{root}"
    meta["order"] = ",".join([str(x) for x in order])

    if meta:
        for k, v in meta.items():
            content.append(f"{k}:{v}")

    content = sorted(content)

    content.append("----")

    for i in ids:
        var, low, high = nodes[i]
        content.append(f"{i} {var} 0:{low} 0:{high}")

    with open(filename, "w") as file:
        file.write(f"{os.linesep}".join(content))
        file.write(os.linesep)


class Manager(manager.Manager):
    
    def init(self):
        buddy = self.load_lib(shared_lib, hint_install)

        buddy.bdd_init(1000000, 100000)
        buddy.bdd_setminfreenodes(33)
        buddy.bdd_setmaxincrease(c_int(1000000))

        self.buddy = buddy
        self.dvo = DVO["OFF"]

        return self


    def exit(self):
        self.buddy.bdd_done()


    def set_no_variables(self, no_variables):
        self.buddy.bdd_setvarnum(no_variables)

#---- Constants ---------------------------------------------------------------#

    def zero_(self):
        return self.buddy.bdd_false() 

    def one_(self):
        return self.buddy.bdd_true()

#---- Variables ---------------------------------------------------------------#

    def ithvar_(self, varid):
        return self.buddy.bdd_ithvar(varid)

    def nithvar_(self, varid):
        return self.buddy.bdd_nithvar(varid)

#---- Unary Operators ---------------------------------------------------------#

    def not_(self, obj):
        return self.buddy.bdd_not(obj)

#---- Binary Operators --------------------------------------------------------#
   
    def and_(self, lhs, rhs, free_factors = True):

        out = self.buddy.bdd_addref(self.buddy.bdd_and(lhs, rhs))

        if free_factors:
            self.delref_(lhs)
            self.delref_(rhs)

        return out

    def or_(self, lhs, rhs, free_factors = True):
        out = self.buddy.bdd_addref(self.buddy.bdd_or(lhs, rhs))

        if free_factors:
            self.delref_(lhs)
            self.delref_(rhs)

        return out

    def xor_(self, lhs, rhs, free_factors = True):
        out = self.buddy.bdd_addref(self.buddy.bdd_xor(lhs, rhs))

        if free_factors:
            self.delref_(lhs)
            self.delref_(rhs)

        return out

#---- Ternary Operators ------------------------------------------------------#

    def ite_(self, a, b, c, free_factors = True):
        pass

#---- Utility -----------------------------------------------------------------#
    
    def enable_dvo(self, dvo):
        self.dvo = DVO[dvo.upper()]

        self.buddy.bdd_autoreorder(self.dvo)
        self.buddy.bdd_reorder_verbose(1)
        self.buddy.bdd_enable_reorder()
        self.buddy.bdd_autoreorder(self.dvo)


    def disable_dvo(self):
        self.dvo = DVO["OFF"]
        self.buddy.bdd_autoreorder(self.dvo)
        self.buddy.bdd_disable_reorder()


    def get_dvo(self):
        return self.dvo.name


    def set_order(self, order):
        order_min = min(order)

        if order_min > 0:
            order = [x - order_min for x in order]   

        arr = (c_uint * len(order))(*order)

        self.buddy.bdd_setvarorder(arr)


    def to_index(self, n):
        return abs(n) - 1


    def addref_(self, obj):
        pass

    def delref_(self, obj):
        self.buddy.bdd_delref(obj)

    def dump(self, bdd, filename, meta = {}, **kwargs):
        self.buddy.bdd_fnsave(c_char_p(filename.encode("utf-8")), bdd)
        format2file(filename, meta = meta)


    def get_name(self):
        return FULL
