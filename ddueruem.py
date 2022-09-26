#!/usr/bin/env python3

"""

"""

# ------------------------------------------------------------------------------
# External imports #-----------------------------------------------------------
import os
import re
import subprocess
import sys
from os import linesep, path
from pathlib import Path
from datetime import datetime
# ------------------------------------------------------------------------------
# Internal imports #-----------------------------------------------------------
import config
from bdd import bdd
from svo import svo, fm_traversal
from usample import usample
from cli import cli, argparser
from util import plugin, util, jinja_renderer
from parsers import parsers, sxfm_parser, dimacs


# ------------------------------------------------------------------------------
# feature_model_name = 'busybox1dot18dot0'
# feature_model_name = 'npc'
# feature_model_name = 'anyvend'
# feature_model_name = 'finSer01'
# feature_model_name = 'automotiv2v4'
feature_model_name = 'mendonca_dis'

def main():
    bootstrap()
    args = sys.argv

    name = feature_model_name + '.xml'
    # svo_name = 'pre_cl'
    # traversal_strategy = 'size'
    svo_name = 'fm_traversal'
    # traversal_strategy = 'bf'
    # evals = [xml for xml in glob('evaluation/**/*.xml', recursive=True) if '_sxfm' not in str(xml).lower()]
    # evals = [x for x in evals if 'automotive' not in str(x).lower()]
    # args = ['./ddueruem.py'] + evals + ['--svo', svo_name]
    # args = ['./ddueruem.py', 'examples/xml/' + name, '--svo', svo_name]
    # args = ['./ddueruem.py', f'examples/xml/{feature_model_name}.xml', 'examples/xml/npc.xml', '--svo', svo_name]
    cli.debug(args)
    files, actions = argparser.parse(args)

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

            input_filepath = expr.meta["input-filepath"]
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

    if "SVO" in actions:
        # for fm_traversal strategy is 'df','bf' 'pre', 'in' or 'post'
        # for pre_cl strategy is 'size' or 'min_span'
        traversal_strategy = 'size'
        cli.say("Computing static variable orders...")
        for algo in actions["SVO"]['algos']:
            algo_name = algo.__name__.replace('svo.', '').lower().strip()
            if ('force' in algo_name) or ('random' in algo_name):
                for expr in exprs:
                    svo.compute(expr, actions["SVO"])
            elif 'pre_cl' in algo_name:
                for expr in exprs:
                    file = Path(expr[-1]['input-filename'])
                    if not file.name.endswith('.xml'):
                        cli.error('SVO pre_cl is only compatible with .xml files!')
                        return
                    data = {'FeatureModel': expr[0], 'CTCs': expr[1], 'by': traversal_strategy}
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
                    print('For FM', file_name, 'n is', actions['SVO']['settings']['n'])
                    svo.compute(data, actions['SVO'])

            elif 'fm_traversal' in algo_name:
                traversal_strategy = 'bf'
                for expr in exprs:
                    data = {'FeatureModel': expr[0], 'CTCs': expr[1], 'by': traversal_strategy}
                    file = Path(expr[-1]['input-filename'])
                    fm_traversal_file_name = str(file).replace('.xml', '').split(os.path.sep)[
                                                 -1] + f'-fm_traversal_{traversal_strategy}.order'
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
                    if Path(fm_traversal_file_path).is_file():
                        cli.say(fm_traversal_file_name + ' already present, skipping')
                        continue

                    print('data', data['dimacs'].variables)
                    print('feature model', data['FeatureModel'])
                    start = datetime.now()
                    # TODO: Change saving computed order to use svo.compute
                    # svo.compute(data, actions['SVO'])
                    features = fm_traversal.run(data, traversal=traversal_strategy)
                    end = datetime.now()
                    for f in features['order']:
                        for f_dimacs in data['dimacs'].variables:
                            # print('Feature', f, 'f_dimacs', f_dimacs)
                            if data['dimacs'].variables[f_dimacs]['desc'] == f['name']:
                                f.update({'dimacsIdx': data['dimacs'].variables[f_dimacs]['ID']})
                                break
                    cli.say('name, id', list(map(lambda x: x['name'] + ', ' + str(x['dimacsIdx']), features['order'])))
                    # direct save to file
                    open(fm_traversal_file_path, 'w').write(
                        str({'order': list(map(lambda x: x['dimacsIdx'], features['order'])), 't': end - start}))
            else:
                cli.error('SVO name ' + algo_name + ' is unkown!')
                return

        cli.say("Finished static variable ordering.")

    bdd_stats = []
    if "BDD" in actions:
        cli.say("Computing BDDs")

        for compiler in actions["BDD"]["compilers"]:
            stats = bdd.compile(compiler, exprs, actions["BDD"])
            bdd_stats.extend(stats)

        stat_file = path.join(config.DIR_OUT, f"bdd-{util.timestamp()}.csv")
        jinja_renderer.render("bdd", stat_file, bdd_stats)
        exit()


def bootstrap():
    # Verify existence or create directories
    dirs = [config.DIR_ROOT, config.DIR_ARCHIVES, config.DIR_CACHE, config.DIR_TOOLS, config.DIR_OUT]

    for dir in dirs:
        verify_or_create_dir(dir)


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
