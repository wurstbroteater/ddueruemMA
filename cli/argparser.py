"""

"""

# ------------------------------------------------------------------------------
# External imports #-----------------------------------------------------------
from os import path
import re

# ------------------------------------------------------------------------------
# Internal imports #-----------------------------------------------------------
from cli import cli
from bdd import bdd
from svo import svo
from usample import usample

# ------------------------------------------------------------------------------
# RegEx Patterns #-------------------------------------------------------------

P_action_param = re.compile(r"(?P<key>\w+):(?P<value>[^\s]+)")


# ------------------------------------------------------------------------------


def parse(args):
    actions = {}

    current_args = []
    action_groups = []

    for arg in args[1:]:
        if arg in ACTIONS.keys():
            action_groups.append(current_args)
            current_args = [arg]
        else:
            current_args.append(arg)

    if current_args:
        action_groups.append(current_args)

    if not action_groups:
        cli.say("No arguments submitted, nothing to do.")
        exit(1)

    files = action_groups[0]
    files = process_files(files)

    try:
        i = [x[0] for x in action_groups[1:]].index("--install")
    except ValueError:
        i = None

    if i:

        action = action_groups[i][0]
        params = action_groups[i][1:]

        action, details = parser(params)
        actions[action] = details

    else:
        for action_group in action_groups[1:]:
            action = action_group[0]
            params = action_group[1:]

            if action in ACTIONS.keys():
                parser = ACTIONS[action]["parser"]

                action, details = parser(params)
                actions[action] = details

            else:
                cli.error("Action", cli.highlight(action), "unknown, ignoring")

    return files, actions


def process_files(files):
    good_files = []

    for file in files:
        if not path.exists(file):
            cli.say(cli.highlight(file), "does not exist, disregarded.")
        elif not path.isfile(file):
            cli.say(cli.highlight(file), "is not a file, disregarded.")
        else:
            good_files.append(path.abspath(file))

    return good_files


def process_svo(params):
    settings = ACTIONS["--svo"]["defaults"]

    algos = []

    for algo in settings["algos"]:
        if isinstance(algo, str):
            algo = svo.by_stub(algo.lower())

            if algo:
                algos.append(algo)

    settings.pop("algos")

    for param in params:

        if m := P_action_param.match(param):
            k = m["key"]
            v = m["value"]

            v = ensure_same_type(settings[k], v)

            settings[k] = v

        else:
            is_pre_cl = 'pre_cl' in param.lower()
            is_fm_traversal = 'fm_traversal' in param.lower()
            if is_pre_cl:
                algo = svo.by_stub('pre_cl')
                settings['by'] = param.split('pre_cl_')[-1].strip().lower()
            elif is_fm_traversal:
                algo = svo.by_stub('fm_traversal')
                settings['by'] = param.split('fm_traversal_')[-1].strip().lower()
            else:
                algo = svo.by_stub(param.lower())
            if algo:
                algos.append(algo)
            else:
                if param in settings:
                    settings[param] = True
                else:
                    cli.warning("Parameter", cli.highlight(param),
                                "is neither a registered heuristic nor configurable parameter, ignoring.",
                                origin="argparser[--svo]")

    return "SVO", {
        "algos": algos,
        "settings": settings
    }


def process_bdd(params):
    settings = ACTIONS["--bdd"]["defaults"]

    algos = []

    for algo in settings["compilers"]:
        if isinstance(algo, str):
            algo = usample.by_stub(algo)

            if algo:
                algos.append(algo)

    settings.pop("compilers")

    for param in params:

        if m := P_action_param.match(param):
            k = m["key"]
            v = m["value"]

            v = ensure_same_type(settings[k], v)

            settings[k] = v

        else:
            algo = bdd.by_stub(param)

            if algo:
                algos.append(algo)
            else:
                if param in settings:
                    settings[param] = True
                else:
                    cli.warning("Parameter", cli.highlight(param),
                                "is neither a registered sampler nor configurable parameter, ignoring.",
                                origin="argparser[--svo]")

    return "BDD", {
        "compilers": algos,
        "settings": settings
    }


def process_usample(params):
    settings = ACTIONS["--usample"]["defaults"]

    algos = []

    for algo in settings["algos"]:
        if isinstance(algo, str):
            algo = usample.by_stub(algo)

            if algo:
                algos.append(algo)

    settings.pop("algos")

    for param in params:

        if m := P_action_param.match(param):
            k = m["key"]
            v = m["value"]

            v = ensure_same_type(settings[k], v)

            settings[k] = v

        else:
            algo = usample.by_stub(param)

            if algo:
                algos.append(algo)
            else:
                if param in settings:
                    settings[param] = True
                else:
                    cli.warning("Parameter", cli.highlight(param),
                                "is neither a registered sampler nor configurable parameter, ignoring.",
                                origin="argparser[--svo]")

    return "USAMPLE", {
        "algos": algos,
        "settings": settings
    }


def process_install(params):
    tools_available = dict()

    tools_available.update(bdd.plugins)
    tools_available.update(usample.plugins)

    tools = []

    for x in params:

        x = x.lower()

        if x == "bdd":
            tools.extend(bdd.plugins).values()
        elif x == "nnf":
            tools.extend(nnf.plugins).values()
        elif x == "usample":
            tools.extend(usample.plugins).values()
        else:
            if x in tools_available:
                tools.append(tools_available[x])

    return "INSTALL", {
        "tools": tools
    }


def process_analysis(params):
    return "ANALYZE", {}


def ensure_same_type(old, new):
    old_type = type(old)
    new_type = type(new)

    if old is None:
        return new

    if old_type == new_type:
        return new

    if old_type == int:
        return int(new)

    if old_type == list:
        return re.split(",", new)

    if old_type == bool:
        if new.lower() in ["true", "1", "t"]:
            return True
        else:
            return False


# ------------------------------------------------------------------------------
# Initialization #-------------------------------------------------------------

ACTIONS = {
    "--svo": {
        "desc": "Compute variable orderings for input files",
        "parser": process_svo,
        "defaults": {
            "algos": [],
            "n": 10,
            "time_run": 60,
            "par": True,
            "seed": None
        }
    },
    "--bdd": {
        "desc": "Compute binary decision diagrams for input files",
        "parser": process_bdd,
        "defaults": {
            "compilers": [bdd.by_stub("cudd")],
            "svo": [svo.by_stub("force")],
            "dvo": ["sift"],
            "lib_t": 60,
            "dump": False
        }
    },
    "--usample": {
        "desc": "Compute uniform samples for input files",
        "parser": process_usample,
        "defaults": {
            "algos": [],
            "n": 10,
            "timeout": 60,
            "par": True
        }
    },
    "--install": {
        "desc": "Install tools",
        "parser": process_install
    },
    "--analyze": {
        "desc": "Analyze the model",
        "parser": process_analysis
    }
}
