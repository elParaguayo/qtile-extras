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

from test.helpers import Retry
from test.widget.docs_screenshots.conftest import widget_config
from test.widget.test_livefootballscores import lfs_match, lfswidget, matches_loaded  # noqa


@pytest.fixture
def widget(lfswidget):  # noqa: F811
    yield partial(lfswidget.LiveFootballScores, startup_delay=0, info_timeout=0.3)


@widget_config(
    [
        dict(
            team="Chelsea",
            teams=["Liverpool", "Real Madrid"],
            leagues=["premier-league", "FIFA World Cup"],
        )
    ]
)
def ss_livefootballscores(screenshot_manager):
    matches_loaded(screenshot_manager)
    screenshot_manager.take_screenshot()

    screenshot_manager.c.bar["top"].fake_button_press(0, 0, 1)
    screenshot_manager.take_screenshot(caption="Clicking on widget cycles through: match time...")

    screenshot_manager.c.bar["top"].fake_button_press(0, 0, 1)
    screenshot_manager.take_screenshot(caption="Home goal scorers...")

    screenshot_manager.c.bar["top"].fake_button_press(0, 0, 1)
    screenshot_manager.take_screenshot(caption="Away goal scorers...")

    screenshot_manager.c.bar["top"].fake_button_press(0, 0, 1)
    screenshot_manager.take_screenshot(caption="Competition name.")

    screenshot_manager.c.bar["top"].fake_button_press(0, 0, 4)
    screenshot_manager.take_screenshot(caption="Scrolling shows different matches.")


@widget_config(
    [
        dict(
            team="Chelsea",
            teams=["Liverpool", "Real Madrid"],
            leagues=["premier-league", "FIFA World Cup"],
        )
    ]
)
def ss_livefootballscores_popup(screenshot_manager):
    @Retry(ignore_exceptions=(AssertionError,))
    def wait_for_popup():
        assert len(screenshot_manager.c.internal_windows()) == 3  # 2 bars + 1 popup

    matches_loaded(screenshot_manager)
    screenshot_manager.c.bar["top"].fake_button_press(0, 0, 3)
    wait_for_popup()
    screenshot_manager.take_popup_screenshot(caption="Showing list of all followed matches.")


@widget_config(
    [
        dict(
            team="Chelsea",
            teams=["Liverpool", "Real Madrid"],
            leagues=["premier-league", "FIFA World Cup"],
        )
    ]
)
def ss_livefootballscores_extended_popup(screenshot_manager):
    @Retry(ignore_exceptions=(AssertionError,))
    def wait_for_popup():
        assert len(screenshot_manager.c.internal_windows()) == 3  # 2 bars + 1 popup

    matches_loaded(screenshot_manager)
    screenshot_manager.c.widget["livefootballscores"].show_detail()
    wait_for_popup()
    screenshot_manager.take_extended_popup_screenshot(caption="Showing detail for single match.")
