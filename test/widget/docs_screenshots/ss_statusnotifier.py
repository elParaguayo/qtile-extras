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

from qtile_extras.widget.statusnotifier import StatusNotifier
from test.helpers import Retry
from test.widget.docs_screenshots.conftest import statusnotifier


@pytest.fixture
def widget():
    yield StatusNotifier


@statusnotifier
def ss_statusnotifier(screenshot_manager):
    @Retry(ignore_exceptions=(AssertionError,))
    def wait_for_menu():
        assert len(screenshot_manager.c.internal_windows()) == 4

    screenshot_manager.c.bar["top"].eval("self.draw()")
    screenshot_manager.take_screenshot(
        caption="For some reason the docs won't display the icon..."
    )
    screenshot_manager.c.bar["top"].fake_button_press(10, 10, 3)
    wait_for_menu()
    screenshot_manager.take_popup_screenshot(caption="...but the menu works.")
