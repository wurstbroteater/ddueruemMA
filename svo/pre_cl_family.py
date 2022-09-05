# ------------------------------------------------------------------------------
# External imports #-----------------------------------------------------------
import random

# ------------------------------------------------------------------------------

STUB = "pre_cl"


# ------------------------------------------------------------------------------

def run_cached(expr, id, store, kwargs):
    fd = expr[0]
    ctcs = expr[1]
    print('------------------------------------------------------------------------------' +
          '------------------------------------------------------------------------------')
    print(fd, '\n', ctcs)
    print(id)
    print(store)
    print(kwargs)
    pass


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
