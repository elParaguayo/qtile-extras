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
import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import pytest
from libqtile import widget

from qtile_extras.widget.mixins import TooltipMixin
from test.helpers import Retry

BAR_SIZE = 50


class TooltipWidget(widget.TextBox, TooltipMixin):
    def __init__(self, text, **config):
        widget.TextBox.__init__(self, text, **config)
        TooltipMixin.__init__(self)
        self.add_defaults(TooltipMixin.defaults)


# Tooltips may be difference sizes on different setups.
class TooltipAdjust:
    def __init__(self, base, dimension, add=False):
        self.base = base
        self.dimension = dimension
        self.add = add

    def __call__(self, widget):
        _, val = widget.eval(f"self._tooltip.{self.dimension}")
        val = int(val)
        if not self.add:
            val *= -1

        return str(self.base + val)


@Retry(ignore_exceptions=(AssertionError,))
def assert_window_count(manager, number):
    assert len(manager.c.internal_windows()) == number


@pytest.fixture
def bar_position(request):
    yield getattr(request, "param", "top")


@pytest.fixture(scope="function")
def tooltip_manager(request, bar_position, manager_nospawn):
    widget = TooltipWidget(
        "Testint", **{**{"tooltip_delay": 0.5}, **getattr(request, "param", dict())}
    )

    class TooltipConfig(libqtile.confreader.Config):
        auto_fullscreen = True
        keys = []
        mouse = []
        groups = [
            libqtile.config.Group("a"),
        ]
        layouts = [libqtile.layout.Max()]
        floating_layout = libqtile.resources.default_config.floating_layout
        screens = [
            libqtile.config.Screen(
                **{
                    bar_position: libqtile.bar.Bar(
                        [widget],
                        BAR_SIZE,
                    )
                }
            )
        ]

    manager_nospawn.start(TooltipConfig)
    yield manager_nospawn


def test_tooltip_display(tooltip_manager, backend_name):
    widget = tooltip_manager.c.widget["tooltipwidget"]

    number = len(tooltip_manager.c.internal_windows())

    # No tooltip_text so this won't start timer
    widget.eval("self.mouse_enter(0, 0)")
    _, timer = widget.eval("self._tooltip_timer")
    assert timer == "None"

    widget.eval("self.tooltip_text='running test'")
    widget.eval("self.mouse_enter(0, 0)")
    assert_window_count(tooltip_manager, number + 1)

    if backend_name == "x11":
        pytest.xfail("Last test fails on X11.")

    widget.eval("self.mouse_leave(100, 100)")
    assert_window_count(tooltip_manager, number)


@pytest.mark.parametrize(
    "bar_position,pos,expected",
    [
        ("top", (0, 0), (0, BAR_SIZE)),
        ("bottom", (0, 600), (0, TooltipAdjust(600 - BAR_SIZE, "height"))),
        ("left", (0, 0), (BAR_SIZE, 0)),
        ("right", (800, 0), (TooltipAdjust(800 - BAR_SIZE, "width"), 0)),
    ],
    indirect=["bar_position"],
)
def test_tooltip_position(tooltip_manager, pos, expected):
    x, y = pos
    ex, ey = [str(n) for n in expected]
    widget = tooltip_manager.c.widget["tooltipwidget"]
    number = len(tooltip_manager.c.internal_windows())

    widget.eval("self.tooltip_text='running test'")
    widget.eval(f"self.mouse_enter({x}, {y})")
    assert_window_count(tooltip_manager, number + 1)

    _, pos_x = widget.eval("self._tooltip.x")
    _, pos_y = widget.eval("self._tooltip.y")

    assert pos_x == ex(widget) if isinstance(ex, TooltipAdjust) else ex
    assert pos_y == ey(widget) if isinstance(ex, TooltipAdjust) else ey


@pytest.mark.parametrize(
    "tooltip_manager,expected",
    [
        ({}, [4, 4]),
        ({"tooltip_padding": 2}, [2, 2]),
        ({"tooltip_padding": [5, 1]}, [5, 1]),
        ({"tooltup_padding": [1, 2, 3, 4]}, [4, 4]),
        ({"tooltip_padding": "2"}, [4, 4]),
    ],
    indirect=["tooltip_manager"],
)
def test_tooltip_padding(tooltip_manager, expected):
    widget = tooltip_manager.c.widget["tooltipwidget"]
    number = len(tooltip_manager.c.internal_windows())

    widget.eval("self.tooltip_text='running test'")
    widget.eval("self.mouse_enter(0, 0)")
    assert_window_count(tooltip_manager, number + 1)

    _, padding = widget.eval("self._tooltip_padding")

    assert padding == str(expected)


@pytest.mark.parametrize("tooltip_manager", [{"tooltip_delay": 100}], indirect=True)
def test_tooltip_cancel_timer(tooltip_manager):
    widget = tooltip_manager.c.widget["tooltipwidget"]
    widget.eval("self.tooltip_text='running test'")
    number = len(tooltip_manager.c.internal_windows())

    def get_timer():
        _, timer = widget.eval("self._tooltip_timer")
        return timer

    assert get_timer() == "None"

    widget.eval("self.mouse_enter(0, 0)")
    assert_window_count(tooltip_manager, number)

    assert get_timer() != "None"

    widget.eval("self.mouse_leave(0, 0)")
    assert_window_count(tooltip_manager, number)

    assert get_timer() == "None"
