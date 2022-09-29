import re
import multiprocessing
import functools as ft
from os import linesep, path

from svo import *  # DO NOT REMOVE THIS IMPORT! Or else SVOs wont be recognized by plugin.filter...
import config
from cli import cli
from util import plugin, util
from util.formats import CNF

plugins = plugin.filter([globals()[x] for x in dir()], ["run", "run_cached"])


def by_stub(stub):
    return plugins.get(stub)


def compute(expr, details):
    algos = details["algos"]
    settings = details["settings"]
    algos_names = list(map(lambda x: x.__name__.replace('svo.', ''), algos))  # Just the file name of the SVO
    if ft.reduce(lambda x, y: x or ('pre_cl' in y) or ('fm_traversal' in y), algos_names, False):
        # TODO: FIX - Currently this is false if input is not dimacs but svo is force or for svo is pre_cl
        expr_name = expr['dimacs'].meta['input-filename']
    else:
        expr_name = expr.meta["input-filename"]

    # the number of orders to compute per algorithm
    n = settings["n"]

    out = dict()

    for svo in algos:
        svo_name = svo.STUB
        if 'pre_cl' in svo_name or 'fm_traversal' in svo_name:
            svo_name += '_' + settings['by']
        if settings["par"]:
            cli.say(f"Computing", cli.highlight(n), "orders in parallel for", cli.highlight(expr_name), "using",
                    cli.highlight(svo_name))
            results = compute_parallel(expr, svo, n, settings)
        else:
            cli.say(f"Computing", cli.highlight(n), "orders sequentially using", cli.highlight(svo_name))
            results = compute_parallel(expr, svo, settings, threads=1)

        results = post(expr, results)
        out[svo.STUB] = results

    out = store(expr, n, out, settings)

    if type(expr) == CNF:
        expr.orders = out

    return out


def compute_parallel(expr, svo, n, settings, threads=None):
    manager = multiprocessing.Manager()

    if threads:
        pool = manager.Pool(threads)
    else:
        pool = manager.Pool()

    store = manager.dict()

    for i in range(n):
        svo.run_cached(expr, i, store, settings)
        # pool.apply_async(svo.run_cached, args=(expr, i, store, settings))

    pool.close()
    pool.join()

    return store.values()


def post(expr, results):
    for i, entry in enumerate(results):

        if "orders" in entry:
            entry.pop("orders")

        results[i] = entry

        if "times" in entry:
            times = [t.total_seconds() for t in entry["times"]]
            times = [f"{t:.3f}" for t in times]
            entry["times"] = times

    return results


def store(expr, n, orders_by_svo, settings):
    out = {}
    if type(expr) == CNF:
        cnf = expr
    else:
        cnf = expr['dimacs']

    for stub, orders in orders_by_svo.items():
        content = [
            f"input-filename:{cnf.meta['input-filename']}",
            f"input-filehash:{cnf.meta['input-filehash']}",
            f"svo-stub:{stub}",
            f"n:{n}",
            "[orders]"
        ]

        for entry in orders:
            order = entry.pop("order")

            info_str = []
            for k, v in entry.items():
                if k == "orders":
                    continue
                if isinstance(v, list):
                    ls = ",".join([str(x) for x in v])
                    info_str.append(f"{k}:{ls}")
                else:
                    info_str.append(f"{k}:{v}")

            info_str = ";".join(info_str)

            if info_str:
                content.append(f"{', '.join([str(x) for x in order])};{info_str}")
            else:
                content.append(", ".join([str(x) for x in order]))

        content = linesep.join(content) + linesep
        if 'pre_cl' in stub or 'fm_traversal' in stub:
            cutting_point = cnf.meta['input-filename'].find('_DIMACS')
            if cutting_point != -1:
                filename = f"{cnf.meta['input-filename'][0:cutting_point]}-{stub}_{settings['by']}-{n}.orders"
            else:
                cli.warning('Could not extract model name for saving orders file. Using default naming schema')
                filename = f"{cnf.meta['input-filename']}-{stub}_{settings['by']}-{n}.orders"
        else:
            filename = f"{cnf.meta['input-filename']}-{stub}-{n}.orders"
        filepath = path.join(config.DIR_OUT, filename)

        if path.exists(filepath):
            if "ignore_existing" not in settings:
                filepath_old = filepath
                if 'pre_cl' in stub or 'fm_traversal' in stub:
                    cutting_point = cnf.meta['input-filename'].find('_DIMACS')
                    if cutting_point != -1:
                        filename = f"{cnf.meta['input-filename'][0:cutting_point]}-{stub}_{settings['by']}-{n}-{util.timestamp()}.orders"
                    else:
                        cli.warning('Could not extract model name for saving orders file. Using default naming schema')
                        filename = f"{cnf.meta['input-filename']}-{stub}_{settings['by']}-{n}-{util.timestamp()}.orders"
                else:
                    filename = f"{cnf.meta['input-filename']}-{stub}-{n}-{util.timestamp()}.orders"
                filepath = path.join(config.DIR_OUT, filename)

                cli.say("Order file", cli.highlight(filepath_old), "already exists, saving with timestamp",
                        cli.highlight(filepath))

        with open(filepath, "w+") as file:
            file.write(content)

        out[stub] = filepath

    return out


def parse_orders(filename):

    with open(filename, "r") as file:
        raw = file.readlines()

    i = raw.index("[orders]\n")

    orders = raw[i + 1:]
    orders = [re.split(";", order)[0] for order in orders]
    orders = [re.split(r",\s+", order) for order in orders]
    orders = [[int(x) for x in order] for order in orders]

    return orders
