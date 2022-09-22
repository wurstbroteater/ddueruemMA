"""

"""

# ------------------------------------------------------------------------------
# External imports #-----------------------------------------------------------
from os import path
import re

# ------------------------------------------------------------------------------
# Internal imports #-----------------------------------------------------------
from cli import cli

from svo import svo

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
        print("No arguments submitted, nothing to do.")
        exit(1)

    files = action_groups[0]
    files = process_files(files)

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
            good_files.append(file)

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
    raise NotImplementedError()


def ensure_same_type(old, new):
    old_type = type(old)
    new_type = type(new)

    if old is None:
        return new

    if old_type == new_type:
        return new

    if old_type == int:
        return int(new)

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
            "n": 100,
            "time_run": 60,
            "par": True,
            "seed": None
        }
    },
    "--bdd": {
        "desc": "Compute binary decision diagrams for input files",
        "parser": process_bdd
    }
}
