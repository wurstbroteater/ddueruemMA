import config
from cli import cli

import re

from os import path, chdir, getcwd, rename, linesep

import subprocess
from subprocess import PIPE
import random

from util.util import hash_hex, tic, toc
from util import plugin

STUB = "spur"
FULL = "SPUR"

USES_KC = False

tool_dir = path.join(config.DIR_TOOLS, "spur")
git_url = "https://github.com/ZaydH/spur"

tool_exe = path.join(tool_dir, "spur")

P_sampleconf = re.compile(r"\d+,(?P<conf>[01*]+)")


def build():
    original_path = getcwd()
    chdir(tool_dir)

    cli.say("CMaking SPUR", origin=FULL)
    subprocess.run(["cmake", "-DCMAKE_BUILD_TYPE=Release", "."], capture_output=True)

    cli.say("Making SPUR", origin=FULL)
    subprocess.run(["make"], capture_output=True)

    chdir(original_path)


def sample(input_file, n_samples, output_file, i=None, store=None):
    run_id = STUB

    if i:
        run_id = f"{STUB}-{i}"

    tic(run_id)
    output = subprocess.run([tool_exe, "-cnf", input_file, "-s", str(n_samples), "-out", output_file],
                            capture_output=True).stdout.decode('utf-8')
    total = toc(run_id)

    store[i] = {
        "time_total": f"{total:.3f}"
    }

    format(output_file)


def format(output_file):
    raw = []

    with open(output_file, "r") as file:
        raw = file.readlines()

    out = []

    for line in raw:
        if m := P_sampleconf.match(line):
            oconf = m["conf"].strip()

            conf = []
            for i, c in enumerate(oconf):
                if c == "1":
                    conf.append(i + 1)
                elif c == "0":
                    conf.append(-(i + 1))
                else:
                    if random.randint(0, 1) == 1:
                        conf.append(i + 1)
                    else:
                        conf.append(-(i + 1))

            conf = [str(x) for x in conf]
            conf = ", ".join(conf)
            out.append(conf)

    out = linesep.join(out) + linesep

    with open(output_file, "w") as file:
        file.write(out)


def install_post():
    pass
