#!/usr/bin/env python3

"""

"""

# ------------------------------------------------------------------------------
# External imports #-----------------------------------------------------------
import os
import re
import subprocess
import sys
from glob import glob
from os import linesep, path
from pathlib import Path
# ------------------------------------------------------------------------------
# Internal imports #-----------------------------------------------------------
import config
from cli import cli, argparser

from bdd import bdd
from svo import svo
from usample import usample

from util import plugin, util, jinja_renderer
from parsers import parsers, sxfm_parser, dimacs, order_parser
from util.formats import CNF


# ------------------------------------------------------------------------------


def main():
    bootstrap()
    args = sys.argv

    if (e := '--evaluation') in args:
        evals = [xml for xml in glob('evaluation/**/*.xml', recursive=True) if '_sxfm' not in str(xml).lower()]
        evals = [x for x in evals if 'automotive' not in str(x).lower()]
        evals = [x for x in evals if 'linux_2.6' not in str(x).lower()]
        evals = sorted(evals, key=lambda ef: os.stat(ef).st_size)
        pos = args.index(e)
        args = args[:pos] + evals + args[pos + 1:]
    cli.debug(args)

    files, actions = argparser.parse(args)
    # TODO: There is no possibility for just building BDDS
    # ./ddueruem.py <file> --bdd cudd lib_t:-1 dvo:off results in the following actions:
    # {'compilers': [<module 'bdd.cudd' from '/home/eric/Uni/MA/ddueruemMA/bdd/cudd.py'>], 'settings': {'svo': [<module 'svo.force' from '/home/eric/Uni/MA/ddueruemMA/svo/force.py'>], 'dvo': ['off'], 'lib_t': -1}}
    # workaround: Remove svo module if --svo is not in args
    no_svo = False
    if '--svo' not in args:
        try:
            actions['BDD']['settings'].update({'svo': []})
        except KeyError:
            pass
        no_svo = True

    cli.debug("files", files)
    cli.debug("actions", actions)

    if "INSTALL" in actions:
        for tool in actions["INSTALL"]["tools"]:
            cli.say()

            install_ok, require_post = plugin.install(tool)

            if require_post:
                cli.say("Running post install", origin=tool.FULL)
                tool.install_post()

            cli.say("Installation complete", origin=tool.FULL)

        exit()

    if not files:
        cli.say("No input files supplied, nothing to do")

    if "USAMPLE" in actions:
        cli.say("Computing uniform samples...")

        n_samples = actions["USAMPLE"]["settings"]["n"]

        data = []

        for algo in actions["USAMPLE"]["algos"]:
            store = usample.sample(algo, files, actions["USAMPLE"])
            data.extend(store.values())

        stat_file = path.join(config.DIR_OUT, f"usample-{n_samples}-{util.timestamp()}.csv")
        jinja_renderer.render("usample", stat_file, data)

        exit()

    exprs = []

    for file in files:
        parser = parsers.by_filename(file)
        expr = parser.parse(file)
        exprs.append(expr)

    cli.debug("exprs", exprs)

    if "ANALYZE" in actions:
        cli.say("Analyzing")

        sharpSAT = path.join(config.DIR_TOOLS, "smarch", "sharpSAT", "build", "Release", "sharpSAT")

        results = dict()

        for expr in exprs:
            try:
                input_filepath = expr.meta["input-filepath"]
            except AttributeError:
                # input file probably was .xml model, find corresponding dimacs or create it
                input_filepath = Path(expr[-1]['input-filename'])
                cli.say(f"Analyzing model {input_filepath.name.replace('.xml', '')}")
                input_filepath = bootstrap_analyze(str(input_filepath))
                if util.is_file_present(config.DIR_OUT + os.path.sep + Path(input_filepath).name + '.stats'):
                    cli.say(".stats file present, skipping...")
                    continue
                expr = dimacs.parse(input_filepath)

            stat_filepath = path.join(config.DIR_OUT, path.basename(input_filepath)) + ".stats"

            output = subprocess.run([sharpSAT, input_filepath], capture_output=True).stdout.decode("utf-8")
            m = re.search(r"\# solutions[\s\n]+(?P<ssat>\d+)", output)
            mc = int(m["ssat"])
            results["count"] = mc

            results["commonality"] = {}

            for varid in expr.variables.keys():
                filename = path.basename(input_filepath) + f".{varid}"
                output_file = path.join(config.DIR_CACHE, filename)

                expr.clauses.append([int(varid)])

                expr.save_dimacs(output_file)

                output = subprocess.run([sharpSAT, output_file], capture_output=True).stdout.decode("utf-8")
                m = re.search(r"\# solutions[\s\n]+(?P<ssat>\d+)", output)

                results["commonality"][varid] = int(m["ssat"])

                expr.clauses.pop()

            features_core = []
            features_dead = []

            for k, v in results["commonality"].items():
                if v == 0:
                    features_dead.append(k)

                if v == mc:
                    features_core.append(k)

            results["core"] = features_core
            results["dead"] = features_dead

            content = [
                f"input-filename:{expr.meta['input-filename']}",
                f"input-filehash:{expr.meta['input-filehash']}",
                f"solutions-total:{mc}",
                f"features-core:{' '.join([str(x) for x in features_core])}",
                f"features-dead:{' '.join([str(x) for x in features_dead])}",
                "[commonality]",
            ]

            for k, v in results["commonality"].items():
                line = f"{k}:{v}"
                content.append(line)

            with open(stat_filepath, "w+") as file:
                file.write(linesep.join(content))
                file.write(linesep)

        exit()

    if not no_svo and "SVO" in actions:
        # for fm_traversal strategy is 'df','bf' 'pre', 'in' or 'post'
        # for pre_cl strategy is 'size' or 'min_span'
        cli.say("Computing static variable orders...")
        for algo in actions["SVO"]['algos']:
            algo_name = algo.__name__.replace('svo.', '').lower().strip()
            if ('force' in algo_name) or ('random' in algo_name):
                for expr in exprs:
                    if type(expr) == CNF:
                        svo.compute(expr, actions["SVO"])
                    else:
                        file = Path(expr[-1]['input-filename'])
                        if file.name.lower().endswith('.xml'):
                            # check if dimacs present
                            dimacs_file = Path(str(file.parent) + os.path.sep + file.name.replace('.xml', '') +
                                               '_formats' + os.path.sep + file.name.replace('.xml', '') +
                                               '_DIMACS.dimacs')
                            if not dimacs_file.is_file():
                                cli.say('.xml in FORCE: Creating ' + str(dimacs_file))
                                dimacs_file = Path(str(bootstrap_xml_in_force(str(file))[0]))
                            used_svo = 'pre_cl_size'
                            used_n = actions['SVO']['settings']['n']
                            order_file = Path(
                                f"{config.DIR_OUT}{os.path.sep}{file.name.replace('.xml', '')}-{used_svo}-{used_n}.orders")
                            order = None
                            if order_file.is_file():
                                order = order_parser.parse(order_file)[0][0]
                                if not all([isinstance(item, int) for item in order]):
                                    cli.warning('.xml in FORCE: parsed order is not int list!')
                            else:
                                cli.warning(".xml in FORCE: Could not find orders file " + str(order_file))
                            actions['SVO']['settings']['order'] = order
                            svo.compute(dimacs.parse(dimacs_file), actions["SVO"])

                        else:
                            cli.error("Force can not parse file with name " + file.name)
                            return

            elif 'pre_cl' in algo_name:
                for expr in exprs:
                    file = Path(expr[-1]['input-filename'])
                    if not file.name.endswith('.xml'):
                        cli.error('SVO pre_cl is only compatible with .xml files!')
                        return
                    data = {'FeatureModel': expr[0], 'CTCs': expr[1], 'by': actions['SVO']['settings']['by']}
                    file_name = file.name.replace('.xml', '')  # Feature Model name without .xml extension
                    format_paths = bootstrap_pre_cl(str(file))
                    if len(format_paths) > 0:
                        for p in format_paths:
                            if 'dimacs' in p.lower():
                                data.update({'dimacs': dimacs.parse(p)})
                            elif 'sxfm' in p.lower():
                                data.update({'sxfm': sxfm_parser.parse(p)})
                            else:
                                cli.warning("Found suspicious file (format): " + p)
                    svo.compute(data, actions['SVO'])

            elif 'fm_traversal' in algo_name:
                for expr in exprs:
                    data = {'FeatureModel': expr[0], 'CTCs': expr[1], 'by': actions['SVO']['settings']['by']}
                    file = Path(expr[-1]['input-filename'])
                    fm_traversal_file_name = str(file).replace('.xml', '').split(os.path.sep)[
                                                 -1] + f"-fm_traversal_{actions['SVO']['settings']['by']}.order"
                    cli.say('For Feature Model ' + fm_traversal_file_name)
                    format_paths = bootstrap_fm_traversal(str(file))
                    if len(format_paths) > 0:
                        for p in format_paths:
                            if 'dimacs' in p.lower():
                                data.update({'dimacs': dimacs.parse(p)})
                            elif 'sxfm' in p.lower():
                                data.update({'sxfm': sxfm_parser.parse(p)})
                            else:
                                cli.warning("Found suspicious file (format): " + p)
                    cli.debug('For FM', file.name.replace('.xml', ''))

                    fm_traversal_file_path = config.DIR_OUT + os.path.sep + fm_traversal_file_name
                    if util.is_file_present(fm_traversal_file_path):
                        cli.say(fm_traversal_file_name + ' already present, skipping')
                        continue
                    svo.compute(data, actions['SVO'])
            else:
                cli.error('SVO name ' + algo_name + ' is unkown!')
                return

        cli.say("Finished static variable ordering.")

    bdd_stats = []
    if "BDD" in actions:
        cli.say("Computing BDDs")
        for expr in exprs:
            in_file = Path(expr[-1]['input-filename']) if type(expr) != CNF else Path(expr.meta['input-filepath'])
            model_name = in_file.name.replace('.xml', '').replace('_DIMACS.dimacs', '')
            by_in_suffix = 'min_span'
            directory = 'span' if by_in_suffix == 'min_span' else 'size'
            bdd_filename = f"{model_name}-bdd-cudd-{by_in_suffix}.csv"
            if util.is_file_present(config.DIR_OUT + os.path.sep + bdd_filename):
                cli.say('.csv for', in_file.name.replace('.xml', ''), 'already present, skipping ...')
                continue
            cli.say(f"For Model {model_name}")
            for compiler in actions["BDD"]["compilers"]:
                suffix = f'-pre_cl_{by_in_suffix}-1.orders'  # '_DIMACS.dimacs-force-10.orders'
                sep = os.path.sep
                orders_filepath = config.DIR_OUT + f'{sep}data{sep}{directory}{sep}' + model_name + suffix
                if not util.is_file_present(orders_filepath):
                    cli.error('Could not find orders file: ' + orders_filepath)
                    return
                dimacs_filepath = f"{str(in_file.parent)}{os.path.sep}{model_name}_formats{os.path.sep}{model_name}_DIMACS.dimacs" if type(
                    expr) != CNF else in_file
                if not util.is_file_present(dimacs_filepath):
                    cli.warning('Dimacs file not present, creating in: ' + dimacs_filepath)
                    dimacs_filepath = bootstrap_bdd_creation(str(in_file))[0]
                if type(expr) != CNF:
                    attributed_expr = dimacs.parse(dimacs_filepath)
                    attributed_expr.meta = {
                        'input-filename': Path(expr[2]['input-filename']).name,
                        'input-filepath': expr[2]['input-filename'],
                        'input-filehash': expr[2]['input-filehash']}
                    attributed_expr.orders = {}
                    attributed_expr.orders[by_in_suffix] = svo.parse_orders(orders_filepath)
                    attributed_expr = [attributed_expr]
                else:
                    attributed_expr = expr
                    attributed_expr.orders = {}
                    attributed_expr.orders[by_in_suffix] = svo.parse_orders(orders_filepath)
                    attributed_expr = [attributed_expr]
                stats = bdd.compile(compiler, attributed_expr, actions["BDD"])
                stats = [dict(s, svo=by_in_suffix) for s in stats]
                bdd_stats.extend(stats)
                stat_file = path.join(config.DIR_OUT, bdd_filename)
                jinja_renderer.render("svoeval", stat_file, bdd_stats)
                bdd_stats = []

        cli.say('Finished computation of BDDs')
        exit()


def bootstrap():
    # Verify existence or create directories
    dirs = [config.DIR_ROOT, config.DIR_ARCHIVES, config.DIR_CACHE, config.DIR_TOOLS, config.DIR_OUT]

    for dir in dirs:
        verify_or_create_dir(dir)


def bootstrap_analyze(file_path):
    """
    Check if all file formats are present. This follows a certain pattern:
        E.g. for file_path = config.ROOT/home/foo/<model name>.xml
        Check if folder config.ROOT/home/foo/<model name>_formats/ exist then check
          if this folder contains files named like <model name>_DIMACS.dimacs
            If this file is not present, it will be created
    """
    file_path = file_path
    file_name = file_path.split(os.path.sep)[-1]
    formats_dir = file_path.replace(file_name, '') + f"{file_name.replace('.xml', '')}_formats"
    verify_or_create_dir(formats_dir)
    prefix = formats_dir + os.path.sep + file_name.replace('.xml', '')
    expected_folder_content = [prefix + '_DIMACS.dimacs']
    formats = []
    for format_path in expected_folder_content:
        p = Path(format_path)
        if p.is_file():
            continue
        elif not p.is_file() and not p.is_dir():
            if 'dimacs' in format_path.lower():
                formats.append('dimacs')

    if len(formats) > 0:
        cli.say('Creating formats', formats)
        if e := util.translate_xml(file_path, formats_dir, formats) != "Successfully translated to all formats!":
            cli.error(f"Could not create all formats for model {file_name.replace('.xml', '')}: {e}")
            return

    else:
        cli.debug('All formats already present')
    return expected_folder_content[0]


def bootstrap_bdd_creation(file_path):
    """
    Check if all file formats are present. This follows a certain pattern:
        E.g. for file_path = config.ROOT/home/foo/<model name>.xml
        Check if folder config.ROOT/home/foo/<model name>_formats/ exist then check
          if this folder contains files named like <model name>_DIMACS.dimacs
            If this file is not present, it will be created
    """
    file_path = file_path
    file_name = file_path.split(os.path.sep)[-1]
    formats_dir = file_path.replace(file_name, '') + f"{file_name.replace('.xml', '')}_formats"
    verify_or_create_dir(formats_dir)
    prefix = formats_dir + os.path.sep + file_name.replace('.xml', '')
    expected_folder_content = [prefix + '_DIMACS.dimacs']
    formats = []
    for format_path in expected_folder_content:
        p = Path(format_path)
        if p.is_file():
            continue
        elif not p.is_file() and not p.is_dir():
            if 'dimacs' in format_path.lower():
                formats.append('dimacs')

    if len(formats) > 0:
        cli.say('Creating formats', formats)
        if e := util.translate_xml(file_path, formats_dir, formats) != "Successfully translated to all formats!":
            cli.error(f"Could not create all formats for model {file_name.replace('.xml', '')}: {e}")
            return

    else:
        cli.debug('All formats already present')
    return expected_folder_content


def bootstrap_fm_traversal(file_path):
    """
    Check if all file formats are present. This follows a certain pattern:
        E.g. for file_path = config.ROOT/home/foo/<model name>.xml
        Check if folder config.ROOT/home/foo/<model name>_formats/ exist then check
          if this folder contains files named like <model name>_DIMACS.dimacs and <model name>_SXFM.xml
            If one of this files is not present, create it

    """
    file_path = file_path
    file_name = file_path.split(os.path.sep)[-1]
    formats_dir = file_path.replace(file_name, '') + f"{file_name.replace('.xml', '')}_formats"
    verify_or_create_dir(formats_dir)
    prefix = formats_dir + os.path.sep + file_name.replace('.xml', '')
    expected_folder_content = [prefix + '_DIMACS.dimacs']
    formats = []
    for format_path in expected_folder_content:
        p = Path(format_path)
        if p.is_file():
            continue
        elif not p.is_file() and not p.is_dir():
            if 'dimacs' in format_path.lower():
                formats.append('dimacs')

    if len(formats) > 0:
        cli.say('Creating formats', formats)
        if e := util.translate_xml(file_path, formats_dir, formats) != "Successfully translated to all formats!":
            cli.error(f"Could not create all formats for model {file_name.replace('.xml', '')}: {e}")
            return

    else:
        cli.say('All formats already present')
    return expected_folder_content


def bootstrap_xml_in_force(file_path):
    """
    Check if all file formats are present. This follows a certain pattern:
        E.g. for file_path = config.ROOT/home/foo/<model name>.xml
        Check if folder config.ROOT/home/foo/<model name>_formats/ exist then check
          if this folder contains files named like <model name>_DIMACS.dimacs and <model name>_SXFM.xml
            If one of this files is not present, create it

    """
    file_path = file_path
    file_name = file_path.split(os.path.sep)[-1]
    formats_dir = file_path.replace(file_name, '') + f"{file_name.replace('.xml', '')}_formats"
    verify_or_create_dir(formats_dir)
    prefix = formats_dir + os.path.sep + file_name.replace('.xml', '')
    expected_folder_content = [prefix + '_DIMACS.dimacs']
    formats = []
    for format_path in expected_folder_content:
        p = Path(format_path)
        if p.is_file():
            continue
        elif not p.is_file() and not p.is_dir():
            if 'dimacs' in format_path.lower():
                formats.append('dimacs')

    if len(formats) > 0:
        cli.say('Creating formats', formats)
        if e := util.translate_xml(file_path, formats_dir, formats) != "Successfully translated to all formats!":
            cli.error(f"Could not create all formats for model {file_name.replace('.xml', '')}: {e}")
            return

    else:
        cli.say('All formats already present')
    return expected_folder_content


def bootstrap_pre_cl(file_path):
    """
    Check if all file formats are present. This follows a certain pattern:
        E.g. for file_path = config.ROOT/home/foo/<model name>.xml
        Check if folder config.ROOT/home/foo/<model name>_formats/ exist then check
          if this folder contains files named like <model name>_DIMACS.dimacs and <model name>_SXFM.xml
            If one of this files is not present, create it

    """
    file_path = file_path
    file_name = file_path.split(os.path.sep)[-1]
    formats_dir = file_path.replace(file_name, '') + f"{file_name.replace('.xml', '')}_formats"
    verify_or_create_dir(formats_dir)
    prefix = formats_dir + os.path.sep + file_name.replace('.xml', '')
    expected_folder_content = [prefix + '_DIMACS.dimacs',
                               prefix + '_SXFM.xml']
    formats = []
    for format_path in expected_folder_content:
        p = Path(format_path)
        if p.is_file():
            continue
        elif not p.is_file() and not p.is_dir():
            if 'dimacs' in format_path.lower():
                formats.append('dimacs')
            elif 'sxfm' in format_path.lower():
                formats.append('sxfm')

    if len(formats) > 0:
        cli.say('Creating formats', formats)
        if e := util.translate_xml(file_path, formats_dir, formats) != "Successfully translated to all formats!":
            cli.error(f"Could not create all formats for model {file_name.replace('.xml', '')}: {e}")
            return

    else:
        cli.say('All formats already present')
    return expected_folder_content


def verify_or_create_dir(dir):
    """Creates the directory `dir` if it does not already exist."""

    if not path.exists(dir):
        # cli.debug("Directory", cli.highlight(dir), "does not exist, creating")

        try:
            os.mkdir(dir)
        except OSError as ose:
            cli.error("error_create_directory_failed", cli.highlight(dir))
    else:
        pass
        # cli.debug("Verified existence of directory", cli.highlight(dir))


if __name__ == '__main__':
    main()
