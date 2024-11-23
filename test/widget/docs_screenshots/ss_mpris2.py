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
from functools import partial

import pytest

from qtile_extras.widget.mpris2widget import Mpris2
from test.helpers import Retry
from test.widget.test_mpris2 import MPRIS_SERVICE, dbus_thread, wait_for_player  # noqa: F401


@pytest.fixture
def widget():
    yield partial(Mpris2, objname=MPRIS_SERVICE)


def ss_mpris2(dbus_thread, screenshot_manager):  # noqa: F811
    @Retry(ignore_exceptions=(AssertionError,))
    def wait_for_popup():
        assert len(screenshot_manager.c.internal_windows()) == 3

    w = screenshot_manager.c.widget["mpris2"]
    w.play_pause()
    wait_for_player(w)
    screenshot_manager.take_screenshot()

    w.toggle_player()
    wait_for_popup()

    screenshot_manager.take_extended_popup_screenshot(
        caption="Popup layouts are fully customisable"
    )
