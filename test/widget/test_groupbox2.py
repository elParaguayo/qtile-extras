# Copyright (c) 2023 elParaguayo
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
from enum import Flag
from pathlib import Path

import pytest
from libqtile.bar import Bar
from libqtile.config import Screen

from qtile_extras import widget
from qtile_extras.widget.groupbox2 import SENTINEL, GroupBoxRule, ScreenRule
from test.conftest import dualmonitor
from test.helpers import BareConfig

ICON = (
    Path(__file__).parent
    / ".."
    / ".."
    / "qtile_extras"
    / "resources"
    / "github-icons"
    / "github.svg"
)


class Dummy:
    def __init__(self, screen=ScreenRule.UNSET, focused=None, occupied=None):
        self.screen = screen
        self.focused = focused
        self.occupied = occupied


@pytest.fixture
def gbmanager(manager_nospawn, request):
    class GroupBox2(widget.GroupBox2):
        def info(self):
            info = widget.GroupBox2.info(self)
            boxes = []
            for box in self.boxes:
                b_inf = {}
                for attr in GroupBoxRule.attrs:
                    val = getattr(box, attr)
                    if val is SENTINEL:
                        b_inf[attr] = "sentinel"
                    elif isinstance(val, Flag):
                        b_inf[attr] = val.name
                    elif callable(val):
                        b_inf[attr] = val.__name__
                    else:
                        b_inf[attr] = val
                boxes.append(b_inf)

            info["boxes"] = boxes
            return info

    class GroupBoxConfig(BareConfig):
        screens = [
            Screen(top=Bar([GroupBox2(**getattr(request, "param", dict()))], 20)),
            Screen(top=Bar([GroupBox2(name="screen2", **getattr(request, "param", dict()))], 20)),
        ]

    manager_nospawn.start(GroupBoxConfig)

    manager_nospawn.test_window("one")
    manager_nospawn.c.window.togroup("c")

    yield manager_nospawn


@pytest.mark.parametrize(
    "config,args,expected",
    [
        ({}, {"screen": ScreenRule.THIS}, True),
        ({}, {"screen": ScreenRule.OTHER}, True),
        ({}, {"screen": ScreenRule.NONE}, True),
        ({}, {"focused": True}, True),
        ({}, {"focused": False}, True),
        ({}, {"occupied": True}, True),
        ({}, {"occupied": False}, True),
        ({}, {"screen": ScreenRule.THIS, "focused": True}, True),
        ({}, {"focused": True, "occupied": True}, True),
        ({}, {"screen": ScreenRule.THIS, "focused": True, "occupied": True}, True),
        # test screen rules
        ({"screen": ScreenRule.THIS}, {"screen": ScreenRule.THIS}, True),
        ({"screen": ScreenRule.THIS}, {"screen": ScreenRule.OTHER}, False),
        ({"screen": ScreenRule.THIS}, {"screen": ScreenRule.NONE}, False),
        ({"screen": ScreenRule.OTHER}, {"screen": ScreenRule.THIS}, False),
        ({"screen": ScreenRule.OTHER}, {"screen": ScreenRule.OTHER}, True),
        ({"screen": ScreenRule.OTHER}, {"screen": ScreenRule.NONE}, False),
        ({"screen": ScreenRule.NONE}, {"screen": ScreenRule.THIS}, False),
        ({"screen": ScreenRule.NONE}, {"screen": ScreenRule.OTHER}, False),
        ({"screen": ScreenRule.NONE}, {"screen": ScreenRule.NONE}, True),
        ({"screen": ScreenRule.THIS | ScreenRule.OTHER}, {"screen": ScreenRule.THIS}, True),
        ({"screen": ScreenRule.THIS | ScreenRule.OTHER}, {"screen": ScreenRule.OTHER}, True),
        ({"screen": ScreenRule.THIS | ScreenRule.OTHER}, {"screen": ScreenRule.NONE}, False),
        ({"screen": ScreenRule.NONE | ScreenRule.THIS}, {"screen": ScreenRule.THIS}, True),
        ({"screen": ScreenRule.NONE | ScreenRule.THIS}, {"screen": ScreenRule.OTHER}, False),
        ({"screen": ScreenRule.NONE | ScreenRule.THIS}, {"screen": ScreenRule.NONE}, True),
        ({"screen": ScreenRule.NONE | ScreenRule.OTHER}, {"screen": ScreenRule.THIS}, False),
        ({"screen": ScreenRule.NONE | ScreenRule.OTHER}, {"screen": ScreenRule.OTHER}, True),
        ({"screen": ScreenRule.NONE | ScreenRule.OTHER}, {"screen": ScreenRule.NONE}, True),
        # Test focused rules
        ({"focused": True}, {"focused": True}, True),
        ({"focused": True}, {"focused": False}, False),
        ({"focused": False}, {"focused": True}, False),
        ({"focused": False}, {"focused": False}, True),
        # Test occupied rules
        ({"occupied": True}, {"occupied": True}, True),
        ({"occupied": True}, {"occupied": False}, False),
        ({"occupied": False}, {"occupied": True}, False),
        ({"occupied": False}, {"occupied": False}, True),
        # Test function
        ({"func": lambda rule, box: True}, {"occupied": False}, True),
        ({"func": lambda rule, box: False}, {"occupied": False}, False),
        # Test combos
        (
            {"screen": ScreenRule.THIS, "focused": True, "occupied": True},
            {"screen": ScreenRule.THIS, "focused": True, "occupied": True},
            True,
        ),
        (
            {"screen": ScreenRule.THIS, "focused": True, "occupied": True},
            {"screen": ScreenRule.OTHER, "focused": True, "occupied": True},
            False,
        ),
        (
            {"screen": ScreenRule.THIS, "focused": True, "occupied": True},
            {"screen": ScreenRule.THIS, "focused": False, "occupied": True},
            False,
        ),
        (
            {"screen": ScreenRule.THIS, "focused": True, "occupied": True},
            {"screen": ScreenRule.THIS, "focused": True, "occupied": False},
            False,
        ),
        (
            {"screen": ScreenRule.THIS | ScreenRule.OTHER, "occupied": True},
            {"screen": ScreenRule.THIS, "focused": True, "occupied": True},
            True,
        ),
        (
            {"screen": ScreenRule.THIS | ScreenRule.OTHER, "occupied": True},
            {"screen": ScreenRule.OTHER, "focused": True, "occupied": True},
            True,
        ),
        (
            {"screen": ScreenRule.THIS | ScreenRule.OTHER, "occupied": True},
            {"screen": ScreenRule.THIS, "focused": False, "occupied": True},
            True,
        ),
        (
            {"screen": ScreenRule.THIS | ScreenRule.OTHER, "occupied": True},
            {"screen": ScreenRule.THIS, "focused": True, "occupied": False},
            False,
        ),
    ],
)
def test_groupboxrules(config, args, expected):
    rule = GroupBoxRule().when(**config)
    box = Dummy(**args)
    assert rule.match(box) == expected


@pytest.mark.parametrize(
    "format,when,expected",
    [
        ({}, {}, "<GroupBoxRule format() when()>"),
        ({"text": None}, {}, "<GroupBoxRule format(text=None) when()>"),
        (
            {"text": "text", "block_colour": "ff00ff"},
            {"occupied": True},
            "<GroupBoxRule format(block_colour=ff00ff, text=text) when(occupied=True)>",
        ),
        (
            {"line_position": GroupBoxRule.LINE_TOP},
            {"screen": GroupBoxRule.SCREEN_THIS},
            "<GroupBoxRule format(line_position=LinePosition.TOP) when(screen=ScreenRule.THIS)>",
        ),
    ],
)
def test_repr(format, when, expected):
    assert repr(GroupBoxRule(**format).when(**when)) == expected


def test_default(gbmanager):
    info = gbmanager.c.widget["groupbox2"].info()
    assert info["text"] == "a|b|c|d"

    # Default colours: grey for unoccupied
    assert info["boxes"][0]["text_colour"] == "999999"

    # white for occupied group
    assert info["boxes"][2]["text_colour"] == "ffffff"


def set_text(rule, box):
    # Set text to the index of current group
    rule.text = str(box.index)
    return True


@pytest.mark.parametrize(
    "gbmanager", [{"rules": [GroupBoxRule().when(func=set_text)]}], indirect=True
)
def test_function(gbmanager):
    info = gbmanager.c.widget["groupbox2"].info()
    assert info["text"] == "0|1|2|3"


@dualmonitor
@pytest.mark.parametrize(
    "gbmanager",
    [
        {
            "rules": [
                GroupBoxRule(text_colour="00ffff").when(screen=GroupBoxRule.SCREEN_THIS),
                GroupBoxRule(text_colour="990099").when(screen=GroupBoxRule.SCREEN_OTHER),
                GroupBoxRule(text_colour="666666").when(screen=GroupBoxRule.SCREEN_NONE),
            ]
        }
    ],
    indirect=True,
)
def test_screen_focus(gbmanager):
    info = gbmanager.c.widget["groupbox2"].info()
    scr2_info = gbmanager.c.widget["screen2"].info()

    # This screen
    assert info["boxes"][0]["text_colour"] == "00ffff"

    # Other screen
    assert info["boxes"][1]["text_colour"] == "990099"

    # No screen
    assert info["boxes"][2]["text_colour"] == "666666"

    # Screen 2 should have the first two formats the other way around
    # Other screen
    assert scr2_info["boxes"][0]["text_colour"] == "990099"

    # This screen
    assert scr2_info["boxes"][1]["text_colour"] == "00ffff"

    # No screen
    assert scr2_info["boxes"][2]["text_colour"] == "666666"


# Slightly hacky test for line positions:
# Python 3.9 doesn't combine flag names so we can't check for `LEFT|RIGHT`
@pytest.mark.parametrize(
    "gbmanager",
    [
        {
            "rules": [
                GroupBoxRule(
                    line_colour="00ffff", line_width=5, line_position=GroupBoxRule.LINE_TOP
                ).when(focused=True),
                GroupBoxRule(line_colour="990099", line_position=GroupBoxRule.LINE_LEFT).when(
                    occupied=True
                ),
                GroupBoxRule(line_colour="990099"),
                GroupBoxRule(line_colour="990099", line_position=GroupBoxRule.LINE_RIGHT).when(
                    func=lambda r, b: b.group.name == "d"
                ),
            ]
        }
    ],
    indirect=True,
)
def test_line_widths(gbmanager):
    info = gbmanager.c.widget["groupbox2"].info()

    assert info["boxes"][0]["line_colour"] == "00ffff"
    assert info["boxes"][0]["line_width"] == 5
    assert info["boxes"][0]["line_position"] == "TOP"

    # Default line_width and position when only colour set
    assert info["boxes"][1]["line_colour"] == "990099"
    assert info["boxes"][1]["line_width"] == 2
    assert info["boxes"][1]["line_position"] == "BOTTOM"

    assert info["boxes"][2]["line_position"] == "LEFT"
    assert info["boxes"][3]["line_position"] == "RIGHT"


@pytest.mark.parametrize(
    "gbmanager",
    [
        {
            "rules": [
                GroupBoxRule(block_colour="00ffff").when(focused=True),
                GroupBoxRule(block_border_colour="999999", block_corner_radius=5).when(
                    focused=False
                ),
            ]
        }
    ],
    indirect=True,
)
def test_block(gbmanager):
    info = gbmanager.c.widget["groupbox2"].info()

    assert info["boxes"][0]["block_colour"] == "00ffff"

    # Default block border width when only colour set
    assert info["boxes"][1]["block_border_colour"] == "999999"
    assert info["boxes"][1]["block_border_width"] == 2
    assert info["boxes"][1]["block_corner_radius"] == 5


def cdraw(box):
    box.text = "custom"


@pytest.mark.parametrize(
    "gbmanager", [{"rules": [GroupBoxRule(custom_draw=cdraw).when(focused=True)]}], indirect=True
)
def test_custom_draw(gbmanager):
    info = gbmanager.c.widget["groupbox2"].info()

    assert info["boxes"][0]["custom_draw"] == "cdraw"

    # Text set by the custom draw function
    assert info["boxes"][0]["text"] == "custom"
    assert info["text"] == "custom|b|c|d"


@pytest.mark.parametrize(
    "gbmanager",
    [
        {
            "rules": [
                GroupBoxRule(text="focused").when(focused=True),
                GroupBoxRule(text="unfocused").when(focused=False),
            ]
        }
    ],
    indirect=True,
)
def test_set_text(gbmanager):
    info = gbmanager.c.widget["groupbox2"].info()
    assert info["text"] == "focused|unfocused|unfocused|unfocused"

    gbmanager.c.group["c"].toscreen()

    info = gbmanager.c.widget["groupbox2"].info()
    assert info["text"] == "unfocused|unfocused|focused|unfocused"


@pytest.mark.parametrize(
    "gbmanager",
    [{"rules": [GroupBoxRule(image=ICON.as_posix()).when(focused=True)]}],
    indirect=True,
)
def test_image(gbmanager):
    info = gbmanager.c.widget["groupbox2"].info()
    assert "github.svg" in info["boxes"][0]["image"]
    assert info["boxes"][1]["image"] == "sentinel"


@pytest.mark.parametrize(
    "gbmanager", [{"rules": [GroupBoxRule(text="D").when(group_name="d")]}], indirect=True
)
def test_group_name(gbmanager):
    info = gbmanager.c.widget["groupbox2"].info()
    assert info["text"] == "a|b|c|D"


def test_buttons(gbmanager):
    def current_group():
        _, txt = gbmanager.c.eval("self.current_group.name")
        return txt

    assert current_group() == "a"

    gbmanager.c.group["d"].toscreen()
    assert current_group() == "d"

    # Click to change group
    bar = gbmanager.c.bar["top"]
    bar.fake_button_press(0, "top", 0, 0, 1)
    assert current_group() == "a"

    # Scroll up
    for g in ["d", "c", "b", "a"]:
        bar.fake_button_press(0, "top", 0, 0, 4)
        assert current_group() == g

    # Scroll down
    for g in ["b", "c", "d", "a"]:
        bar.fake_button_press(0, "top", 0, 0, 5)
        assert current_group() == g


@pytest.mark.parametrize("gbmanager", [{"visible_groups": ["a", "b"]}], indirect=True)
def test_visible_groups(gbmanager):
    info = gbmanager.c.widget["groupbox2"].info()
    assert info["text"] == "a|b"


@pytest.mark.parametrize(
    "gbmanager",
    [{"rules": [GroupBoxRule(box_size=100).when(focused=True), GroupBoxRule(box_size=50)]}],
    indirect=True,
)
def test_box_size(gbmanager):
    info = gbmanager.c.widget["groupbox2"].info()
    assert info["width"] == 250
