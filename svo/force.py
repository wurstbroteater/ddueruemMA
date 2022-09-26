from datetime import datetime, timedelta

# ------------------------------------------------------------------------------
# Internal imports #-----------------------------------------------------------

from cli import cli
from svo import random

STUB = "force"


def run_cached(expr, id, store, kwargs):
    store[id] = run(expr, **kwargs)


def run(expr, order=None, seed=None, time_run=60, collect_dists=False, **kwargs):
    now = datetime.now()

    if not order:
        order = random.run(expr, seed)["order"]

    clauses = expr.clauses
    span = compute_span(clauses, order)
    dist = compute_inner_dists(clauses, order)

    orders = [order]
    times = [datetime.now() - now]

    spans = [span]
    dists = [dist]

    while datetime.now() - now < timedelta(seconds=time_run):
        n_variables = expr.get_no_variables()

        # +1 as indizes start at 1
        cogs_vc = [0] * (n_variables + 1)
        cogs_vn = [0] * (n_variables + 1)

        span_old = span

        for i, clause in enumerate(clauses):
            cogs = compute_cog(clause, order)

            for x in clause:
                x = abs(x)

                cogs_vc[x] += cogs
                cogs_vn[x] += 1

        tlocs = []

        for i in range(n_variables):
            j = i + 1

            center = cogs_vc[j]
            n = cogs_vn[j]

            if n > 0:
                tlocs.append((j, center / n))

        tlocs = sorted(tlocs, key=lambda x: x[1])

        order = [x[0] for x in tlocs]

        times.append(datetime.now() - now)

        orders.append(order)

        span = compute_span(clauses, order)
        spans.append(span)

        if collect_dists:
            dist = compute_inner_dists(clauses, order)
            dists.append(dist)

        if span_old == span:
            break;

    out = {
        "order": order,
        "orders": orders,
        "spans": spans,
        "times": times
    }

    if collect_dists:
        out["dists"] = dists

    return out


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
    inner_dists = 0

    for clause in clauses:

        dist = 0

        for i, x in enumerate(clause):
            x = abs(x)

            for y in clause[i + 1:]:
                y = abs(y)
                dist += abs(order.index(x) - order.index(y))

        inner_dists += dist

    return inner_dists
