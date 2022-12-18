# Copyright (c) 2022 elParaguayo
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
import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import pytest

import qtile_extras.widget.syncthing

ERROR = "error"
BAR_SIZE = 50
DEFAULT_PROGRESS_BAR_SIZE = 75
PADDING = 3
DEFAULT_ICON_SIZE = BAR_SIZE - 1 - (2 * PADDING)

REPLIES = [
    {
        "completion": 100,
        "globalBytes": 4000000000,
        "globalItems": 100,
        "needBytes": 0,
        "needDeletes": 0,
        "needItems": 0,
        "remoteState": "unknown",
        "sequence": 0,
    },
    {
        "completion": 90,
        "globalBytes": 4000000000,
        "globalItems": 101,
        "needBytes": 1000000,
        "needDeletes": 0,
        "needItems": 0,
        "remoteState": "unknown",
        "sequence": 0,
    },
]


@pytest.fixture
def is_syncing(request):
    def get(*args, **kwargs):
        class Response:
            def json(*args, **kwargs):
                """Quick object to return recording data."""

                if request.param:
                    return REPLIES[1]

                return REPLIES[0]

            @property
            def status_code(self):
                if request.param == ERROR:
                    return 401

                return 200

        return Response()

    yield get


@pytest.fixture(scope="function")
def syncthing_manager(is_syncing, request, manager_nospawn, monkeypatch):
    """
    Fixture provides a manager instance but needs to be configured with
    tuple that will initiate a datetime object to be parsed for
    datetime.now.
    """
    # Patch the web request to provide dummy data
    monkeypatch.setattr("qtile_extras.widget.syncthing.requests.get", is_syncing)

    # Initialise the widget. Set the api_key by default to supppress logging but it can be
    # overriden.
    widget = qtile_extras.widget.syncthing.Syncthing(
        **{**{"api_key": "apikey"}, **getattr(request, "param", dict())}
    )

    class SyncthingConfig(libqtile.confreader.Config):
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
                    [widget],
                    BAR_SIZE,
                ),
            )
        ]

    manager_nospawn.start(SyncthingConfig)
    yield manager_nospawn


@pytest.mark.parametrize("is_syncing", [False], indirect=True)
@pytest.mark.parametrize(
    "syncthing_manager,expected",
    [({}, 0), ({"hide_on_idle": False}, DEFAULT_ICON_SIZE + 2 * PADDING)],
    indirect=["syncthing_manager"],
)
def test_syncthing_not_syncing(syncthing_manager, expected):
    info = syncthing_manager.c.widget["syncthing"].info()
    assert info["width"] == expected


@pytest.mark.parametrize("is_syncing", [True], indirect=True)
@pytest.mark.parametrize(
    "syncthing_manager,expected",
    [
        ({}, DEFAULT_ICON_SIZE + 2 * PADDING),
        ({"hide_on_idle": False}, DEFAULT_ICON_SIZE + 2 * PADDING),
        ({"icon_size": 10}, 10 + 2 * PADDING),
        ({"show_bar": True}, DEFAULT_ICON_SIZE + DEFAULT_PROGRESS_BAR_SIZE + 3 * PADDING),
        ({"show_bar": True, "bar_width": 50}, DEFAULT_ICON_SIZE + 50 + 3 * PADDING),
        ({"show_bar": True, "show_icon": False}, DEFAULT_PROGRESS_BAR_SIZE + (2 * PADDING)),
    ],
    indirect=["syncthing_manager"],
)
def test_syncthing_is_syncing(syncthing_manager, expected):
    info = syncthing_manager.c.widget["syncthing"].info()
    assert info["width"] == expected


@pytest.mark.parametrize("is_syncing", [True], indirect=True)
@pytest.mark.parametrize(
    "syncthing_manager",
    [{"api_key": None}],
    indirect=True,
)
def test_syncthing_no_api_key(syncthing_manager, logger):
    recs = logger.get_records("setup")
    assert recs
    assert recs[0].levelname == "WARNING"
    assert recs[0].msg == "API key not set."


@pytest.mark.parametrize("is_syncing", [ERROR], indirect=True)
def test_syncthing_http_error(syncthing_manager, logger):
    recs = logger.get_records("setup")
    assert recs
    assert recs[0].levelname == "WARNING"
    assert recs[0].msg == "401 error accessing Syncthing server."
