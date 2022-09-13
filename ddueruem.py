#!/usr/bin/env python3

"""

"""

# ------------------------------------------------------------------------------
# External imports #-----------------------------------------------------------
import os
from os import path
from pathlib import Path
import sys

# ------------------------------------------------------------------------------
# Internal imports #-----------------------------------------------------------
import config
from util import util
from cli import cli, argparser
from parsers import parsers, dimacs, xml_parser
from svo import svo

# ------------------------------------------------------------------------------
# feature_model_name = 'busybox1dot18dot0'
# feature_model_name = 'npc'
# feature_model_name = 'anyvend'
feature_model_name = 'mendonca_dis'


# feature_model_name = 'automotiv2v4'


def main2():
    bootstrap()
    # args = sys.argv
    name = feature_model_name + '.xml'
    args = ['./ddueruem.py', 'examples/xml/' + name, '--svo', 'pre_cl']
    # args = ['./ddueruem.py', 'examples/xml/anyvend.xml', 'examples/xml/npc.xml', 'examples/xml/mendonca_dis.xml', 'examples/xml/automotiv2v4.xml' '--svo', 'pre_cl']
    cli.debug('args', args)

    files, actions = argparser.parse(args)

    cli.debug("files", files)
    cli.debug("actions", actions)

    data = {}
    for file in files:
        # only if files ends with .xml
        parser = parsers.by_filename(file)
        fd, ctcs, _ = parser.parse(file)
        cli.debug(f"Feature Diagram: {fd}")
        cli.debug(f"CTCs: {ctcs}")
        data = {'FeatureModel': fd, 'CTCs': ctcs, 'by': 'size'}
        format_paths = []
        for algo_name in list(map(lambda x: x.__name__, actions['SVO']['algos'])):
            if 'pre_cl' in algo_name:
                format_paths = bootstrap_pre_cl(config.ROOT + os.path.sep + file)
                break
        if len(format_paths) > 0:
            for p in format_paths:
                if 'dimacs' in p.lower():
                    data.update({'dimacs': dimacs.parse(p)})
                elif 'sxfm' in p.lower():
                    data.update({'sxfm': xml_parser.parse(p)})
                else:
                    cli.warning("Found suspicious file (format): " + p)
            pass
        cli.debug("Feature model", data['FeatureModel'])

    cli.say("Computing static variable orders...")
    n = 1
    actions["SVO"]["settings"]["n"] = n
    svo.compute(data, actions['SVO'])
    cli.say("Finished static variable ordering.")


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
