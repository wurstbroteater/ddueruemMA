from cli import cli


def filter(ls, attrs):
    attrs.append("STUB")
    out = {}

    for x in ls:
        valid = True

        for attr in attrs:
            if not hasattr(x, attr):
                valid = False
                break

        if valid:
            out[x.STUB] = x

    return out
