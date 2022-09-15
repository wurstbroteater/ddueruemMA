# ------------------------------------------------------------------------------
# External imports #-----------------------------------------------------------
from datetime import datetime, timedelta
# External imports #-----------------------------------------------------------
import ddueruem
from cli import cli
from ddueruem import feature_model_name
from . import force

# ------------------------------------------------------------------------------
STUB = "pre_cl"


# ------------------------------------------------------------------------------

def run_cached(data, id, store, kwargs):
    store[id] = run(data, **kwargs)


def run(data, seed=None, **kwargs):
    cli.say('------------------------------------------------------------------------------' +
            '------------------------------------------------------------------------------')
    root = data['FeatureModel'].copy()
    ctcs = data['CTCs'].copy()
    cnf = data['dimacs']
    by = data['by']
    ctcs_as_cnf = data['sxfm'][1]['clauses']
    model_name = feature_model_name
    features = []
    get_features(root, features)
    # add dimacs IDs for faster translation between FORCE and Pre-CL
    for f in features:
        for f_dimacs in cnf.variables:
            if cnf.variables[f_dimacs]['desc'] == f['name']:
                f.update({'dimacsIdx': cnf.variables[f_dimacs]['ID']})
                break

    unique_ctc_features, ecr = calc_ecr(features, ctcs, True)
    ctc_clauses = get_features_from_names(ctcs_as_cnf, features)

    s = f'[INFO]\tFeature Model \'{model_name}\' has:\n' \
        f'\t{len(features)} feature(s) and {len(ctcs)} CTC(s)\n' \
        f'\t{len(unique_ctc_features)} unique features occur in CTC(s) (Ratio: {ecr})\n' \
        f'\tAll CTCs consist of {len(ctc_clauses)} clause(s)'
    cli.debug(s)
    cli.debug('\n---------Pre-CL---------')
    cli.debug('clauses(names)', list(map(lambda cl: list(map(lambda l: l['name'], cl)), ctc_clauses)))
    features_with_cluster = []
    for feature in features:
        feature = feature.copy()
        feature.update({'clusters': list()})
        features_with_cluster.append(feature)

    start_clustering = datetime.now()
    features_with_cluster = _create_clusters(ctc_clauses, root, features_with_cluster)
    end_clustering = datetime.now()
    order = []
    start_pre_cl = datetime.now()
    pre_cl(find_feature_by_name(root['name'], features_with_cluster), features_with_cluster, order, cnf, by)
    end_pre_cl = datetime.now()
    # print('Pre-CL-' + str(by), 'ordering is:')
    # print(list(map(lambda x: x['dimacsIdx'], order)))
    if ddueruem.feature_model_name == 'mendonca_dis':
        if by == 'size':
            expected = ['r', 'c', 'i', 'j', 'a', 'd', 'b', 'e', 'g', 'h', 'f', 'l', 'm', 'k', 'n']
            print('eq?', expected == list(map(lambda x: x['name'], order)), expected)
        elif by == 'min-span':
            expected = ['r', 'c', 'i', 'j', 'a', 'b', 'e', 'g', 'h', 'f', 'l', 'm', 'k', 'n', 'd']
            print('eq?', expected == list(map(lambda x: x['name'], order)), expected)
    if (l_o := len(order)) != (l_v := len(cnf.variables)):
        cli.warning('Order contains', l_o, 'vars from total of', l_v)
    return {
        'order': list(map(lambda x: x['dimacsIdx'], order)),
        #'features_with_cluster': features_with_cluster,
        'time_clustering': [start_clustering, end_clustering, end_clustering - start_clustering],
        'time_pre_cl': [start_pre_cl, end_pre_cl, end_pre_cl - start_pre_cl],
        'by': by,
        'ecr': ecr
    }


def pre_cl(feature, features_with_clusters, order, cnf, by='size'):
    order.append(feature)
    f_clusters = list(feature['clusters'])
    # print('Feature', feature['name'], 'has', len(f_clusters), 'cluster(s)')
    # ASC sort by cluster size
    f_clusters.sort(key=lambda x: get_cluster_size(x, features_with_clusters), reverse=False)

    for cluster in f_clusters:
        # print('F:', list(map(lambda x: x['name'], cluster['features'])),
        #      'R:', list(map(lambda x: list(map(lambda y: y['name'], x)), cluster['relations'])),
        #      ', size:', get_cluster_size(cluster, features_with_clusters))
        if by.lower() == 'size':
            temp_c = list(cluster['features'])
            temp_c.sort(key=lambda x: get_subtree_size(x, features_with_clusters))
            cluster['features'] = temp_c

            if len(cluster['features']) > 1:
                # for all features with the same subtree_size, arrange them according to their dimacsIdx
                new_cluster = []
                first = cluster['features'][0]
                size = get_subtree_size(first, features_with_clusters)
                rearrange = [first]
                for f in cluster['features'][1::]:
                    if size == get_subtree_size(f, features_with_clusters):
                        rearrange.append(f)
                        continue
                    rearrange.sort(key=lambda x: x['dimacsIdx'])
                    new_cluster = new_cluster + rearrange
                    size = get_subtree_size(f, features_with_clusters)
                    rearrange = [f]
                cluster['features'] = new_cluster + [f for f in rearrange if f not in new_cluster]

            # print('ASC by subtree size',list(map(lambda x: (x['name'], get_subtree_size(x, features_with_clusters)), cluster['features'])))
        elif by.lower() == 'min_span':
            # TODO: WIP
            # ['r', 'c', 'i', 'j', 'd', 'a', 'b', 'e', 'g', 'h', 'f', 'l', 'm', 'k', 'n']
            # order = [1, 12, 13, 14, 15, 2, 3, 4, 10, 11, 5, 7, 8, 6, 9]
            print(list(map(lambda x: x['name'], order)))
            # order = [1, 12, 13, 14, 15, 2, 3, 4, 10, 11, 5, 7, 8, 6, 9]
            print('min_span')
            order = force.run(cnf, order)['order']
            print('force', order)
            return
        else:
            cli.error(f'Unknown sorting strategy: {by}')
            return

        for f in cluster['features']:
            pre_cl(f, features_with_clusters, order, cnf, by)
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

            mc_names_only = list(map(lambda cc: {'features': list(map(lambda fe: fe['name'], cc['features'])),
                                                 'relations': list(map(lambda re: list(map(lambda ir: ir['name'], re)),
                                                                       cc['relations']))}, mc))
            ancestor['clusters'] = mc
            cli.debug("MC", mc_names_only)
            cli.debug('')
    # just for pretty printing
    for f in features_with_cluster:
        f_clusters = list(f['clusters'])
        if len(f_clusters) > 0:
            cli.debug('For feature', f['name'])
            for c in f_clusters:
                cli.debug('F:', list(map(lambda x: x['name'], c['features'])),
                          'R:', list(map(lambda x: list(map(lambda y: y['name'], x)), c['relations'])))

    # create cluster for all features with no cluster
    for f in features_with_cluster:
        f_clusters = list(f['clusters'])
        if len(f_clusters) == 0:
            _create_initial_cluster(f, features_with_cluster)

    cli.debug('done')
    return features_with_cluster


def _create_initial_cluster(feature, features_with_clusters):
    clusters = []
    for child in list(feature['children']):
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
    children = list()
    # only add names to children ...
    for child in list(elem['children']):
        if child not in children:
            children.append(child['name'])
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
    """
    From [['A','B'],...] to e.g. [{'name':'A', 'children':list()},{'name':'B'..}, ...] or
    From ['A','B',...] to e.g. [{'name':'A', 'children':list()},{'name':'B'..}, ...]"""
    # TODO: Optimize this method
    is_list = False
    out = []
    for n in names:
        is_list = type(n) is list
        if not is_list:
            for f in features:
                if f['name'] == n:
                    out.append([f])

    if is_list:
        foo = list(map(lambda cl: list(map(lambda l: list(filter(lambda x: x['name'] == l, features))[0], cl)), names))
        return foo
    return out


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
    if _find_path(feature, root, features, path):
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
    found = [f for f in features if feature['name'] in list(f['children'])]
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


def get_cluster_size(cluster, features_with_clusters):
    features = list(cluster['features'])
    size = len(features)
    for feature in features:
        size = size + _get_cluster_size(feature, features_with_clusters)
    return size


def _get_cluster_size(feature, features_with_clusters):
    children = list(feature['children'])
    size = 0
    if len(children) > 0:
        features = get_features_from_names(children, features_with_clusters)
        size = len(features)
        for f in features:
            # unpack
            f = f[0]
            size = size + _get_cluster_size(f, features_with_clusters)
    return size


def get_subtree_size(feature, features_with_clusters):
    """Returns sum of all recursive children of feature aka subtree size"""
    children = list(feature['children'])
    size = len(children)
    if size > 0:
        for child in children:
            child = find_feature_by_name(child, features_with_clusters)
            size = size + get_subtree_size(child, features_with_clusters)
    return size
