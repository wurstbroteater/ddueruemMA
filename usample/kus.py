import config
from cli import cli

import re

from os import path, chdir, getcwd, rename, linesep

import subprocess
from subprocess import PIPE

from util.util import hash_hex, tic, toc
from util import plugin

STUB = "kus"
FULL = "KUS"

USES_KC = True
KC_LANG = "d-DNNF"
KC_COMPILER = "d4"

tool_dir = path.join(config.DIR_TOOLS, "kus")
git_url = "https://github.com/meelgroup/KUS"
git_commit = "0dfba46f6ccb0c4df60e3b318c6c92f9e8407ab1"

tool_main = path.join(tool_dir, "KUS.py")
tool_requirements = path.join(tool_dir, "requirements.txt")

venv = path.join(tool_dir, ".venv")

venvPython = path.join(venv, "bin/python")
venvPIP = path.join(venv, "bin/pip")

env = {
    "PATH": "/usr/bin",
    "VIRTUAL_ENV": venv
}

P_ddnnftime = re.compile(r"Time taken for dDNNF compilation:\s+(?P<time>\d+[.]\d+)")
P_nnfparse = re.compile(r"Time taken to parse the nnf text:\s+(?P<time>\d+[.]\d+)")
P_mctime = re.compile(r"Time taken for Model Counting:\s+(?P<time>\d+[.]\d+)")
P_mc = re.compile(r"Model Count:\s+(?P<count>\d+)")
P_sampling = re.compile(r"Time taken by sampling:\s+(?P<time>\d+[.]\d+)")

P_sampleconf = re.compile(r"\d+,(?P<conf>[\d\s-]+)")


def sample(input_file, n_samples, output_file, i=None, store=None):
    # required as KUS calls d4 without checking CWD
    original_path = getcwd()
    chdir(tool_dir)

    run_id = STUB

    if i:
        run_id = f"{STUB}-{i}"

    tic(run_id)
    output = subprocess.run(
        [venvPython, tool_main, input_file, "--samples", str(n_samples), "--outputfile", output_file], env=env,
        capture_output=True).stdout.decode('utf-8')
    total = toc(run_id)

    ddnnf_time = f"{float(P_ddnnftime.search(output)['time']):.3f}"
    nnfparse_time = f"{float(P_nnfparse.search(output)['time']):.3f}"
    mctime = f"{float(P_mctime.search(output)['time']):.3f}"
    mc = P_mc.search(output)["count"]
    sample_time = f"{float(P_sampling.search(output)['time']):.3f}"

    store[i] = {
        "kc_time": f"{float(ddnnf_time) + float(nnfparse_time):.3f}",
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
            conf = m["conf"].strip()
            conf = [int(x) for x in re.split(r"\s+", conf)]
            conf = sorted(conf, key=lambda x: abs(x))
            conf = [str(x) for x in conf]
            conf = ", ".join(conf)
            out.append(conf)

    out = linesep.join(out) + linesep

    with open(output_file, "w") as file:
        file.write(out)


def install_post():
    cli.say("Installing KUS requirements", origin=FULL)

    subprocess.run(["python", "-m", "venv", venv])
    subprocess.run([venvPIP, "install", "--upgrade", "pip"], env=env, capture_output=True)

    subprocess.run([venvPIP, "install", "wheel"], env=env, capture_output=True)
    subprocess.run([venvPIP, "install", "numpy"], env=env, capture_output=True)
    subprocess.run([venvPIP, "install", "pydot"], env=env, capture_output=True)
