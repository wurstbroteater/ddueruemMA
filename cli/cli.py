# ------------------------------------------------------------------------------
# External imports #-----------------------------------------------------------

# ------------------------------------------------------------------------------
# Internal imports #-----------------------------------------------------------

import config
from . import format


# ------------------------------------------------------------------------------


def highlight(text, more=""):
    return format.h(text, more)


def say(*parts, origin=None):
    if config.SILENT:
        return

    if origin:
        print(format.render(f"<!>{origin}", ">", *parts))
    else:
        print(format.render(*parts))


def debug(*parts, origin=None):
    if not config.DEBUG:
        return

    if origin:
        print(format.render(f"<!>[{origin}]", f"<?b>DEBUG:", *parts, style="<?>"))
    else:
        print(format.render(f"<?b>DEBUG:", *parts, style="<?>"))


def warning(*parts, origin=None):
    if origin:
        print(format.render("<wb>Warning", "(" + format.render(f"<!>{origin}") + "):", *parts, style=""))
    else:
        print(format.render(*parts, style="<w>"))


def error(*parts, origin=None):
    print(format.render(f"<eb>ERROR:", *parts, "", style="<e>"))
