# ------------------------------------------------------------------------------
# External imports #-----------------------------------------------------------
import random

# ------------------------------------------------------------------------------

STUB = "pre_cl"


# ------------------------------------------------------------------------------

def run_cached(expr, id, store, kwargs):
    root = expr[0].copy()
    ctcs = expr[1].copy()
    features = []
    get_features(root, features)
    print('------------------------------------------------------------------------------' +
          '------------------------------------------------------------------------------')
    print(id, 'Feature Diagram:', root, '\nCTCs:', ctcs)
    print('Store:', store, 'Settings:', kwargs)
    print(f'Has {len(features)} distinct feature(s)')
    # print(f'CTCs: {ctcs}')
    print(f'ECR: {calc_ecr(features, ctcs)}')


def run(expr, seed=None, **kwargs):
    pass


def pre_cl(order, features, by='size'):
    pass


def _pre_cl_rec(current, order, features):
    pass


def _create_clusters(ctc, clusters):
    pass


def _create_initial_cluster(ctc, clusters):
    pass


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
    """Returns features of a single cross tree constraint"""
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
    if with_features:
        return [distinct_features,len(distinct_features) / len(features)]
    else:
        return len(distinct_features) / len(features)
