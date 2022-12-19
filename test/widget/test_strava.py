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
from datetime import datetime

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import pytest
from pint import Unit
from stravalib.model import Activity

from qtile_extras.widget.strava import StravaWidget
from test.helpers import Retry

ACTIVITIES = [
    Activity(
        name="Test Activity 1",
        start_date_local=datetime(2021, 11, 20, 9, 0),
        distance=Unit("m") * 10000,
        elapsed_time=45 * 60,
        moving_time=45 * 60,
        type=Activity.RUN,
    ),
    Activity(
        name="Test Activity 2",
        start_date_local=datetime(2021, 11, 21, 7, 10),
        distance=Unit("m") * 21100,
        elapsed_time=105 * 60,
        moving_time=105 * 60,
        type=Activity.RUN,
    ),
]


class MockDatetime(datetime):
    @classmethod
    def now(cls, *args, **kwargs):
        return cls(2021, 11, 25, 0, 0)


def fake_client():
    class Client:
        def get_activities(self):
            return ACTIVITIES

    return Client()


@pytest.fixture(scope="function")
def stravawidget(monkeypatch):
    monkeypatch.setattr("qtile_extras.resources.stravadata.sync.get_client", fake_client)
    monkeypatch.setattr("qtile_extras.resources.stravadata.sync.APP_ID", True)
    monkeypatch.setattr("qtile_extras.resources.stravadata.sync.SECRET", True)
    monkeypatch.setattr(
        "qtile_extras.resources.stravadata.sync.check_last_update", lambda _: True
    )
    monkeypatch.setattr("qtile_extras.resources.stravadata.sync.datetime.datetime", MockDatetime)
    monkeypatch.setattr("qtile_extras.resources.stravadata.sync.cache_data", lambda _: None)
    yield StravaWidget


@pytest.fixture(scope="function")
def strava(stravawidget):
    class StravaConfig(libqtile.confreader.Config):
        auto_fullscreen = True
        keys = []
        mouse = []
        groups = [
            libqtile.config.Group("a"),
        ]
        layouts = [libqtile.layout.Max()]
        floating_layout = libqtile.resources.default_config.floating_layout
        screens = [
            libqtile.config.Screen(
                top=libqtile.bar.Bar(
                    [stravawidget(startup_delay=0)],
                    50,
                ),
            )
        ]

    yield StravaConfig


@Retry(ignore_exceptions=(AssertionError,))
def data_parsed(manager):
    _, output = manager.c.widget["stravawidget"].eval("self.display_text")
    assert output != ""


def test_strava_widget_display(manager_nospawn, strava):
    manager_nospawn.start(strava)
    data_parsed(manager_nospawn)
    assert manager_nospawn.c.widget["stravawidget"].info()["display_text"] == "Nov 31.1km"


def test_strava_widget_popup(manager_nospawn, strava):
    manager_nospawn.start(strava)
    data_parsed(manager_nospawn)
    manager_nospawn.c.bar["top"].fake_button_press(0, "top", 0, 0, 1)
    assert len(manager_nospawn.c.internal_windows()) == 2

    _, text = manager_nospawn.c.widget["stravawidget"].eval("self.popup.text")
    assert text == (
        " Date         Title            km       time     pace \n"
        "20 Nov: Test Activity 1         10.0    0:45:00   4:30\n"
        "21 Nov: Test Activity 2         21.1    1:45:00   4:58\n"
        "\n"
        "Nov 21: 2 runs                  31.1    2:30:00   4:49\n"
        "Oct 21: 0 runs                   0.0    0:00:00   0:00\n"
        "Sep 21: 0 runs                   0.0    0:00:00   0:00\n"
        "Aug 21: 0 runs                   0.0    0:00:00   0:00\n"
        "Jul 21: 0 runs                   0.0    0:00:00   0:00\n"
        "Jun 21: 0 runs                   0.0    0:00:00   0:00\n"
        "\n"
        "2021  : 2 runs                  31.1    2:30:00   4:49\n"
        "\n"
        "TOTAL : 2 runs                  31.1    2:30:00   4:49"
    )


def test_strava_deprecated_font_colour(caplog):
    widget = StravaWidget(font_colour="ffffff")

    assert caplog.record_tuples[0] == (
        "libqtile",
        logging.WARNING,
        "The use of `font_colour` is deprecated. "
        "Please update your config to use `foreground` instead.",
    )

    assert widget.foreground == "ffffff"
