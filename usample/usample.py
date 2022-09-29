import multiprocessing
from os import path

from . import *
import config
from cli import cli
from util import plugin, util

plugins = plugin.filter([globals()[x] for x in dir()], ["install_post", "sample", "format"])


def by_stub(stub):
    return plugins.get(stub.lower())


def sample(algo, files, details):
    settings = details["settings"]
    n_samples = settings["n"]

    inputs = []

    for file in files:
        basename = path.basename(file)
        out_file = f"{basename}-{algo.STUB}-{n_samples}.samples"
        out_file = path.join(config.DIR_OUT, out_file)

        input = {
            "input_file": file,
            "input_hash": util.hash_hex(file),
            "output_file": out_file,
            "sample_size": n_samples,
            "sample_tool": algo.STUB
        }

        if algo.USES_KC:
            input.update({
                "kc_lang": algo.KC_LANG,
                "kc_compiler": algo.KC_COMPILER
            })

        inputs.append(input)

    manager = multiprocessing.Manager()
    pool = manager.Pool()
    store = manager.dict()

    cli.say("with", cli.highlight(algo.FULL))

    for i, input in enumerate(inputs):
        input_file = input["input_file"]
        output_file = input["output_file"]

        algo.sample(input_file, n_samples, output_file, i, store)
        # pool.apply_async(algo.sample, args=(input_file, n_samples, output_file, i, store))

    pool.close()
    pool.join()

    store = dict(store)

    for i, input in enumerate(inputs):
        if i in store:
            store[i].update(input)
        else:
            store[i] = input

    return store
