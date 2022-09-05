import multiprocessing

from os import linesep, path

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

    expr_name = expr.meta["input-filename"]

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

    for stub, orders in orders_by_svo.items():
        content = [
            f"input-filename:{expr.meta['input-filename']}",
            f"input-filehash:{expr.meta['input-filehash']}",
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

        filename = f"{expr.meta['input-filename']}-{stub}-{n}.orders"
        filepath = path.join(config.DIR_OUT, filename)

        if path.exists(filepath):
            if not "ignore_existing" in settings:
                filepath_old = filepath

                filename = f"{expr.meta['input-filename']}-{stub}-{n}-{util.timestamp()}.orders"
                filepath = path.join(config.DIR_OUT, filename)

                cli.say("Order file", cli.highlight(filepath_old), "already exists, saving with timestamp",
                        cli.highlight(filepath))

        with open(filepath, "w+") as file:
            file.write(content)

        out[stub] = filepath

    return out
