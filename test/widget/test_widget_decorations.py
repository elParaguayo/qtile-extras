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
from libqtile.log_utils import init_log

from qtile_extras import widget
from qtile_extras.widget.decorations import BorderDecoration, RectDecoration, _Decoration


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
                        decorations=[RectDecoration(colour="00ff00")],
                    ),
                    widget.ScriptExit(
                        name="two",
                        background="ff0000",
                        decorations=[RectDecoration(colour="00ff00", use_widget_background=True)],
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
