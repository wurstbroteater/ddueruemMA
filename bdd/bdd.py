import multiprocessing
import os.path
from os import path
from pathlib import Path

import traceback

from . import *

import config

from svo import svo
from svo.random import asc_by_id

from cli import cli
from util import plugin, jinja_renderer

from util.util import tic, toc, timestamp, peek

from collections import deque
from copy import copy

from pebble import ProcessPool
from concurrent.futures import TimeoutError

import time

plugins = plugin.filter([globals()[x] for x in dir()], [])
manager = multiprocessing.Manager()


def by_stub(stub):
    return plugins.get(stub.lower())


def compile_threaded(lib, dvo, expr, order, meta, dump=False):
    lib = by_stub(lib)

    bdd_manager = BDD(lib, dvo)
    out = bdd_manager.build_from_CNF(expr, order, meta)

    if dump:
        model_name = Path(expr.meta['input-filepath']).name.replace('.xml', '').replace('_DIMACS.dimacs', '')
        filepath = str(Path(config.DIR_OUT + f'{os.path.sep}{model_name}-{lib.STUB}-dump.log'))
        bdd_manager.dump(expr, filepath, out)

    return out


def compile(compiler, exprs, context):
    stats = []

    stat_file = None

    context = context["settings"]
    dump = context["dump"]
    dvos = context["dvo"]
    lib_t = context["lib_t"]

    for expr in exprs:
        if type(expr) == dict:
            pass
        elif not hasattr(expr, 'orders'):
            cli.say("No precomputed variable orders found, taking order from input.")
            order = asc_by_id(expr)
            expr.orders = {}
            expr.orders["none"] = [order]

        for svo_stub, orders in expr.orders.items():
            print("Using variable orders computed with", svo_stub)
            model_name = Path(expr.meta['input-filepath']).name.replace('.xml', '').replace('_DIMACS.dimacs', '')
            stat_file = path.join(config.DIR_OUT, f"{model_name}-bdd-{compiler.STUB}-{svo_stub}.csv")

            if isinstance(orders, list):
                pass
            else:
                orders = svo.parse_orders(orders)

            runs = []

            with ProcessPool(max_tasks=1) as pool:
                for order in orders:
                    for dvo in dvos:

                        meta = manager.dict()
                        meta["svo"] = svo_stub
                        meta.update(expr.meta)

                        if lib_t <= 0:
                            future = pool.submit(compile_threaded, None, compiler.STUB, dvo, expr, order,
                                                 meta, dump)
                        else:
                            future = pool.submit(compile_threaded, lib_t, compiler.STUB, dvo, expr, order,
                                                 meta, dump)

                        runs.append((future, meta))

                pool.close()
                pool.join()

            for i, (run, meta) in enumerate(runs):
                try:
                    results = run.result()
                    meta = results
                    # cli.say(f"#{i} {compiler.FULL} {dvo} {meta['time-bdd-build']:.3f}s ({meta['time-bdd-bootstrap']:.3f}s)")
                    cli.say(f"#{i} {compiler.FULL} {dvo} {meta['time-bdd-build']}s ({meta['time-bdd-bootstrap']}s)")
                except TimeoutError:
                    cli.say(f"#{i} {compiler.FULL} {dvo} timeouted ({lib_t}s)")
                except Exception as exc:
                    cli.say("Exception case")
                    traceback.print_exc()

                if "log" in meta:
                    if meta["log"]:
                        _, _, _, _, time_dvo = meta["log"][-1]
                        meta["time-dvo"] = time_dvo
                    meta['input-filename'] = meta['input-filename'].replace('.xml', '').replace('_DIMACS.dimacs', '')
                    stats.append(meta)
        # jinja_renderer.render("bdd", stat_file, stats)

    return stats


class BDD():

    def __init__(self, lib, dvo=None):
        self.bdd = None
        self.lib = lib
        self.mgr = lib.Manager()
        self.mgr.init()

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

    def build_from_CNF(self, expr, order, meta=dict()):

        bdd = self.bdd
        lib = self.lib
        mgr = self.mgr

        meta["bdd-lib"] = self.lib.STUB
        meta["bdd-dvo"] = mgr.get_dvo()
        meta["log"] = list()

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

            if hasattr(mgr, "dvo_time"):
                time_dvo = mgr.dvo_time()
                time_bdd = time_total - time_dvo
            else:
                time_dvo = 0
                time_bdd = 0

            log = meta["log"]
            log.append((i, str(clause), time_total, time_bdd, time_dvo))
            meta["log"] = log

            i += 1

            # inner_order = mgr.get_order(bdd)

            # if inner_order != order:
            #     order = inner_order

        meta["time-bdd-build"] = toc()
        meta["bdd-build-timeout"] = False
        meta["bdd-nodes"] = self.mgr.size_(bdd)

        self.bdd = bdd

        return meta

    def dump(self, expr, filename, meta):
        self.mgr.dump(self.bdd, filename, no_variables=expr.get_no_variables(), meta=meta)


def info_compile(expr, compiler, context):
    cli.say("Compiling", cli.highlight(expr.meta["input-filename"]))
    print("\t\u221f SVO:", context["svo"].STUB)
    print("\t\u221f LIB:", compiler.FULL)
    print("\t\u221f DVO:", context["dvo"])
    print()