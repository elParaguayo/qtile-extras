# Copyright (c) 2024 elParaguayo
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
import pytest

from qtile_extras.widget.groupbox2 import GroupBox2, GroupBoxRule


@pytest.fixture
def widget():
    yield GroupBox2


def rainbow(rule, box):
    index = int(box.group.name) - 1
    colours = [
        "ff0000",
        "ff7f00",
        "ffff00",
        "00ff00",
        "00ffff",
        "0000ff",
        "4b0082",
        "ff00ff",
        "ffffff",
    ]
    rule.text_colour = colours[index]
    return True


def set_label(rule, box):
    if box.focused:
        rule.text = "◉"
    elif box.occupied:
        rule.text = "◎"
    else:
        rule.text = "○"

    return True


@pytest.mark.parametrize(
    "screenshot_manager",
    [
        {},
        {"visible_groups": ["1", "2", "3", "4"]},
        {
            "padding_x": 5,
            "rules": [
                GroupBoxRule(block_colour="00ffff").when(screen=GroupBoxRule.SCREEN_THIS),
                GroupBoxRule(block_border_colour="999999").when(screen=GroupBoxRule.SCREEN_OTHER),
                GroupBoxRule(text_colour="ffffff").when(occupied=True),
                GroupBoxRule(text_colour="999999").when(occupied=False),
            ],
        },
        {
            "padding_x": 5,
            "rules": [
                GroupBoxRule(
                    line_colour="00ffff",
                    line_position=GroupBoxRule.LINE_LEFT | GroupBoxRule.LINE_RIGHT,
                ).when(screen=GroupBoxRule.SCREEN_THIS),
                GroupBoxRule(text="+").when(occupied=True),
                GroupBoxRule(text="-").when(occupied=False),
                GroupBoxRule(text_colour="ffffff"),
            ],
        },
        {
            "padding_x": 5,
            "rules": [
                GroupBoxRule().when(func=rainbow),
            ],
        },
        {
            "fontsize": 20,
            "padding_x": 5,
            "rules": [
                GroupBoxRule().when(func=set_label),
                GroupBoxRule(text_colour="ff00ff").when(screen=GroupBoxRule.SCREEN_THIS),
                GroupBoxRule(text_colour="e85e00").when(screen=GroupBoxRule.SCREEN_OTHER),
                GroupBoxRule(text_colour="999999"),
            ],
        },
    ],
    indirect=True,
)
def ss_groupbox2(screenshot_manager):
    screenshot_manager.test_window("one")
    screenshot_manager.c.window.togroup("3")
    screenshot_manager.take_screenshot()
