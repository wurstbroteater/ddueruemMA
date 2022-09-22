#!/usr/bin/env python3

"""

"""

# ------------------------------------------------------------------------------
# External imports #-----------------------------------------------------------
import os
from os import path
from pathlib import Path
import sys
from glob import glob
# ------------------------------------------------------------------------------
# Internal imports #-----------------------------------------------------------
import config
from util import util
from cli import cli, argparser
from parsers import parsers, dimacs, xml_parser
from svo import svo, fm_traversal

# ------------------------------------------------------------------------------
# feature_model_name = 'busybox1dot18dot0'
# feature_model_name = 'npc'
# feature_model_name = 'anyvend'
# feature_model_name = 'finSer01'
# feature_model_name = 'automotiv2v4'
feature_model_name = 'mendonca_dis'


def main2():
    bootstrap()
    # args = sys.argv
    name = feature_model_name + '.xml'
    # svo_name = 'pre_cl'
    # traversal_strategy = 'size'
    svo_name = 'fm_traversal'
    traversal_strategy = 'bf'
    evals = [xml for xml in glob('evaluation/**/*.xml', recursive=True) if '_sxfm' not in str(xml).lower()]
    # evals = [x for x in evals if 'automotive' not in str(x).lower()]
    args = ['./ddueruem.py'] + evals + ['--svo', svo_name]
    # args = ['./ddueruem.py', 'examples/xml/' + name, '--svo', svo_name]
    # args = ['./ddueruem.py', f'examples/xml/{feature_model_name}.xml', 'examples/xml/npc.xml', '--svo', svo_name]
    cli.debug('args', args)

    files, actions = argparser.parse(args)

    # cli.debug("files", files)
    # cli.debug("actions", actions)
    n = 1
    for file in files:
        # only if files ends with .xml
        parser = parsers.by_filename(file)
        fd, ctcs, _ = parser.parse(file)
        # cli.debug(f"Feature Diagram: {fd}")
        # cli.debug(f"CTCs: {ctcs}")
        data = {'FeatureModel': fd, 'CTCs': ctcs, 'by': traversal_strategy}
        format_paths = []
        skip = False
        for algo_name in list(map(lambda x: x.__name__, actions['SVO']['algos'])):
            if 'pre_cl' in algo_name:
                # check if *-pre_cl-1.orders file already present (if n == 1)
                order_file_path = str(config.DIR_OUT) + os.path.sep + \
                                  str(file).replace('.xml', f'-pre_cl-{n}.orders').split(os.path.sep)[-1]
                if Path(order_file_path).is_file():
                    cli.say(f".orders file for feature model {str(file).replace('.xml', '').split(os.path.sep)[-1]}",
                            "already present, skipping...")
                    skip = True
                format_paths = bootstrap_pre_cl(config.ROOT + os.path.sep + file)
                break
            elif 'fm_traversal' in algo_name:
                format_paths = bootstrap_fm_traversal(config.ROOT + os.path.sep + file)
        if skip:
            continue
        # print('fp', format_paths)
        if len(format_paths) > 0:
            for p in format_paths:
                if 'dimacs' in p.lower():
                    data.update({'dimacs': dimacs.parse(p)})
                elif 'sxfm' in p.lower():
                    data.update({'sxfm': xml_parser.parse(p)})
                else:
                    cli.warning("Found suspicious file (format): " + p)
            pass

        cli.say("Computing static variable orders...")
        actions["SVO"]["settings"]["n"] = n
        if 'fm_traversal' in svo_name:
            fm_traversal_file_name = str(file).replace('.xml', '').split(os.path.sep)[-1] \
                                     + f'-fm_traversal_{traversal_strategy}.order'
            fm_traversal_file_path = config.DIR_OUT + os.path.sep + fm_traversal_file_name
            if Path(fm_traversal_file_path).is_file():
                cli.say(fm_traversal_file_name + ' already present, skipping')
                continue

            features = fm_traversal.run(data, traversal=traversal_strategy)
            for f in features['order']:
                for f_dimacs in data['dimacs'].variables:
                    # print('Feature', f, 'f_dimacs', f_dimacs)
                    if data['dimacs'].variables[f_dimacs]['desc'] == f['name']:
                        f.update({'dimacsIdx': data['dimacs'].variables[f_dimacs]['ID']})
                        break
            # cli.say('name, id', list(map(lambda x: x['name'] + ', ' + str(x['dimacsIdx']), features['order'])))
            open(fm_traversal_file_path, 'w').write(str(list(map(lambda x: x['dimacsIdx'], features['order']))))
        else:
            svo.compute(data, actions["SVO"])
        cli.say("Finished static variable ordering.")
    pass


def main():
    bootstrap()

    args = sys.argv
    cli.debug(args)

    files, actions = argparser.parse(args)

    cli.debug("files", files)
    cli.debug("actions", actions)

    exprs = []

    for file in files:
        parser = parsers.by_filename(file)
        expr = parser.parse(file)
        exprs.append(expr)

    cli.debug("exprs", exprs)

    if "SVO" in actions:
        cli.say("Computing static variable orders...")
        for expr in exprs:
            svo.compute(expr, actions["SVO"])
        cli.say("Finished static variable ordering.")


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
    main2()
