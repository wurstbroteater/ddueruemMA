"""
!!!Warning!!!
The xml.etree.ElementTree module is not secure against maliciously constructed data!
If you need to parse untrusted or unauthenticated data,
see https://docs.python.org/3/library/xml.html#xml-vulnerabilities
"""

# ------------------------------------------------------------------------------
# External imports #-----------------------------------------------------------
from os import path
import xml.etree.ElementTree as xmlTree

# ------------------------------------------------------------------------------
# Internal imports #-----------------------------------------------------------
from cli import cli
from util.util import hash_hex

# ------------------------------------------------------------------------------
# Plugin Properties #----------------------------------------------------------
STUB = "xml"

name = "XML Feature Model Parser"
parses = [".xml"]


# ------------------From XML to JSON ------------------
def _parse_xml_feature(item):
    """
    E.g. returns:
     element = {
        "type": "alt",
        "abstract": True,
        "mandatory": True,
        "name": "someName", # can be used as id and is case-sensitive
        "children": []

    """
    as_dict = {"type": item.tag}
    as_dict.update(item.attrib)
    children = []
    # print(f"elem: {children}\t\t{as_dict['type']}")
    for child in list(item):
        to_append = _parse_xml_feature(child)
        if len(to_append) > 0:
            children.append(to_append)
    as_dict.update({"children": children})
    # ignore <graphics key=".." value=".."/>
    return {} if item.tag == 'graphics' else as_dict


def _parse_xml_constraint(item):
    """
    E.g. returns:
     element = {
        "type": "rule",
        "feature": NAME,  # ONLY IF type == var
        "children": []

    """
    # print(item.tag, item)
    if item.tag == 'rule':
        item = list(item)[0]
    as_dict = {"type": item.tag}
    if item.tag == 'var':
        as_dict.update({"feature": item.text})
    else:
        children = []
        for child in list(item):
            children.append(_parse_xml_constraint(child))
        as_dict.update({"children": children})
    return as_dict


def _parse_sxfm_constraint(item):
    """
    E.g. returns:
    list of lists. Each inner list is 1 clause from the constraints without negation indicator for the included feature names
    """
    # create list for each clause without leading e.g. C1:
    clauses = list(map(lambda clause: clause.split(':', 1)[1],
                       list(filter(None, list(map(lambda lines: lines.strip(), item.split('\n')))))))
    # remove negation indicators
    clauses = list(map(lambda x: x.replace('~', ''), clauses))
    # From ['X or Y', 'A or B'] to [['X','Y'], ['A','B']]
    clauses = list(map(lambda x: list(map(lambda inner: inner.strip(), x.split(' or '))), clauses))
    return clauses


def _parse_element(element, fun=_parse_xml_feature):
    response = {}
    if fun is _parse_sxfm_constraint:
        response.update({'clauses': _parse_sxfm_constraint(element.text)})
    else:
        for child in list(element):
            element_as_dict = fun(child)
            if fun is _parse_xml_constraint:
                element_as_dict = {f"rule-{list(element).index(child)}": element_as_dict}
            if len(element_as_dict) > 0:
                response.update(element_as_dict)
    return response


def parse(file, is_file_path=True):
    """
    If is_file_path is set to True (also per default), the file parameter will be interpreted as
    String containing the XML content, otherwise it will be interpreted as path to a file.
    """
    if is_file_path:
        root = xmlTree.parse(file).getroot()
    else:
        root = xmlTree.fromstring(file)

    # print(f"root: {root.tag}, size: {len(root)}")
    malformed = True
    feature_dia = {}
    ctcs = {}
    has_struct = len([f for f in root.iter() if f.tag == 'struct'])
    has_feature_tree = len([f for f in root.iter() if f.tag == 'feature_tree'])
    if has_struct > 0 and has_feature_tree == 0:
        # parse as FeatureIDE Feature Model xml
        cli.debug('XML is FeatureIDE Feature Model xml')
        for child in root.iter():
            if child.tag == 'struct':
                feature_dia.update(_parse_element(child))
            if child.tag == 'constraints':
                ctcs.update(_parse_element(child, _parse_xml_constraint))
    elif has_struct == 0 and has_feature_tree > 0:
        # parse as SXFM Feature Model xml
        cli.debug('XML is SXFM Feature Model xml')
        for child in root.iter():
            if child.tag == 'feature_tree':
                # feature_dia.update(_parse_element(child))
                pass
            if child.tag == 'constraints':
                ctcs.update(_parse_element(child, _parse_sxfm_constraint))
    else:
        cli.error('Unable to parse xml because of unknown format')
    meta = {"input-filename": path.basename(file), "input-filehash": hash_hex(file)}

    return [feature_dia, ctcs, meta]
