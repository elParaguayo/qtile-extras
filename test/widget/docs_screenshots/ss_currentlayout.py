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

from qtile_extras.widget.currentlayout import CurrentLayout
from test.widget.docs_screenshots.conftest import widget_config


@pytest.fixture
def widget():
    yield CurrentLayout


@widget_config(
    [
        {},
        {"mode": "icon"},
        {"use_mask": True, "mode": "icon", "foreground": "0ff"},
        {"use_mask": True, "icon_first": True, "mode": "both", "foreground": "0ff"},
        {
            "use_mask": True,
            "icon_first": False,
            "mode": "both",
            "foreground": ["f0f", "00f", "0ff"],
        },
        {"use_mask": False, "icon_first": True, "mode": "both", "foreground": "f0f"},
    ]
)
def ss_currentlayout(screenshot_manager):
    screenshot_manager.take_screenshot()
