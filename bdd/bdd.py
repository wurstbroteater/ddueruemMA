import multiprocessing
from os import path

from . import *
import config

from svo import svo
from svo.random import asc_by_id

from cli import cli
from util import plugin, util

from util.util import tic, toc, peek

from collections import deque
from copy import copy

plugins = plugin.filter([globals()[x] for x in dir()], [])


def by_stub(stub):
    return plugins.get(stub.lower())


def compile_threaded(lib, dvo, expr, order, log, meta):
    manager = BDD(lib, dvo)
    manager.build_from_CNF(expr, order, log, meta)


def compile(compiler, exprs, context):
    stats = []
    context = context["settings"]
    dvos = context["dvo"]

    for expr in exprs:
        # print(expr)
        # info_compile(expr, compiler, context)

        if not hasattr(expr, "orders"):
            cli.say("No precomputed variable orders found, taking order from input.")
            order = asc_by_id(expr)

            expr.orders = {}
            expr.orders["none"] = [order]

        for svo_stub, orders in expr.orders.items():
            print(f"Using variable orders computed with", svo_stub)

            if isinstance(orders, list):
                pass
            else:
                orders = svo.parse_orders(orders)

            for order in orders:
                for dvo in dvos:
                    print(f"Compiling with DVO set to:", dvo)

                    corrupted = False
                    if context["lib_t"] <= 0:
                        log = []
                        meta = dict()
                        meta.update(expr.meta)

                        manager = BDD(compiler, dvo)
                        manager.build_from_CNF(expr, order, log, meta)
                    else:
                        pmanager = multiprocessing.Manager()

                        log = pmanager.list()
                        meta = pmanager.dict()

                        meta.update(expr.meta)

                        p = multiprocessing.Process(target=compile_threaded,
                                                    args=(compiler, dvo, expr, order, log, meta))

                        p.start()
                        p.join(context["lib_t"])

                        if p.is_alive():
                            corrupted = True
                            p.terminate()
                            p.kill()

                        bdd_log = list(log)
                        # print(bdd_log)

                        if corrupted:
                            meta["time-bdd-build"] = context["lib_t"]

                    cli.say('Meta', meta)
                    cli.say("BDD bootstrap time:", cli.highlight(meta["time-bdd-bootstrap"]))

                    if corrupted:
                        cli.say(f"BDD compilation reached timeout.")
                    else:
                        cli.say("BDD building time:", cli.highlight(meta["time-bdd-build"]))

                    meta = dict(meta)
                    meta["svo"] = svo_stub

                    stats.append(meta)
                    cli.say()

    return stats


class BDD():

    def __init__(self, lib, dvo=None):
        self.bdd = None
        self.lib = lib
        self.mgr = lib.Manager().init()

        if dvo:
            self.mgr.enable_dvo(dvo)

        self.meta = {}

    def bootstrap(self, expr, order=None):
        lib = self.lib
        mgr = self.mgr

        if lib.requires_variable_count_advertisement:
            mgr.set_no_variables(expr.get_no_variables())

        if order:
            mgr.set_order(order)

    def build_from_CNF(self, expr, order, log, meta):
        bdd = self.bdd
        lib = self.lib
        mgr = self.mgr

        meta["bdd-lib"] = self.lib.STUB
        meta["bdd-dvo"] = mgr.get_dvo()

        tic()

        if self.bdd is None:
            self.bootstrap(expr, order)
            self.bdd = mgr.one_()

        meta["time-bdd-bootstrap"] = toc()
        meta["bdd-build-timeout"] = True

        clauses = deque(list(copy(expr.clauses)))

        n = len(clauses)
        i = 1

        tic()

        bdd = mgr.one_()

        while clauses:
            clause = clauses.popleft()
            clause_bdd = mgr.zero_()

            for x in clause:

                y = mgr.to_index(x)

                if x < 0:
                    clause_bdd = mgr.or_(clause_bdd, mgr.nithvar_(y))
                else:
                    clause_bdd = mgr.or_(clause_bdd, mgr.ithvar_(y))

            bdd = mgr.and_(bdd, clause_bdd)

            time_total = peek()
            time_dvo = mgr.dvo_time()
            time_bdd = time_total - time_dvo
            log.append((i, str(clause), time_total, time_bdd, time_dvo))
            i += 1

            inner_order = mgr.get_order(bdd)

            if inner_order != order:
                order = inner_order

        meta["time-bdd-build"] = toc()
        # print(expr.meta["time-bdd-build"])

        # cli.say("#SAT:", cli.highlight(mgr.ssat(bdd, expr.get_no_variables())))

        meta["bdd-build-timeout"] = False
        log = list(log)
        _, _, _, _, dvo_time = log[-1]
        meta["time-dvo"] = dvo_time
        self.bdd = bdd


def info_compile(expr, compiler, context):
    cli.say("Compiling", cli.highlight(expr.meta["input-filename"]))
    print(f"\t\u221f SVO:", context["svo"].STUB)
    print(f"\t\u221f LIB:", compiler.FULL)
    print(f"\t\u221f DVO:", context["dvo"])
    print()
