# Copyright (c) 2015 dmpayton
# Copyright (c) 2021 elParaguayo
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import importlib
import inspect
import json
import os
import pprint
from pathlib import Path
from subprocess import CalledProcessError, run
from unittest.mock import MagicMock

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.statemachine import ViewList
from jinja2 import Template
from libqtile import command, configurable, widget
from libqtile.utils import import_class
from libqtile.widget.base import _Widget
from sphinx.util.nodes import nested_parse_with_titles

from qtile_extras.resources import wallpapers
from qtile_extras.widget import widgets

qtile_module_template = Template(
    """
.. qtile_class:: {{ module }}.{{ class_name }}
    {% if no_config %}:no-config:{% endif %}
    {% if no_commands %}:no-commands:{% endif %}
    {% if show_config %}:show-config:{% endif %}
"""
)

list_objects_template = Template(
    """
{% for obj in objects %}
  - :ref:`{{ obj }} <{{ obj.lower() }}>`
{% endfor %}
"""
)

list_wallpapers_template = Template(
    """
{% for name, path in wallpapers %}
{{ name }}

    .. image:: /{{ path }}
        :alt: {{ name }}

{% endfor %}
"""
)

qtile_class_template = Template(
    """
{{ class_name }}
{{ class_underline }}

{% if inactive %}
.. warning::

    This class has been marked as inactive.

    This means I am no longer actively developing it and so may
    not implement updates/bugfixes as regularly.

{% endif %}

{% if experimental %}
.. warning::

    This class has been marked as experimental.

    The widget may behave unexpectedly, have missing features and will
    probably crash at some point!

    Feedback on any issues would be appreciated.

{% endif %}

{% if compatibility %}
.. note::

    This class has just been modified to enable compatibility with features
    provided by qtile-extras. No new functionality has been added.

{% endif %}

.. autoclass:: {{ module }}.{{ class_name }}{% for arg in extra_arguments %}
    {{ arg }}{% endfor %}

    {% if not compatibility %}

    {% if dependencies %}
    .. admonition:: Required Dependencies

        This module requires the following third-party libraries:
        {{ dependencies }}

    {% endif %}
    {% if is_widget %}
    .. compound::

        Supported bar orientations: {{ obj.orientations }}
    {% endif %}
    {% if screenshots %}
    {% for path, caption in screenshots %}
    .. figure:: /_static/images/{{ path }}
        :target: ../../_static/images/{{ path }}

        {{ caption }}

    {% endfor %}
    {% endif %}
    {% if is_widget and widget_screenshots %}
    .. raw:: html

        <table class="docutils">
        <tr>
        <td width="50%"><b>example</b></td>
        <td width="50%"><b>config</td>
        </tr>
    {% for sshot, conf in widget_screenshots.items() %}
        <tr>
        <td><img src="{{ sshot }}" /></td>
        {% if conf %}
        <td><code class="docutils literal notranslate">{{ conf }}</code></td>
        {% else %}
        <td><i>default</i></td>
        {% endif %}
        </tr>
    {% endfor %}
        </table>

    {% endif %}
    {% if hooks %}
    Available hooks:
    {% for name in hooks %}
    - `{{ name}} <hooks.html#qtile_extras.hook.subscribe.{{ name }}>`_
    {% endfor %}

    {% endif %}
    {% if defaults %}
    .. list-table::
        :widths: 20 20 60
        :header-rows: 1

        * - key
          - default
          - description
        {% for key, default, description in defaults %}
        * - ``{{ key }}``
          - ``{{ default }}``
          - {{ description[1:-1] }}
        {% endfor %}
    {% endif %}
    {% if commandable %}
    {% for cmd in commands %}
    .. automethod:: {{ module }}.{{ class_name }}.{{ cmd }}
    {% endfor %}
    {% endif %}
    {% endif %}
"""
)

qtile_hooks_template = Template(
    """
.. automethod:: qtile_extras.hook.subscribe.{{ method }}
"""
)


def is_widget(obj):
    return issubclass(obj, _Widget)


class SimpleDirectiveMixin:
    has_content = True
    required_arguments = 1

    def make_rst(self):
        raise NotImplementedError

    def run(self):
        node = nodes.section()
        node.document = self.state.document
        result = ViewList()
        for line in self.make_rst():
            result.append(line, "<{0}>".format(self.__class__.__name__))
        nested_parse_with_titles(self.state, result, node)
        return node.children


def sphinx_escape(s):
    return pprint.pformat(s, compact=False, width=10000)


class QtileClass(SimpleDirectiveMixin, Directive):
    optional_arguments = 3
    option_spec = {
        "show-config": directives.flag,
        "no-commands": directives.flag,
        "exclude-base": directives.flag,
    }

    def make_rst(self):
        module, class_name = self.arguments[0].rsplit(".", 1)
        obj = import_class(module, class_name)
        is_configurable = "show-config" in self.options
        is_commandable = "no-commands" in self.options

        # build up a dict of defaults using reverse MRO
        defaults = {}
        for klass in reversed(obj.mro()):
            # if not issubclass(klass, configurable.Configurable):
            #     continue
            if not hasattr(klass, "defaults"):
                continue
            klass_defaults = getattr(klass, "defaults")
            defaults.update({d[0]: d[1:] for d in klass_defaults})
        # turn the dict into a list of ("value", "default", "description") tuples
        defaults = [
            (k, sphinx_escape(v[0]), sphinx_escape(v[1])) for k, v in sorted(defaults.items())
        ]
        if len(defaults) == 0:
            is_configurable = False

        deps = [f"``{d}``" for d in getattr(obj, "_dependencies", list())]
        dependencies = ", ".join(deps)

        is_widget = issubclass(obj, widget.base._Widget)

        if is_widget:
            index = Path(__file__).parent / "_static" / "screenshots" / "widgets" / "shots.json"
            try:
                with open(index, "r") as f:
                    shots = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                shots = {}

            widget_shots = shots.get(class_name.lower(), dict())
        else:
            widget_shots = {}

        widget_shots = {
            f"../../widgets/{class_name.lower()}/{k}.png": v for k, v in widget_shots.items()
        }

        context = {
            "module": module,
            "class_name": class_name,
            "class_underline": "=" * len(class_name),
            "obj": obj,
            "defaults": defaults,
            "configurable": is_configurable and issubclass(obj, configurable.Configurable),
            "commandable": is_commandable and issubclass(obj, command.base.CommandObject),
            "experimental": getattr(obj, "_experimental", False),
            "hooks": getattr(obj, "_hooks", list()),
            "inactive": getattr(obj, "_inactive", False),
            "screenshots": getattr(obj, "_screenshots", list()),
            "dependencies": dependencies,
            "compatibility": getattr(obj, "_qte_compatibility", False),
            "widget_screenshots": widget_shots,
            "is_widget": is_widget,
        }
        if context["commandable"]:
            context["commands"] = [
                # Command methods have the "_cmd" attribute so we check for this
                # However, some modules are Mocked so we need to exclude them
                attr.__name__
                for _, attr in inspect.getmembers(obj)
                if hasattr(attr, "_cmd") and not isinstance(attr, MagicMock)
            ]

        rst = qtile_class_template.render(**context)
        for line in rst.splitlines():
            yield line


class QtileModule(SimpleDirectiveMixin, Directive):
    # :baseclass: <base class path>
    # :no-commands:
    # :no-config:
    optional_arguments = 4
    option_spec = {
        "baseclass": directives.unchanged,
        "no-commands": directives.flag,
        "exclude-base": directives.flag,
        "show-config": directives.flag,
    }

    def make_rst(self):
        module = importlib.import_module(self.arguments[0])
        exclude_base = "exclude-base" in self.options

        base_class = None
        if "baseclass" in self.options:
            base_class = import_class(*self.options["baseclass"].rsplit(".", 1))

        for item in dir(module):
            obj = import_class(self.arguments[0], item)
            if (
                (not inspect.isclass(obj))
                or (base_class and not issubclass(obj, base_class))
                or (exclude_base and obj == base_class)
                or (is_widget(obj) and item not in widgets)
            ):
                continue

            context = {
                "module": self.arguments[0],
                "class_name": item,
                "no_commands": "no-commands" in self.options,
                "show_config": "show-config" in self.options,
            }

            rst = qtile_module_template.render(**context)
            for line in rst.splitlines():
                if not line.strip():
                    continue
                yield line


class ListObjects(SimpleDirectiveMixin, Directive):
    optional_arguments = 1
    option_spec = {
        "baseclass": directives.unchanged,
    }

    def make_rst(self):
        module = importlib.import_module(self.arguments[0])

        base_class = None
        if "baseclass" in self.options:
            base_class = import_class(*self.options["baseclass"].rsplit(".", 1))
        objects = []
        for item in dir(module):
            obj = import_class(self.arguments[0], item)
            if (
                (not inspect.isclass(obj))
                or (base_class and not issubclass(obj, base_class))
                or (obj == base_class)
                or (is_widget(obj) and item not in widgets)
                or getattr(obj, "_qte_compatibility", False)
            ):
                continue

            objects.append(item)

        context = {"objects": objects}

        rst = list_objects_template.render(**context)
        for line in rst.splitlines():
            if not line.strip():
                continue
            yield line


class ListWallpapers(SimpleDirectiveMixin, Directive):
    required_arguments = 0
    optional_arguments = 0

    def make_rst(self):
        wps = []
        for wpname in dir(wallpapers):
            wpaper = getattr(wallpapers, wpname)
            wps.append((wpname, wpaper))

        rst = list_wallpapers_template.render(wallpapers=wps)
        for line in rst.splitlines():
            if not line.strip():
                continue
            yield line


class QtileHooks(SimpleDirectiveMixin, Directive):
    def make_rst(self):
        module, class_name = self.arguments[0].rsplit(".", 1)
        obj = import_class(module, class_name)
        for method in sorted(obj.hooks):
            rst = qtile_hooks_template.render(method=method)
            for line in rst.splitlines():
                yield line


def generate_widget_screenshots():
    this_dir = os.path.dirname(__file__)
    try:
        run(["make", "-C", this_dir, "genwidgetscreenshots"], check=True)
    except CalledProcessError:
        raise Exception("Widget screenshots failed to build.")


def setup(app):
    # screenshots will be skipped unless QTILE_BUILD_SCREENSHOTS environment variable is set
    # Variable is set for ReadTheDocs at https://readthedocs.org/dashboard/qtile/environmentvariables/
    if os.getenv("QTILE_BUILD_SCREENSHOTS", False):
        generate_widget_screenshots()
    else:
        print("Skipping screenshot builds...")
    app.add_directive("qtile_class", QtileClass)
    app.add_directive("qtile_module", QtileModule)
    app.add_directive("list_objects", ListObjects)
    app.add_directive("qte_wallpapers", ListWallpapers)
    app.add_directive("qte_hooks", QtileHooks)
