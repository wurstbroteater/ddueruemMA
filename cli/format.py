# ------------------------------------------------------------------------------
# External imports #-----------------------------------------------------------

import i18n
import re
from termcolor import colored

# ------------------------------------------------------------------------------
# Internal imports #-----------------------------------------------------------


# ------------------------------------------------------------------------------
# Initialization #-------------------------------------------------------------

i18n.load_path.append("lang")
i18n.set('filename_format', '{locale}.{format}')

# ------------------------------------------------------------------------------
# RegEx Patterns #-------------------------------------------------------------

P_RENDER = re.compile(r"\<(?P<args>[?!bwet]+)\>(?P<text>.*)$")


# ------------------------------------------------------------------------------


def render(*parts, sep=" ", always_translate=False, style=None):
    parts = list(parts)

    for i, part in enumerate(parts):

        if i < len(parts) - 1:
            parts[i] = f"{str(part)}{sep}"
        else:
            parts[i] = f"{str(part)}"

    for i, part in enumerate(parts):

        if m := P_RENDER.match(part):
            args = m["args"]
            part = m["text"]
        else:
            if style:
                args = style
            else:
                continue

        if style:
            args = style + args

        color = None
        bgcolor = None
        attrs = []

        if "t" in args:
            part = i18n.t(part)

        if "?" in args:
            color = "white"
            bgcolor = "on_grey"

        if "w" in args:
            color = "red"

        if "e" in args:
            color = "grey"
            bgcolor = "on_red"
            attrs.append("bold")

        if "!" in args:
            color = "blue"

            if "e" in args:
                color = "white"

        if "b" in args:
            attrs.append("bold")

        parts[i] = colored(part, color, bgcolor, attrs)

    return "".join(parts)


def t(parts, sep=" "):
    return render(parts, sep, always_translate=True)


def h(text, more=""):
    return f"<!{more}>{text}"
