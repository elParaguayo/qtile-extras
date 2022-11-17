# Copyright (c) p2021 elParaguayo
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

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import pytest
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

import qtile_extras.widget.tvheadend

NOW = int(datetime(2021, 11, 26, 19, 0).timestamp())
FIVE_MINS = 5 * 60
QUARTER_HOUR = 15 * 60

RECORDINGS = {
    "entries": [
        {
            "channelname": "BBC ONE HD",
            "creator": "elParaguayo",
            "duplicate": 0,
            "errorcode": 0,
            "filename": "",
            "start": NOW - FIVE_MINS,
            "stop": NOW + QUARTER_HOUR,
            "disp_subtitle": "Fake Recording #1",
            "disp_title": "TVH Widget Test 1",
            "uuid": "edcba09876543321",
        },
        {
            "channelname": "BBC ONE HD",
            "creator": "elParaguayo",
            "duplicate": 0,
            "errorcode": 0,
            "filename": "",
            "start": NOW + FIVE_MINS,
            "stop": NOW + QUARTER_HOUR,
            "disp_subtitle": "Fake Recording #2",
            "disp_title": "TVH Widget Test 2",
            "uuid": "1234567890abcde",
        },
    ]
}


def fake_post(*args, **kwargs):
    """Quick object to return recording data."""

    class Response:
        def json(*args, **kwargs):
            return RECORDINGS

    return Response()


@pytest.fixture(scope="function")
def tvh_manager(request, manager_nospawn, monkeypatch):
    """
    Fixture provides a manager instance but needs to be configured with
    tuple that will initiate a datetime object to be parsed for
    datetime.now.
    """

    class MockDatetime(datetime):
        """Mock object returning date/time set by parameterize."""

        @classmethod
        def now(cls, *args, **kwargs):
            return cls(*request.param)

    # Patch some objects
    monkeypatch.setattr("qtile_extras.widget.tvheadend.requests.post", fake_post)
    monkeypatch.setattr("qtile_extras.widget.tvheadend.datetime", MockDatetime)

    class TVHConfig(libqtile.confreader.Config):
        """Config for the test."""

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
                    [qtile_extras.widget.tvheadend.TVHWidget(startup_delay=0)],
                    50,
                ),
            )
        ]

    manager_nospawn.start(TVHConfig)
    yield manager_nospawn


@pytest.mark.parametrize("tvh_manager", [(2021, 11, 26, 18, 45)], indirect=True)
def test_tvh_widget_not_recording(tvh_manager):
    """No live recordings."""
    info = tvh_manager.c.widget["tvhwidget"].info()
    assert not info["recording"]
    assert info["scheduled_recordings"] == 2


@pytest.mark.parametrize("tvh_manager", [(2021, 11, 26, 19, 5)], indirect=True)
def test_tvh_widget_recording(tvh_manager):
    """Live recording."""
    info = tvh_manager.c.widget["tvhwidget"].info()

    # Call 'draw' to make sure the 'draw_highlight' method is called
    # (even though we can't test it!)
    tvh_manager.c.widget["tvhwidget"].eval("self.draw()")

    # Check that widget shows as recording
    assert info["recording"]
    assert info["scheduled_recordings"] == 2


@pytest.mark.parametrize("tvh_manager", [(2021, 11, 26, 19, 5)], indirect=True)
def test_tvh_widget_popup(tvh_manager):
    """Test the popup displays the correct information."""
    tvh_manager.c.bar["top"].fake_button_press(0, "top", 0, 0, 1)
    _, text = tvh_manager.c.widget["tvhwidget"].eval("self.popup.text")
    assert text == (
        "Upcoming recordings:\n"
        "Fri 26 Nov 18:55: TVH Widget Test 1\n"
        "Fri 26 Nov 19:05: TVH Widget Test 2"
    )

    # Popup hides when clicked again.
    tvh_manager.c.bar["top"].fake_button_press(0, "top", 0, 0, 1)
    _, result = tvh_manager.c.widget["tvhwidget"].eval("self.popup is None")
    assert result == "True"


@pytest.mark.parametrize(
    "authtype,expected",
    [("digest", HTTPDigestAuth), ("basic", HTTPBasicAuth), ("other", HTTPBasicAuth)],
)
def test_tvh_widget_auth(monkeypatch, authtype, expected):
    """Simple test to check auth parameters are handled correctly."""

    def no_op(*args, **kwargs):
        pass

    class Drawer:
        def draw(self, *args, **kwargs):
            pass

    monkeypatch.setattr("qtile_extras.widget.tvheadend.base._Widget._configure", no_op)
    monkeypatch.setattr("qtile_extras.widget.tvheadend.TVHWidget.timeout_add", no_op)
    monkeypatch.setattr("qtile_extras.widget.tvheadend.TVHWidget.setup_images", no_op)
    monkeypatch.setattr("qtile_extras.widget.tvheadend.TVHWidget.configure_decorations", no_op)

    tvh = qtile_extras.widget.tvheadend.TVHWidget(
        auth=("TESTUSER", "PASSWORD"), auth_type=authtype
    )
    tvh.drawer = Drawer()
    tvh._configure(None, None)
    assert tvh.auth
    assert isinstance(tvh.auth, expected)
