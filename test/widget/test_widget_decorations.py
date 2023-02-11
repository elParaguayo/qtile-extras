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
import logging

import libqtile.bar
import libqtile.config
import pytest
from libqtile.log_utils import init_log

from qtile_extras import widget
from qtile_extras.widget.decorations import (
    BorderDecoration,
    PowerLineDecoration,
    RectDecoration,
    _Decoration,
)


def test_single_or_four():
    for value, expected in [
        (1, [1, 1, 1, 1]),
        ((1,), [1, 1, 1, 1]),
        ((1, 2, 3, 4), [1, 2, 3, 4]),
        ((1, 2, 3), [0, 0, 0, 0]),
        ("Invalid", [0, 0, 0, 0]),
    ]:
        assert _Decoration().single_or_four(value, "test") == expected


def test_single_or_four_logging(caplog):
    init_log(logging.INFO)

    log_message = "TEST should be a single number or a list of 1 or 4 values"

    for value in [(1, 2, 3), "Invalid"]:
        _ = _Decoration().single_or_four(value, "TEST")

        assert caplog.record_tuples == [("libqtile", logging.INFO, log_message)]

        caplog.clear()


def test_decorations(manager_nospawn, minimal_conf_noscreen):
    config = minimal_conf_noscreen
    decorated_widget = widget.ScriptExit(
        decorations=[RectDecoration(), BorderDecoration(), RectDecoration(radius=0, filled=True)]
    )
    config.screens = [libqtile.config.Screen(top=libqtile.bar.Bar([decorated_widget], 10))]

    manager_nospawn.start(config)

    _, decs = manager_nospawn.c.widget["scriptexit"].eval("len(self.decorations)")
    assert int(decs) == 3


def test_rect_decoration_using_widget_background(manager_nospawn, minimal_conf_noscreen):
    config = minimal_conf_noscreen
    config.screens = [
        libqtile.config.Screen(
            top=libqtile.bar.Bar(
                [
                    widget.ScriptExit(
                        name="one",
                        background="ff0000",
                        decorations=[RectDecoration(colour="00ff00", filled=True)],
                    ),
                    widget.ScriptExit(
                        name="two",
                        background="ff0000",
                        decorations=[
                            RectDecoration(
                                colour="00ff00", use_widget_background=True, filled=True
                            )
                        ],
                    ),
                ],
                10,
            )
        )
    ]

    manager_nospawn.start(config)

    manager_nospawn.c.bar["top"].eval("self.draw()")

    _, one = manager_nospawn.c.widget["one"].eval("self.decorations[0].fill_colour")
    _, two = manager_nospawn.c.widget["two"].eval("self.decorations[0].fill_colour")

    # First widget's decoration is drawn using the decoration's colour
    assert one == "00ff00"

    # Second widget's decoration inherits the colour from the widget
    assert two == "ff0000"


def test_powerline_decoration(manager_nospawn, minimal_conf_noscreen):
    config = minimal_conf_noscreen
    config.screens = [
        libqtile.config.Screen(
            top=libqtile.bar.Bar(
                [
                    widget.Spacer(
                        length=50,
                        name="one",
                        background="ff0000",
                        decorations=[PowerLineDecoration(size=10, path="arrow_left")],
                    ),
                    widget.Spacer(
                        length=50,
                        name="two",
                        background="0000ff",
                        decorations=[PowerLineDecoration(size=10, shift=5, path="arrow_right")],
                    ),
                    widget.Spacer(
                        length=50,
                        name="three",
                        background="00ffff",
                        decorations=[PowerLineDecoration(size=10, path="rounded_left")],
                    ),
                    widget.Spacer(
                        length=50,
                        name="four",
                        background="ff00ff",
                        decorations=[PowerLineDecoration(size=10, shift=5, path="rounded_right")],
                    ),
                    widget.Spacer(
                        length=50,
                        name="five",
                        background="ffffff",
                        decorations=[PowerLineDecoration(size=10, path="zig_zag")],
                    ),
                ],
                10,
            )
        )
    ]

    manager_nospawn.start(config)
    manager_nospawn.c.bar["top"].eval("self.draw()")

    # First widget should have a length of 50 (widget) + 10 (decoration) = 60
    assert manager_nospawn.c.widget["one"].info()["length"] == 60

    # Second widget should have a length of 50 (widget) + 5 (decoration - shift) = 55
    assert manager_nospawn.c.widget["two"].info()["length"] == 55

    _, fg = manager_nospawn.c.widget["one"].eval("self.decorations[0].fg")
    _, bg = manager_nospawn.c.widget["one"].eval("self.decorations[0].bg")

    # Widget one has a 'forwards' decoration so the background is the current widget and background is the next
    assert fg == "ff0000"  # widget one's background
    assert bg == "0000ff"  # widget two's background

    _, fg = manager_nospawn.c.widget["four"].eval("self.decorations[0].fg")
    _, bg = manager_nospawn.c.widget["four"].eval("self.decorations[0].bg")

    # Widget four has a 'backwards' decoration so the background is the next widget and background is the current
    assert fg == "ffffff"  # widget five's background
    assert bg == "ff00ff"  # widget four's background


def test_decoration_extrawidth(manager_nospawn, minimal_conf_noscreen):
    config = minimal_conf_noscreen
    config.screens = [
        libqtile.config.Screen(
            top=libqtile.bar.Bar(
                [
                    widget.Spacer(
                        length=50,
                        name="one",
                        decorations=[PowerLineDecoration(size=10, extrawidth=10)],
                    ),
                    widget.Spacer(
                        length=50,
                        name="two",
                        decorations=[RectDecoration(extrawidth=20)],
                    ),
                    widget.Spacer(
                        length=50,
                        name="three",
                        background="00ffff",
                        decorations=[BorderDecoration(extrawidth=30)],
                    ),
                ],
                10,
            )
        )
    ]

    manager_nospawn.start(config)
    manager_nospawn.c.bar["top"].eval("self.draw()")

    assert manager_nospawn.c.widget["one"].info()["length"] == 70
    assert manager_nospawn.c.widget["two"].info()["length"] == 70
    assert manager_nospawn.c.widget["three"].info()["length"] == 80


@pytest.mark.parametrize(
    "dec_class,dec_config",
    [
        (BorderDecoration, {"border_width": 4, "colour": "ff0000"}),
        (RectDecoration, {"radius": 5, "colour": "ff0000"}),
    ],
)
def test_decoration_grouping(manager_nospawn, minimal_conf_noscreen, dec_class, dec_config):
    def assert_first_last(widget, first, last):
        _, ft = widget.eval("self.decorations[0].is_first")
        _, lt = widget.eval("self.decorations[0].is_last")
        _, gp = widget.eval("self.decorations[0]._get_parent_group()")
        assert ft == str(first)
        assert lt == str(last)

    config = minimal_conf_noscreen

    group_decoration = {"decorations": [dec_class(**dec_config, group=True)]}

    group2_decoration = {"decorations": [dec_class(**dec_config, group=True, groupid=2)]}

    no_group_decoration = {"decorations": [dec_class(**dec_config, group=False)]}

    config.screens = [
        libqtile.config.Screen(
            top=libqtile.bar.Bar(
                [
                    widget.TextBox("Text 1", name="tb1", **group_decoration),
                    widget.TextBox("Text 2", name="tb2", **group_decoration),
                    widget.TextBox("Text 3", name="tb3", **group_decoration),
                    widget.TextBox("Text 4", name="tb4", **group2_decoration),
                    widget.TextBox("Text 5", name="tb5", **group2_decoration),
                    widget.TextBox("Text 6", name="tb6", **no_group_decoration),
                ],
                10,
            )
        )
    ]

    manager_nospawn.start(config)
    manager_nospawn.c.bar["top"].eval("self.draw()")

    widget1 = manager_nospawn.c.widget["tb1"]
    widget2 = manager_nospawn.c.widget["tb2"]
    widget3 = manager_nospawn.c.widget["tb3"]
    widget4 = manager_nospawn.c.widget["tb4"]
    widget5 = manager_nospawn.c.widget["tb5"]
    widget6 = manager_nospawn.c.widget["tb6"]

    # First group is 3 widgets
    assert_first_last(widget1, True, False)
    assert_first_last(widget2, False, False)
    assert_first_last(widget3, False, True)

    # Next group has 2 widgets
    assert_first_last(widget4, True, False)
    assert_first_last(widget5, False, True)

    # Last widget is not grouped
    assert_first_last(widget6, True, True)
