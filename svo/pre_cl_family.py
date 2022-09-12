# ------------------------------------------------------------------------------
# External imports #-----------------------------------------------------------
import random

# External imports #-----------------------------------------------------------
from parsers import dimacs, xml_parser
from cli import cli
from util.util import translate_xml
import os
from ddueruem import feature_model_name

# ------------------------------------------------------------------------------

STUB = "pre_cl"


# ------------------------------------------------------------------------------

def run_cached(fm, id, store, kwargs):
    store[id] = run(fm, **kwargs)


def run(fm, seed=None, **kwargs):
    print('------------------------------------------------------------------------------' +
          '------------------------------------------------------------------------------')
    root = fm[0].copy()
    ctcs = fm[1].copy()
    features = []
    model_name = feature_model_name
    model_prefix = '.xml'
    formats = ['uvl', 'dimacs', 'sxfm']
    target_folder = f'/home/eric/Uni/MA/ddueruemMA/examples/{model_name}_results'
    cli.say(f'Translating {model_name}{model_prefix} to {formats} ...')
    if e := translate_xml(f'/home/eric/Uni/MA/ddueruemMA/examples/xml/{model_name}{model_prefix}', target_folder,
                          formats) != "Successfully translated to all formats!":
        cli.error(f'For model {model_name}{model_prefix}: {e}')
        return

    cnf = dimacs.parse(f'{target_folder}{os.path.sep}{model_name}_DIMACS.dimacs')
    get_features(root, features)

    unique_ctc_features, ecr = calc_ecr(features, ctcs, True)

    ctc_clauses = get_features_from_names(
        xml_parser.parse(f'{target_folder}{os.path.sep}{model_name}_SXFM.xml')[1]['clauses'], features)

    # print(id, 'Feature Diagram:', root, '\nCTCs:', ctcs)
    # print('Store:', store, 'Settings:', kwargs)
    # print(f'Has {len(features)} distinct feature(s)')
    # print(f'CTCs: {ctcs}')

    # print(list(map(lambda x: x['name'], features)))
    # print(f'{list(map(lambda x: x["name"], ecr[0]))}\nECR: {ecr[1]}')
    s = f'[INFO]\tFeature Model \'{model_name}\' has:\n' \
        f'\t{len(features)} feature(s) and {len(ctcs)} CTC(s)\n' \
        f'\t{len(unique_ctc_features)} unique features occur in CTC(s) (Ratio: {ecr})\n' \
        f'\tAll CTCs consist of {len(ctc_clauses)} clause(s)'
    cli.say(s)
    # cli.say(f'CTCs in CNF have {len(ctc_clauses)} clauses and {len(cnf.clauses)} clauses')
    print('\n---------Pre-CL---------')
    print('clauses(names)', list(map(lambda cl: list(map(lambda l: l['name'], cl)), ctc_clauses)))
    features_with_cluster = []
    for feature in features:
        feature = feature.copy()
        # {'clusters': [{'features': set(), 'relations': list()}, ...]
        feature.update({'clusters': list()})
        features_with_cluster.append(feature)

    features_with_cluster = _create_clusters(ctc_clauses, root, features_with_cluster)
    return {
        "order": [],
        "ecr": ecr
    }


def pre_cl(order, features, by='size'):
    pass


def _pre_cl_rec(current, order, features):
    pass


def _create_clusters(ctc_clauses, root, features_with_cluster):
    for clause in ctc_clauses:
        cli.debug('---------------------------------CTC--------------------------------------------------')
        pairs = get_distinct_pairs(clause)
        for f1, f2 in pairs:
            cli.debug('For pair', (f1['name'], f2['name']))
            ancestor = find_lca(f1, f2, root, features_with_cluster)
            cli.debug('Ancestor is', ancestor['name'])
            cs = ancestor['clusters']
            if len(cs) == 0:
                cli.debug(f' Initializing cluster for ' + ancestor['name'])
                cs = _create_initial_cluster(ancestor, features_with_cluster)
            else:
                cli.debug(f' Reusing cluster for ' + ancestor['name'])
            r = roots(f1, f2, ancestor, features_with_cluster)
            cli.debug('Roots are', list(map(lambda x: x['name'], r)))
            mc = _merge_sharing_elements(cs, r)
            # add relation
            for cl in mc:
                for f in cl['features']:
                    if f['name'] in list(map(lambda x: x['name'], r)):
                        cl['relations'] = cl['relations'] + [r]
                        break

            mc_names_only = list(map(lambda c: {'features': list(map(lambda fe: fe['name'], c['features'])),
                                                'relations': list(map(lambda re: list(map(lambda ir: ir['name'], re)),
                                                                      c['relations']))}, mc))
            ancestor['clusters'] = mc
            cli.debug("MC", mc_names_only)
            cli.debug('')

    for f in features_with_cluster:
        f_clusters = list(f['clusters'])
        if len(f_clusters) > 0:
            cli.debug('For feature', f['name'])
            for c in f_clusters:
                cli.debug('F:', list(map(lambda x: x['name'], c['features'])),
                          'R:', list(map(lambda x: list(map(lambda y: y['name'], x)), c['relations'])))
    cli.debug('done')
    return features_with_cluster


def _create_initial_cluster(feature, features_with_clusters):
    clusters = []
    for child in set(feature['children']):
        child = find_feature_by_name(child, features_with_clusters)
        if not child:
            cli.debug(f"Could not find feature {feature['name']}  in features_with_clusters")
            return []
        cluster = {'features': [child], 'relations': []}
        clusters.append(cluster)
    feature['clusters'] = clusters
    return clusters


def _merge_sharing_elements(clusters, r):
    # print("CS features are", list(map(lambda x: list(map(lambda y: y['name'], x['features'])), clusters)))
    # print(len(clusters), "CS is", clusters)
    # print("R is", list(map(lambda x: x['name'], r)))
    # print("R is", roots)
    nc = {'features': [], 'relations': []}
    to_remove = []
    for cl in clusters:
        # print('cl', cl)
        for f_in_r in r:
            for f_in_cl in list(cl['features']):
                if f_in_r == f_in_cl:
                    # print('FOUND', f_in_r)
                    # print('old nc', list(nc['features']))
                    nc['features'] = nc['features'] + [f for f in cl['features'] if f not in nc['features']]
                    nc['relations'] = cl['relations']
                    # print('new nc', list(nc['features']))
                    to_remove.append(cl)
    clusters = [c for c in clusters if c not in to_remove]
    clusters.append(nc)
    # print(len(clusters), "CS is", clusters)
    return clusters


def roots(f1, f2, lca, features):
    """If lca has no children, then the roots of f1 and f2 is [lca]. Otherwise roots is list containing the
     direct children of lca which have a path to f1 or f2, respectively."""
    # print('f1:', f1['name'], ', f2:', f2['name'], ', lca:', lca['name'])
    children = list(lca['children'])
    out = []
    if len(children) == 0:
        out.append(lca)
    else:
        for child in children:
            child = find_feature_by_name(child, features)
            path = find_path(f1, child, features)
            if len(path) > 0 and child not in out:
                out.append(child)
            path = find_path(f2, child, features)
            if len(path) > 0 and child not in out:
                out.append(child)
    return out


# --------------------------------- utils ---------------------------------------------
def get_features(elem, out=None):
    """
    returns last processed element and fills out list via side effect with features
    """
    if out is None:
        out = []

    feature = {"name": elem['name']}
    children = set()
    # only add names to children ...
    for child in list(elem['children']):
        children.add(child['name'])
    feature.update({'children': children})
    out.append(feature)
    for child in list(elem['children']):
        get_features(child, out)
    return feature


def find_feature_by_name(name, features):
    found = None
    for f in features:
        if f['name'] == name:
            found = f
            break
    return found


def get_features_from_names(names, features):
    """From [['A',B],...] to e.g. [{'name':'A', 'children': set()},{'name':'B'..}, ...]"""
    return list(map(lambda cl: list(map(lambda l: list(filter(lambda x: x['name'] == l, features))[0], cl)), names))


def get_ctc_features(ctc, out=None):
    """Returns feature names of a single cross tree constraint"""
    if out is None:
        out = []
    for key in ctc:
        if ctc[key] == 'var':
            feature = ctc['feature']
            if feature not in out:
                out.append(feature)
        if key == 'children':
            for child in list(ctc['children']):
                get_ctc_features(child, out)
    pass


def calc_ecr(features, ctcs, with_features=False):
    """Returns ECR or (with_features=True) list containing all features in CTCs and ECR"""
    features_in_ctcs = []
    for i in range(0, len(ctcs)):
        features_in_ctc = []
        get_ctc_features(ctcs[f"rule-{i}"], features_in_ctc)
        # Features per CTC
        features_in_ctcs.append(features_in_ctc)
    distinct_features = list(dict.fromkeys([f for sub in features_in_ctcs for f in sub]))
    ecr = len(distinct_features) / len(features)
    if with_features:
        # map feature names into actual features
        distinct_features = [x for x in features if x['name'] in distinct_features]
        return distinct_features, ecr
    else:
        return [], ecr


def find_path(feature, root, features):
    """Find path from root to current feature node. If a path exists it returns a list representing this path or
    an empty list otherwise"""
    path = []
    if x := _find_path(feature, root, features, path):
        return path
    return []


def _find_path(feature, root, features, parents=None):
    """
    Find the path from root to current feature node.
    Returns True if path exists and always fills parents list via side effect with nodes in the path
    starting from the searched feature and ending at root
    """
    if len(parents) == 0:
        parents.append(feature)
    # there can be only be exactly one parent
    found = [f for f in features if feature['name'] in set(f['children'])]
    if len(found) == 0:
        return False
    elif feature['name'] is not root['name']:
        parent = found[0]
    else:
        parent = root
    parents.append(parent)
    if parent['name'] is root['name']:
        return True
    else:
        out = _find_path(parent, root, features, parents)
        return out


def find_lca(f1, f2, root, features):
    """find lowest common ancestor of two features. A feature can be an ancestor of itself"""
    path1 = []
    if not _find_path(f1, root, features, path1):
        cli.error(f'Could not find path in FD for feature {f1}')
        return
    path2 = []
    if not _find_path(f2, root, features, path2):
        cli.error(f'Could not find path in FD for feature {f2}')
        return
    return [f for f in path1 if f in path2][0]


def get_distinct_pairs(clause):
    """Returns list of distinct (1,2) == (2,1) pairs"""
    return [(a, b) for idx, a in enumerate(clause) for b in clause[idx + 1:]]
