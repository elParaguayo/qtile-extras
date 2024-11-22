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
from datetime import datetime
from functools import partial

import pytest

import qtile_extras.widget.tvheadend
from test.helpers import Retry
from test.widget.test_tvhwidget import fake_post


@pytest.fixture
def widget(monkeypatch, request):
    class MockDatetime(datetime):
        """Mock object returning date/time set by parameterize."""

        @classmethod
        def now(cls, *args, **kwargs):
            return cls(*request.param)

    # Patch some objects
    monkeypatch.setattr("qtile_extras.widget.tvheadend.requests.post", fake_post)
    monkeypatch.setattr("qtile_extras.widget.tvheadend.datetime", MockDatetime)

    yield partial(qtile_extras.widget.tvheadend.TVHWidget, startup_delay=0)


def set_time(time):
    return pytest.mark.parametrize("widget", [time], indirect=True)


@set_time((2021, 11, 26, 18, 45))
def ss_tvh_not_recording(screenshot_manager):
    screenshot_manager.take_screenshot(caption="Not recording.")


@set_time((2021, 11, 26, 19, 5))
def ss_tvh_recording(screenshot_manager):
    screenshot_manager.take_screenshot(caption="Recording.")


@set_time((2021, 11, 26, 18, 45))
def ss_tvh_popup(screenshot_manager):
    @Retry(ignore_exceptions=(AssertionError,))
    def wait_for_popup():
        assert len(screenshot_manager.c.internal_windows()) == 3

    screenshot_manager.c.bar["top"].fake_button_press(0, 0, 1)
    wait_for_popup()
    screenshot_manager.take_popup_screenshot(caption="Popup shows upcoming recordings")
