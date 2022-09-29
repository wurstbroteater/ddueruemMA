import config
from cli import cli
from util.util import tic, toc

import os
from os import path, getcwd, chdir, linesep, listdir
from shutil import rmtree

import subprocess

STUB = "smarch"
FULL = "Smarch"

USES_KC = False

tool_dir = path.join(config.DIR_TOOLS, "smarch")
git_url = "https://github.com/jeho-oh/Smarch.git"
git_commit = ""  # TODO

tool_main = path.join(tool_dir, "smarch_base.py")

venv = path.join(tool_dir, ".venv")
venvPython = path.join(venv, "bin/python")
venvPIP = path.join(venv, "bin/pip")

bloat_dirs = [".idea", "FeatureModel", "Ratios", "Samples", "Stats", "venv"]

sharpSAT_dir = path.join(tool_dir, "sharpSAT")
sharpSAT_url = "https://github.com/jeho-oh/sharpSAT.git"
sharpSAT_commit = "c44cc3683332a89c255bdfe2c361a2c4fa920751"

sharpSAT_configure = path.join(sharpSAT_dir, "setupdev.sh")
sharpSAT_sources = path.join(sharpSAT_dir, "build/Release")


def sample(input_file, n_samples, output_file, i=None, store=None):
    model_name, _ = path.splitext(path.basename(input_file))

    output_dir = path.join(config.DIR_CACHE, model_name + "-dir")

    run_id = STUB

    if i:
        run_id = f"{STUB}-{i}"

    tic(run_id)
    output = subprocess.run([venvPython, tool_main, "-o", output_dir, input_file, str(n_samples)],
                            capture_output=True).stdout.decode("utf-8")
    total = toc(run_id)

    filename, _ = path.splitext(input_file)

    filename_old = f"{path.basename(filename)}_{n_samples}.samples"
    filename_old = path.join(output_dir, filename_old)

    os.rename(filename_old, output_file)

    store[i] = {
        "time_total": f"{total:.3f}"
    }

    format(output_file)


def format(output_file):
    pass


def install_post():
    if not listdir(sharpSAT_dir):
        cli.say("Downloading sharpSAT dependency", origin=FULL)
        subprocess.run(["git", "clone", sharpSAT_url, sharpSAT_dir], capture_output=True)

    original_dir = getcwd()
    chdir(sharpSAT_dir)

    cli.say("Checking out required commit for sharpSAT", origin=FULL)
    subprocess.run(["git", "checkout", sharpSAT_commit], capture_output=True)

    cli.say("Configuring sharpSAT", origin=FULL)
    subprocess.run([sharpSAT_configure], capture_output=True)

    cli.say("Making sharpSAT", origin=FULL)
    chdir(sharpSAT_sources)

    subprocess.run(["make"], capture_output=True)

    chdir(original_dir)

    cli.say("Fixing broken lines in", cli.highlight("smarch_base.py"), origin=FULL)

    # Fixing broken line in smarch_base.py

    filename = path.join(tool_dir, "smarch_base.py")

    line_fixes = [
        {  # fixes sharpSAT path
            "linenr": 16,
            "old": "SHARPSAT = srcdir + '/sharpSAT/Release/sharpSAT'",
            "rep": "SHARPSAT = srcdir + '/sharpSAT/build/Release/sharpSAT'"
        },
        # {   # allows to supply sample file instead of dir  
        #     "linenr": 339,
        #     "old": "samplefile = odir + \"/\" + target + \"_\" + str(n) + \".samples\"",
        #     "rep": "samplefile = odir"
        # },
    ]

    # lines_remove = [126, 127, 349, 350]
    lines_remove = []

    with open(filename) as file:
        raw = file.readlines()

    for fix in line_fixes:
        linenr = fix["linenr"]
        old = fix["old"]
        rep = fix["rep"]

        try:
            i = raw[linenr].index(old)
            raw[linenr] = " " * i + rep + linesep
        except ValueError:
            cli.error("Expected line to fix not found", linenr, old, rep)

    for line in lines_remove:
        raw[line] = ""

    raw = "".join(raw)

    with open(filename, "w") as file:
        file.write(raw)

    cli.say("Installing pycoSAT dependency", origin=FULL)

    venv = path.join(tool_dir, ".venv")

    env = {
        "PATH": "/usr/bin",
        "VIRTUAL_ENV": venv
    }

    venvPIP = f"{venv}/bin/pip"

    subprocess.run(["python", "-m", "venv", venv], capture_output=True)
    subprocess.run([venvPIP, "install", "wheel"], env=env, capture_output=True)
    subprocess.run([venvPIP, "install", "pycosat"], env=env, capture_output=True)

    cli.say("Cleaning up repo bloat", origin=FULL)

    for d in bloat_dirs:
        p = path.join(tool_dir, d)
        rmtree(p)
