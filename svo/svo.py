import multiprocessing

from os import linesep, path

from util.formats import CNF
from . import *
import config
from util import plugin, util
from cli import cli

plugins = plugin.filter([globals()[x] for x in dir()], ["run", "run_cached"])


def by_stub(stub):
    return plugins.get(stub)


def compute(expr, details):
    algos = details["algos"]
    settings = details["settings"]
    if type(expr) == CNF:
        expr_name = expr.meta["input-filename"]
    else:
        # currently this is false if input file is not dimacs but svo is force
        # or for svo is pre_cl
        expr_name = expr['dimacs'].meta["input-filename"]

    # the number of orders to compute per algorithm
    n = settings["n"]

    out = dict()

    for svo in algos:
        if settings["par"]:
            cli.say(f"Computing", cli.highlight(n), "orders in parallel for", cli.highlight(expr_name), "using",
                    cli.highlight(svo.STUB))
            orders = compute_parallel(expr, svo, n, settings)
        else:
            cli.say(f"Computing", cli.highlight(n), "orders sequentially using", cli.highlight(svo.STUB))
            orders = compute_seq(expr, svo, n, settings)

        out[svo.STUB] = orders

    out = store(expr, n, out, settings)

    return out


def compute_parallel(expr, svo, n, settings):
    manager = multiprocessing.Manager()
    pool = manager.Pool()
    store = manager.dict()
    jobs = []

    for i in range(n):
        pool.apply_async(svo.run_cached, args=(expr, i, store, settings))

    pool.close()
    pool.join()

    return store.values()


def compute_seq(expr, svo, n, settings):
    orders = []

    for i in range(n):
        order = svo.run(expr, **settings)
        orders.append(order)

    return orders


def store(expr, n, orders_by_svo, settings):
    out = {}
    if type(expr) == CNF:
        cnf = expr
    else:
        # currently this is false if input file is not dimacs but svo is force
        # or for svo is pre_cl
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
                info_str.append(f"{k}:{v}")

            info_str = ";".join(info_str)

            if info_str:
                content.append(f"{', '.join([str(x) for x in order])};{info_str}")
            else:
                content.append(", ".join([str(x) for x in order]))

        content = linesep.join(content) + linesep
        if 'pre_cl' in stub:
            cutting_point = cnf.meta['input-filename'].find('_DIMACS')
            if cutting_point != -1:
                filename = f"{cnf.meta['input-filename'][0:cutting_point]}-{stub}-{n}.orders"
            else:
                cli.warning('Could not extract model name for saving orders file. Using default naming schema')
                filename = f"{cnf.meta['input-filename']}-{stub}-{n}.orders"
        else:
            filename = f"{cnf.meta['input-filename']}-{stub}-{n}.orders"
        filepath = path.join(config.DIR_OUT, filename)

        if path.exists(filepath):
            if  "ignore_existing" not in settings:
                filepath_old = filepath

                filename = f"{cnf.meta['input-filename']}-{stub}-{n}-{util.timestamp()}.orders"
                filepath = path.join(config.DIR_OUT, filename)

                cli.say("Order file", cli.highlight(filepath_old), "already exists, saving with timestamp",
                        cli.highlight(filepath))

        with open(filepath, "w+") as file:
            file.write(content)

        out[stub] = filepath

    return out
