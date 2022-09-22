from datetime import datetime, timedelta

# ------------------------------------------------------------------------------
# Internal imports #-----------------------------------------------------------

from cli import cli
from svo import random

STUB = "force"


def run_cached(expr, id, store, kwargs):
    store[id] = run(expr, **kwargs)


def run(expr, order=None, seed=None, time_run=60, **kwargs):
    if not order:
        order = random.run(expr, seed)["order"]

    clauses = expr.clauses

    span = compute_span(clauses, order)

    now = datetime.now()

    while True:  # datetime.now() - now < timedelta(seconds=time_run):
        cogs_v = {}
        span_old = span

        for i, clause in enumerate(clauses):
            cogs = compute_cog(clause, order)

            for x in clause:
                x = abs(x)
                if x in cogs_v:
                    a, b = cogs_v[x]
                    cogs_v[x] = (a + cogs, b + 1)
                else:
                    cogs_v[x] = (cogs, 1)

        tlocs = []
        for key, value in cogs_v.items():
            center, n = value
            tlocs.append((key, center / n))

        tlocs = sorted(tlocs, key=lambda x: x[1])

        order = [x[0] for x in tlocs]
        span = compute_span(clauses, order)

        if span_old == span:
            break

    return {
        "order": order,
        "span": span,
        "dist": sum(compute_inner_dists(clauses, order))
    }


def compute_cog(clause, order):
    cog = sum([order.index(abs(x)) for x in clause])

    return cog / len(clause)


def compute_span(clauses, order):
    span = []
    for clause in clauses:
        lspan = 0
        indizes = [order.index(abs(x)) for x in clause]
        lspan = max(indizes) - min(indizes)

        span.append(lspan)

    return sum(span)


def compute_inner_dists(clauses, order):
    inner_dists = []

    for clause in clauses:

        dist = 0

        for i, x in enumerate(clause):
            x = abs(x)

            for y in clause[i + 1:]:
                y = abs(y)
                dist += abs(order.index(x) - order.index(y))

        inner_dists.append(dist)

    return inner_dists
