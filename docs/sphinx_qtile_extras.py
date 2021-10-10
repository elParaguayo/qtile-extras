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
import pprint

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.statemachine import ViewList
from jinja2 import Template
from libqtile import command, configurable, widget
from libqtile.utils import import_class
from libqtile.widget.base import _Widget
from sphinx.util.nodes import nested_parse_with_titles

from qtile_extras.widget import widgets


qtile_module_template = Template('''
.. qtile_class:: {{ module }}.{{ class_name }}
    {% if no_config %}:no-config:{% endif %}
    {% if no_commands %}:no-commands:{% endif %}
    {% if show_config %}:show-config:{% endif %}
''')

list_objects_template = Template('''
{% for obj in objects %}
  - :ref:`{{ obj }} <{{ obj.lower() }}>`
{% endfor %}
''')

qtile_class_template = Template('''
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

.. autoclass:: {{ module }}.{{ class_name }}{% for arg in extra_arguments %}
    {{ arg }}{% endfor %}

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
    {% if configurable %}
    .. raw:: html

        <table class="colwidths-auto docutils align-default">
        <tr>
        <td><b>key</b></td>
        <td><b>default</b></td>
        <td><b>description</b></td>
        </tr>
        {% for key, default, description in defaults %}
        <tr>
        <td><code class="docutils literal notranslate">{{ key }}</code></td>
        <td><code class="docutils literal notranslate">{{ default }}</code></td>
        <td>{{ description[1:-1] }}</td>
        </tr>
        {% endfor %}
        </table>
    {% endif %}
    {% if commandable %}
    {% for cmd in commands %}
    .. automethod:: {{ module }}.{{ class_name }}.{{ cmd }}
    {% endfor %}
    {% endif %}
''')

qtile_hooks_template = Template('''
.. automethod:: libqtile.hook.subscribe.{{ method }}
''')


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
            result.append(line, '<{0}>'.format(self.__class__.__name__))
        nested_parse_with_titles(self.state, result, node)
        return node.children


def sphinx_escape(s):
    return pprint.pformat(s, compact=False, width=10000)


class QtileClass(SimpleDirectiveMixin, Directive):
    optional_arguments = 3
    option_spec = {
        "show-config": directives.flag,
        "no-commands": directives.flag,
        "exclude-base": directives.flag
    }

    def make_rst(self):
        module, class_name = self.arguments[0].rsplit('.', 1)
        obj = import_class(module, class_name)
        is_configurable = 'show-config' in self.options
        is_commandable = 'no-commands' in self.options

        # build up a dict of defaults using reverse MRO
        defaults = {}
        for klass in reversed(obj.mro()):
            if not issubclass(klass, configurable.Configurable):
                continue
            if not hasattr(klass, "defaults"):
                continue
            klass_defaults = getattr(klass, "defaults")
            defaults.update({
                d[0]: d[1:] for d in klass_defaults
            })
        # turn the dict into a list of ("value", "default", "description") tuples
        defaults = [
            (k, sphinx_escape(v[0]), sphinx_escape(v[1])) for k, v in sorted(defaults.items())
        ]
        if len(defaults) == 0:
            is_configurable = False

        deps = [f"``{d}``" for d in getattr(obj, "_dependencies", list())]
        dependencies = ", ".join(deps)

        context = {
            'module': module,
            'class_name': class_name,
            'class_underline': "=" * len(class_name),
            'obj': obj,
            'defaults': defaults,
            'configurable': is_configurable and issubclass(obj, configurable.Configurable),
            'commandable': is_commandable and issubclass(obj, command.base.CommandObject),
            'is_widget': issubclass(obj, widget.base._Widget),
            'experimental': getattr(obj, "_experimental", False),
            'inactive': getattr(obj, "_inactive", False),
            'screenshots': getattr(obj, "_screenshots", list()),
            'dependencies': dependencies
        }
        if context['commandable']:
            context['commands'] = [
                attr for attr in dir(obj) if attr.startswith('cmd_')
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
        "show-config": directives.flag
    }

    def make_rst(self):
        module = importlib.import_module(self.arguments[0])
        exclude_base = 'exclude-base' in self.options

        BaseClass = None
        if 'baseclass' in self.options:
            BaseClass = import_class(*self.options["baseclass"].rsplit('.', 1))

        for item in dir(module):
            obj = import_class(self.arguments[0], item)
            if (
                (
                    not inspect.isclass(obj)
                ) or (
                    BaseClass and not issubclass(obj, BaseClass)
                ) or (
                    exclude_base and obj == BaseClass
                ) or (
                    is_widget(obj) and item not in widgets
                )
            ):
                continue

            context = {
                'module': self.arguments[0],
                'class_name': item,
                'no_commands': 'no-commands' in self.options,
                'show_config': 'show-config' in self.options,
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

        BaseClass = None
        if 'baseclass' in self.options:
            BaseClass = import_class(*self.options["baseclass"].rsplit('.', 1))
        objects = []
        for item in dir(module):
            obj = import_class(self.arguments[0], item)
            if (
                (
                    not inspect.isclass(obj)
                ) or (
                    BaseClass and not issubclass(obj, BaseClass)
                ) or (
                    obj == BaseClass
                ) or (
                    is_widget(obj) and item not in widgets
                )
            ):
                continue

            objects.append(item)

        context = {"objects": objects}

        rst = list_objects_template.render(**context)
        for line in rst.splitlines():
            if not line.strip():
                continue
            yield line        

    
def setup(app):
    app.add_directive('qtile_class', QtileClass)
    app.add_directive('qtile_module', QtileModule)
    app.add_directive('list_objects', ListObjects)
