# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2012-2013 Craig Barnes
# Copyright (c) 2012 roger
# Copyright (c) 2012, 2014-2015 Tycho Andersen
# Copyright (c) 2014 Sean Vig
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
import libqtile.config
import libqtile.confreader
import libqtile.layout

from qtile_extras import widget
from qtile_extras.bar import Bar


class GeomConf(libqtile.confreader.Config):
    auto_fullscreen = False
    keys = []
    mouse = []
    groups = [
        libqtile.config.Group("a"),
        libqtile.config.Group("b"),
        libqtile.config.Group("c"),
        libqtile.config.Group("d")
    ]
    layouts = [libqtile.layout.stack.Stack(num_stacks=1)]
    floating_layout = libqtile.resources.default_config.floating_layout
    screens = [
        libqtile.config.Screen(
            top=Bar([], 10),
            bottom=Bar([], 10),
            left=Bar([], 10),
            right=Bar([], 10),
        )
    ]


def test_bar_border_horizontal(manager_nospawn):
    config = GeomConf

    config.screens = [
        libqtile.config.Screen(
            top=Bar(
                [widget.Spacer()],
                12,
                margin=5,
                border_width=5,
            ),
            bottom=Bar(
                [widget.Spacer()],
                12,
                margin=5,
                border_width=0,
            ),
        )
    ]

    manager_nospawn.start(config)

    top_info = manager_nospawn.c.bar["top"].info
    bottom_info = manager_nospawn.c.bar["bottom"].info

    # Screen is 800px wide so:
    # -top bar should have width of 800 - 5 - 5 - 5 - 5 = 780 (margin and border)
    # -bottom bar should have width of 800 - 5 - 5 = 790 (margin and no border)

    assert top_info()["width"] == 780
    assert bottom_info()["width"] == 790

    # Bar "height" should still be the value set in the config but "size" is
    # adjusted for margin and border:
    # -top bar should have size of 12 + 5 + 5 + 5 + 5 = 32 (margin and border)
    # -bottom bar should have size of 12 + 5 + 5 = 22 (margin and border)

    assert top_info()["height"] == 12
    assert top_info()["size"] == 32
    assert bottom_info()["height"] == 12
    assert bottom_info()["size"] == 22

    # Test widget offsets
    # Where there is a border, widget should be offset by that amount

    _, xoffset = manager_nospawn.c.bar["top"].eval("self.widgets[0].offsetx")
    assert xoffset == "5"

    _, yoffset = manager_nospawn.c.bar["top"].eval("self.widgets[0].offsety")
    assert xoffset == "5"

    # Where there is no border, this should be 0
    _, xoffset = manager_nospawn.c.bar["bottom"].eval("self.widgets[0].offsetx")
    assert xoffset == "0"

    _, yoffset = manager_nospawn.c.bar["bottom"].eval("self.widgets[0].offsety")
    assert xoffset == "0"


def test_bar_border_vertical(manager_nospawn):
    config = GeomConf

    config.screens = [
        libqtile.config.Screen(
            left=Bar(
                [widget.Spacer()],
                12,
                margin=5,
                border_width=5,
            ),
            right=Bar(
                [widget.Spacer()],
                12,
                margin=5,
                border_width=0,
            ),
        )
    ]

    manager_nospawn.start(config)

    left_info = manager_nospawn.c.bar["left"].info
    right_info = manager_nospawn.c.bar["right"].info

    # Screen is 600px tall so:
    # -left bar should have height of 600 - 5 - 5 - 5 - 5 = 580 (margin and border)
    # -right bar should have height of 600 - 5 - 5 = 590 (margin and no border)

    assert left_info()["height"] == 580
    assert right_info()["height"] == 590

    # Bar "width" should still be the value set in the config but "size" is
    # adjusted for margin and border:
    # -left bar should have size of 12 + 5 + 5 + 5 + 5 = 32 (margin and border)
    # -right bar should have size of 12 + 5 + 5 = 22 (margin and border)

    assert left_info()["width"] == 12
    assert left_info()["size"] == 32
    assert right_info()["width"] == 12
    assert right_info()["size"] == 22

    # Test widget offsets
    # Where there is a border, widget should be offset by that amount

    _, xoffset = manager_nospawn.c.bar["left"].eval("self.widgets[0].offsetx")
    assert xoffset == "5"

    _, yoffset = manager_nospawn.c.bar["left"].eval("self.widgets[0].offsety")
    assert xoffset == "5"

    # Where there is no border, this should be 0
    _, xoffset = manager_nospawn.c.bar["right"].eval("self.widgets[0].offsetx")
    assert xoffset == "0"

    _, yoffset = manager_nospawn.c.bar["right"].eval("self.widgets[0].offsety")
    assert xoffset == "0"