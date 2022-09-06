# ------------------------------------------------------------------------------
# External imports #-----------------------------------------------------------
import random

# External imports #-----------------------------------------------------------
from parsers.dimacs import parse
from cli import cli

# ------------------------------------------------------------------------------

STUB = "pre_cl"


# ------------------------------------------------------------------------------

def run_cached(fm, id, store, kwargs):
    store[id] = run(fm, **kwargs)


def run(fm, seed=None, **kwargs):
    root = fm[0].copy()
    ctcs = fm[1].copy()
    features = []
    cnf = parse('examples/npc.dimacs')
    get_features(root, features)
    ecr = calc_ecr(features, ctcs, True)

    print('------------------------------------------------------------------------------' +
          '------------------------------------------------------------------------------')
    # print(id, 'Feature Diagram:', root, '\nCTCs:', ctcs)
    # print('Store:', store, 'Settings:', kwargs)
    # print(f'Has {len(features)} distinct feature(s)')
    # print(f'CTCs: {ctcs}')

    # print(list(map(lambda x: x['name'], features)))
    # print(f'{list(map(lambda x: x["name"], ecr[0]))}\nECR: {ecr[1]}')
    s = f'FM has {len(ctcs)} CTCs and {len(features)} features from which {len(ecr[0])} occur in CTCs (ratio: {ecr[1]})'
    cli.say(s)
    cli.say(f'CNF has {cnf.get_no_variables()} vars and {len(cnf.clauses)} clauses')

    # clauses with feature names (ignoring potential not before feature)
    clauses = list(map(lambda cl: list(map(lambda l: cnf.variables[abs(l)]['desc'], cl)), cnf.clauses))
    ec_names = list(map(lambda cl: cl['name'], ecr[0]))
    c = []
    for clause in clauses:
        for literal in clause:
            if literal in ec_names:
                c.append(clause)
                break
    # clauses with variable names affected by ctcs
    clauses = c
    del c
    # replace feature names by actual features
    clauses = list(
        map(lambda cl: list(map(lambda l: list(filter(lambda x: x['name'] == l, features))[0], cl)), clauses))
    # only names
    # print('clauses', list(map(lambda cl:list(map(lambda l: l['name'],cl)),clauses)))
    clusters = []
    for clause in clauses:
        pairs = get_distinct_pairs(clause)
        for f1, f2 in pairs:
            pair = (f1, f2)
            ancestor = find_lca(f1, f2, root, features)
            print('pair', (f1['name'], f2['name']))
            print('lca for', (f1['name'], f2['name']), 'is', ancestor['name'])

        break

    # for f in ec:

    f1 = [x for x in features if x['name'] == 'Pasta'][0]
    f2 = [x for x in features if x['name'] == 'SWING'][0]

    lca = find_lca(f1, f2, root, features)

    # print(ecr[0])
    return {
        "order": [],
        "ecr": ecr
    }


def pre_cl(order, features, by='size'):
    pass


def _pre_cl_rec(current, order, features):
    pass


def _create_clusters(feature):
    pass


def _create_initial_cluster(feature):
    clusters = []
    for child in set(feature['children']):
        clusters.append([child])
    return clusters


def _merge_sharing_elements(root, cluster):
    pass


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
        return [distinct_features, ecr]
    else:
        return ecr


def _find_path(feature, root, features, parents=None):
    """
    Find the path from root to current feature node.
    Returns True if path exists and fills parents list via side effect with nodes in the path
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
    """find lowest common ancestor of two features"""
    path1 = []
    if not _find_path(f1, root, features, path1):
        cli.error(f'Could not find path in FD for feature {f1}')
        return
    path2 = []
    if not _find_path(f2, root, features, path2):
        cli.error(f'Could not find path in FD for feature {f2}')
        return
    print(path2)
    return [f for f in path1 if f in path2][0]


def get_distinct_pairs(clause):
    """Returns list of distinct (1,2) == (2,1) pairs"""
    return [(a, b) for idx, a in enumerate(clause) for b in clause[idx + 1:]]


# -----------------------data structures
class Cluster:

    def __init__(self, features, relations, **kwargs):
        self.features = features
        self.relations = relations
        self.stub = "Cluster"

    def __str__(self):
        return self.stub + " " + str(self.features) + " " + str(self.relations)
