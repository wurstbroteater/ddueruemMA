import re

from jinja2 import Environment, PackageLoader, select_autoescape

env = Environment(
    loader=PackageLoader("ddueruem", "templates"),
    autoescape=select_autoescape()
)


def render(template_name, filename, data):
    if not template_name.endswith("j2"):
        template_name = f"{template_name}.j2"

    template = env.get_template(template_name)

    for i, x in enumerate(data):

        y = dict()

        for k, v in x.items():
            k = re.sub("-", "_", k)
            y[k] = v

        data[i] = y

    with open(filename, "w+") as file:
        file.write(template.render(data=data))
