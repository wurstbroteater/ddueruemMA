from abc import ABC
from ctypes import CDLL
from os import path
import multiprocessing
# -----------------------------------------------------------------------------#

from cli import cli


# -----------------------------------------------------------------------------#

class Manager(ABC):

    # def __init__(self, no_variables = None, order = None, dvo = None):
    #     self.init()

    #     if dvo:
    #         self.enable_dvo(dvo)
    #     else:
    #         self.disable_dvo()

    #     self.nodes = dict()

    #     if lib.requires_variable_count_advertisement:
    #         if no_variables is None:
    #             raise ValueError(f"{self.get_name()} requires the number of variables to be advertised.")

    #         self.set_no_variables(no_variables)

    #     if order:
    #         self.set_order(order)

    def load_lib(self, shared_lib, hint_install):
        if not path.exists(shared_lib):
            cli.error(cli.highlight(shared_lib, "e"), "not found, please install first with",
                      cli.highlight(hint_install, "e"))
        else:
            return CDLL(f"./{shared_lib}")

    # ---- Initialization, Setup, Destruction---------------------------------------#

    def init(self):
        raise NotImplementedError()

    def exit(self):
        raise NotImplementedError()

    def set_no_variables(self, no_variables):
        raise NotImplementedError()

    # ---- Constants ---------------------------------------------------------------#

    def zero_(self):
        raise NotImplementedError()

    def one_(self):
        raise NotImplementedError()

    # ---- Variables ---------------------------------------------------------------#

    def ithvar_(self, varid):
        raise NotImplementedError()

    def nithvar_(self, varid):
        raise NotImplementedError()

    # ---- Unary Operators ---------------------------------------------------------#

    def not_(self, obj):
        raise NotImplementedError()

    # ---- Binary Operators --------------------------------------------------------#

    def and_(self, lhs, rhs, free_factors=True):
        raise NotImplementedError()

    def or_(self, lhs, rhs, free_factors=True):
        raise NotImplementedError()

    def xor_(self, lhs, rhs, free_factors=True):
        raise NotImplementedError()

    # ---- Ternary Operators -------------------------------------------------------#

    def ite_(self, a, b, c, free_factors=True):
        raise NotImplementedError()

    # ---- Query -------------------------------------------------------------------#

    def size_(self, obj):
        raise NotImplementedError()

    def get_order(self, obj):
        raise NotImplementedError()

    # ---- Utility -----------------------------------------------------------------#

    def addref_(self, obj):
        raise NotImplementedError()

    def delref_(self, obj):
        raise NotImplementedError()

    # ---- Variable Ordering -------------------------------------------------------#

    def enable_dvo(self, dvo_id):
        raise NotImplementedError()

    def disable_dvo(self, dvo_id):
        raise NotImplementedError()

    def dvo_once(self, dvo_id="lib-default"):
        raise NotImplementedError()

    def set_order(self, order):
        raise NotImplementedError()

    # ---- UI ----------------------------------------------------------------------#

    def say(self, msg):
        cli.say(msg, origin=self.get_name())

    def say_hi(self):
        self.say("Initialized")

    def say_bye(self):
        self.say("Shutdown")

    # ---- IO ----------------------------------------------------------------------#

    def dump(self, bdd, filename):
        raise NotImplementedError()

    def dump_dot(self, bdd, filename):
        raise NotImplementedError()
