# ------------------------------------------------------------------------------
# External imports #-----------------------------------------------------------
import random

# ------------------------------------------------------------------------------

STUB = "random"


# ------------------------------------------------------------------------------

def run_cached(expr, id, store, kwargs):
    store[id] = run(expr, **kwargs)


def run(expr, seed=None, **kwargs):
    if seed:
        random.seed(seed)

    order = asc_by_id(expr)
    random.shuffle(order)

    return {"order": order}


def asc_by_id(expr):
    return [x + 1 for x in range(0, len(expr.variables))]
