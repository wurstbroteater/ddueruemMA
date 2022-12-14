# ------------------------------------------------------------------------------
"""
This is the implementation of Pre-Cl-Family heuristic as it is described
in the dissertation of Marcilio Mendonca
https://central.bac-lac.gc.ca/.item?id=TC-OWTU-4201&op=pdf&app=Library&oclc_number=613414464
"""
# External imports #-----------------------------------------------------------
from datetime import datetime
# External imports #-----------------------------------------------------------
from cli import cli
from util.formats import CNF
from . import force

# ------------------------------------------------------------------------------
STUB = "pre_cl"


# ------------------------------------------------------------------------------

def run_cached(data, id, store, kwargs):
    store[id] = run(data, **kwargs)


def run(data, **kwargs):
    root = data['FeatureModel'].copy()
    ctcs = data['CTCs'].copy()
    cnf = data['dimacs']
    by = data['by']
    ctcs_as_cnf = data['sxfm'][1]['clauses']
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
    force_log = None
    if 'min_span' in by:
        force_log = []
    pre_cl(find_feature_by_name(root['name'], features_with_cluster), features_with_cluster, order, cnf, force_log, by)
    end_pre_cl = datetime.now()

    if (l_o := len(order)) != (l_v := len(cnf.variables)):
        cli.warning('Order contains', l_o, 'vars from total of', l_v)
    out = {
        'order': list(map(lambda x: x['dimacsIdx'], order)),
        'time_clustering': [start_clustering, end_clustering, end_clustering - start_clustering],
        'time_pre_cl': [start_pre_cl, end_pre_cl, end_pre_cl - start_pre_cl],
        'vars': len(order),
        'ctcs': len(ctcs),
        'clauses': len(ctcs_as_cnf),
        'by': by,
        'ecr': ecr,
        # 'clusters': print_clusters(features_with_cluster, False).replace('\n', '--'),
        'cluster_size_per_feature': get_cluster_size_per_feature(features_with_cluster)
    }
    if force_log is not None:
        out['force_log'] = force_log
    return out


def pre_cl(feature, features_with_clusters, order, cnf, force_log=None, by='size'):
    order.append(feature)
    f_clusters = list(feature['clusters'])
    # ASC sort by cluster size
    f_clusters.sort(key=lambda x: get_cluster_size(x, features_with_clusters), reverse=False)

    for cluster in f_clusters:
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

        elif by.lower() == 'min_span':
            # Create necessary data structure for class CNF
            if len(cluster['relations']) > 0:
                # sorted according to dimacsIdx to reflect hierarchy
                cluster['features'] = sorted(cluster['features'], key=lambda x: x['dimacsIdx'], reverse=False)
                cnf_vars = {}
                for i_f, f in enumerate(cluster['features']):
                    cnf_vars[str(i_f + 1)] = {'ID': i_f + 1, 'desc': f['name']}

                cnf_clauses = []
                for r in cluster['relations']:
                    cl = []
                    for f_name in list(map(lambda x: x['name'], r)):
                        id = '-1'
                        for k in cnf_vars:
                            if f_name == cnf_vars[k]['desc']:
                                id = cnf_vars[k]['ID']
                                break
                        if id == -1:
                            cli.error('Could not find feature with name ' + f_name + ' in cnf_vars')
                            return
                        cl.append(id)
                    cnf_clauses.append(cl)

                force_order = []
                for f_name in list(map(lambda x: x['name'], cluster['features'])):
                    id = -1
                    for k in cnf_vars:
                        if f_name == cnf_vars[k]['desc']:
                            id = cnf_vars[k]['ID']
                            break
                    if id == -1:
                        cli.error('Could not find feature with name ' + f_name + ' in cnf_vars')
                        return
                    force_order.append(id)
                # This cnf does not have negated literals.
                # This is fine because we just want to reflect relatedness of variables
                fo = force.run(expr=CNF(clauses=cnf_clauses, variables=cnf_vars), order=force_order, time_run=-1)
                if force_log is not None:
                    force_log.append(fo)
                fo = fo['order']
                if (fo_l := len(fo)) != (vars_len := len(cnf_vars)):
                    cli.warning(f'For force order size {fo_l} differ from number of variables {vars_len}')
                # IDs to feature names
                fo_names = []
                for v_id in fo:
                    for k in cnf_vars:
                        if cnf_vars[k]['ID'] == v_id:
                            fo_names.append(cnf_vars[k]['desc'])
                            break
                cluster['features'] = list(map(lambda x: find_feature_by_name(x, features_with_clusters), fo_names))
        else:
            cli.error(f'Unknown sorting strategy: {by}')
            return

        for f in cluster['features']:
            pre_cl(f, features_with_clusters, order, cnf, by)
    pass


def _create_clusters(ctc_clauses, root, features_with_cluster):
    for clause in ctc_clauses:
        pairs = get_distinct_pairs(clause)
        for f1, f2 in pairs:
            ancestor = find_lca(f1, f2, root, features_with_cluster)
            cs = ancestor['clusters']
            if len(cs) == 0:
                cs = _create_initial_cluster(ancestor, features_with_cluster)
            else:
                pass
            r = roots(f1, f2, ancestor, features_with_cluster)
            mc = _merge_sharing_elements(cs, r)
            # add relation
            for cl in mc:
                for f in cl['features']:
                    if f['name'] in list(map(lambda x: x['name'], r)):
                        cl['relations'] = cl['relations'] + [r]
                        break

            ancestor['clusters'] = mc

    # create cluster for all features with no cluster
    for f in features_with_cluster:
        f_clusters = list(f['clusters'])
        if len(f_clusters) == 0:
            _create_initial_cluster(f, features_with_cluster)

    return features_with_cluster


def _create_initial_cluster(feature, features_with_clusters):
    clusters = []
    for child in list(feature['children']):
        child = find_feature_by_name(child, features_with_clusters)
        if not child:
            cli.error(f"Could not find feature {feature['name']}  in features_with_clusters")
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
        for f_in_r in r:
            for f_in_cl in list(cl['features']):
                if f_in_r == f_in_cl:
                    nc['features'] = nc['features'] + [f for f in cl['features'] if f not in nc['features']]
                    nc['relations'] = cl['relations'] + [f for f in nc['relations'] if f not in cl['relations']]
                    to_remove.append(cl)
    clusters = [c for c in clusters if c not in to_remove]
    clusters.append(nc)
    return clusters


def roots(f1, f2, lca, features):
    """If lca has no children, then the roots of f1 and f2 is [lca]. Otherwise roots is list containing the
     direct children of lca which have a path to f1 or f2, respectively."""
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
    Returns last processed element and fills out list via side effect with features
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
    """
    Returns the feature with the given name from the features list or None if it is not in the list.
    A Feature may look like f = {'name': 'Aa', cluster:[..],...}. The parameter name matches against the name of the f"""
    found = None
    for f in features:
        if f['name'] == name:
            found = f
            break
    return found


def get_features_from_names(names, features):
    """
    From [['A','B'],...] to e.g. [[{'name':'A', 'children':list()}],[{'name':'B'..}], ...] or
    From ['A','B',...] to e.g. [[{'name':'A', 'children':list()}],[{'name':'B'..}], ...]"""
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
        cli.error(f'Could not find path in FD for feature {f1} with root {root}')
        return
    path2 = []
    if not _find_path(f2, root, features, path2):
        cli.error(f'Could not find path in FD for feature {f2} with root {root}')
        return
    return [f for f in path1 if f in path2][0]


def get_distinct_pairs(clause):
    """Returns list of distinct (1,2) == (2,1) pairs"""
    return [(a, b) for idx, a in enumerate(clause) for b in clause[idx + 1:]]


def get_cluster_size(cluster, features_with_clusters):
    """Returns the sum of all (recursive) children cluster sizes"""
    features = list(cluster['features'])
    size = len(features)
    for feature in features:
        size = size + _get_cluster_size(feature, features_with_clusters)
    return size


def _get_cluster_size(feature, features_with_clusters):
    """get_cluster_size helper """
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


def get_cluster_size_per_feature(feature_with_clusters):
    """Receives list of features with clusters and returns a String containing the dimacsId and cluster
     size for each feature, e.g. for feature r with id 1 and 14 cluster, the output could look like 1:14.
     If there more than one feature, the outputs are separated by -."""
    out = ''
    for i_f, f in enumerate(feature_with_clusters):
        out += f"{f['dimacsIdx']}:{_get_cluster_size(f, feature_with_clusters)}"
        if i_f != len(feature_with_clusters) - 1:
            out += '-'
    return out


def print_clusters(features_with_clusters, print_it=True):
    """
    The respective clusters for every feature are printed only with feature names.
    If print_it is set to False the method just returns the String.
    Example: Feature x has two clusters, one with the the variables a,b and one with c.
        The output could looks like
    cluster-x1: F={ a, b }, R={ [a, b] }
    cluster-x2: F={ c }, R={ }
    """
    out = ''
    for f in features_with_clusters:
        for i_c, c in enumerate(f['clusters']):
            out += 'cluster-' + f['name'] + str(i_c + 1) + '= F={ '
            for i_cf, cf in enumerate(c['features']):
                out += cf['name'] + (', ' if i_cf != len(c['features']) - 1 else '')
            out += ' }, R={ '
            for i_cr, cr in enumerate(c['relations']):
                out += str(list(map(lambda x: x['name'], cr))).replace('\'', '') + (
                    ', ' if i_cr != len(c['relations']) - 1 else '')
            out += ' }\n'
    # normalize whitespaces (this also removes \n, so we have to add it again)
    out = " ".join(out.split()).replace('} c', '}\nc')
    if print_it:
        print(out)
    return out
