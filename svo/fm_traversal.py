from datetime import datetime, timedelta

# ------------------------------------------------------------------------------
# Internal imports #-----------------------------------------------------------

from cli import cli
from svo import random

STUB = "fm_traversal"


def run_cached(data, id, store, kwargs):
    store[id] = run(data, **kwargs)


def run(data, by='bf', **kwargs):
    """
    traversal can be 'bf', 'df', 'in', 'pre', 'post'
    """
    fm = data['FeatureModel']
    order = []
    start = datetime.now()
    if by.lower() == 'bf':
        order = _bf_fm_traversal(fm)
    elif by.lower() == 'df':
        order = _df_fm_traversal(fm)
    elif by.lower() == 'in':
        raise NotImplementedError('in-order traversal not implemented yet')
    elif by.lower() == 'pre':
        raise NotImplementedError('pre-order traversal not implemented yet')
    elif by.lower() == 'post':
        raise NotImplementedError('post-order traversal not implemented yet')
    else:
        cli.warning('Found unknown traversal strategy: ' + by)
    end = datetime.now()
    for i, f in enumerate(order):
        id = -1
        for k in data['dimacs'].variables:
            if f['name'] == data['dimacs'].variables[k]['desc']:
                id = data['dimacs'].variables[k]['ID']
                break
        if id == -1:
            cli.error("Could not find id for " + f['name'])
            return
        order[i] = id
    return {
        "order": order,
        't': end - start,
        'by': by
    }


def _df_fm_traversal(node, out=None):
    """Returns list of (feature tree) nodes induced by depth first traversal of the feature tree"""
    if not out:
        out = []
    out.append(node)
    children = list(node['children'])
    for child in children:
        _df_fm_traversal(child, out)
    return out


def _bf_fm_traversal(node):
    """Returns list of (feature tree) nodes induced by breadth first traversal of the feature tree"""
    if node is None:
        return
    queue = [node]
    out = []
    while len(queue) > 0:
        current = queue.pop(0)
        out.append(current)
        children = list(current['children'])
        if len(children) > 0:
            for child in children:
                queue.append(child)

    return out
