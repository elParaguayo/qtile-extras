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
import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import pytest

import qtile_extras.widget.snapcast
from test.helpers import Retry

ERROR = "error"

BAR_SIZE = 50
PADDING = 3
DEFAULT_ICON_SIZE = BAR_SIZE - 1 - (2 * PADDING)

COLOUR_ACTIVE = "ffffff"
COLOUR_INACTIVE = "808080"
COLOUR_ERROR = "ffff00"

REPLIES = [
    # Copied from https://github.com/badaix/snapcast/blob/master/doc/json_rpc_api/control.md#servergetstatus
    {
        "id": 1,
        "jsonrpc": "2.0",
        "result": {
            "server": {
                "groups": [
                    {
                        "clients": [
                            {
                                "config": {
                                    "instance": 2,
                                    "latency": 6,
                                    "name": "123 456",
                                    "volume": {"muted": False, "percent": 48},
                                },
                                "connected": True,
                                "host": {
                                    "arch": "x86_64",
                                    "ip": "127.0.0.1",
                                    "mac": "00:21:6a:7d:74:fc",
                                    "name": "T400",
                                    "os": "Linux Mint 17.3 Rosa",
                                },
                                "id": "00:21:6a:7d:74:fc#2",
                                "lastSeen": {"sec": 1488025696, "usec": 578142},
                                "snapclient": {
                                    "name": "Snapclient",
                                    "protocolVersion": 2,
                                    "version": "0.10.0",
                                },
                            },
                            {
                                "config": {
                                    "instance": 1,
                                    "latency": 0,
                                    "name": "",
                                    "volume": {"muted": False, "percent": 81},
                                },
                                "connected": True,
                                "host": {
                                    "arch": "x86_64",
                                    "ip": "192.168.0.54",
                                    "mac": "00:21:6a:7d:74:fc",
                                    "name": "T400",
                                    "os": "Linux Mint 17.3 Rosa",
                                },
                                "id": "00:21:6a:7d:74:fc",
                                "lastSeen": {"sec": 1488025696, "usec": 611255},
                                "snapclient": {
                                    "name": "Snapclient",
                                    "protocolVersion": 2,
                                    "version": "0.10.0",
                                },
                            },
                        ],
                        "id": "4dcc4e3b-c699-a04b-7f0c-8260d23c43e1",
                        "muted": False,
                        "name": "",
                        "stream_id": "stream 2",
                    }
                ],
                "server": {
                    "host": {
                        "arch": "x86_64",
                        "ip": "",
                        "mac": "",
                        "name": "T400",
                        "os": "Linux Mint 17.3 Rosa",
                    },
                    "snapserver": {
                        "controlProtocolVersion": 1,
                        "name": "Snapserver",
                        "protocolVersion": 1,
                        "version": "0.10.0",
                    },
                },
                "streams": [
                    {
                        "id": "stream 1",
                        "status": "idle",
                        "uri": {
                            "fragment": "",
                            "host": "",
                            "path": "/tmp/snapfifo",
                            "query": {
                                "chunk_ms": "20",
                                "codec": "flac",
                                "name": "stream 1",
                                "sampleformat": "48000:16:2",
                            },
                            "raw": "pipe:///tmp/snapfifo?name=stream 1",
                            "scheme": "pipe",
                        },
                    },
                    {
                        "id": "stream 2",
                        "status": "idle",
                        "uri": {
                            "fragment": "",
                            "host": "",
                            "path": "/tmp/snapfifo",
                            "query": {
                                "chunk_ms": "20",
                                "codec": "flac",
                                "name": "stream 2",
                                "sampleformat": "48000:16:2",
                            },
                            "raw": "pipe:///tmp/snapfifo?name=stream 2",
                            "scheme": "pipe",
                        },
                    },
                ],
            }
        },
    }
]


@Retry(ignore_exceptions=(AssertionError,))
def wait_for_poll(manager):
    _, streams = manager.c.widget["snapcast"].eval("hasattr(self, 'streams')")
    assert streams == "True"


@pytest.fixture
def response(request):
    param = getattr(request, "param", True)

    def post(*args, **kwargs):
        class Response:
            def json(*args, **kwargs):
                """Quick object to return recording data."""

                return REPLIES[0]

            @property
            def status_code(self):
                if param == ERROR:
                    return 401

                return 200

        return Response()

    yield post


@pytest.fixture(scope="function")
def snapcast_manager(response, request, manager_nospawn, monkeypatch):
    # Patch the web request to provide dummy data
    monkeypatch.setattr("qtile_extras.widget.snapcast.requests.post", response)

    widget = qtile_extras.widget.snapcast.SnapCast(
        **{
            **{
                "snapclient": "/usr/bin/sleep",
                "options": "10",
                "client_name": "T400",
                "active_colour": COLOUR_ACTIVE,
                "inactive_colour": COLOUR_INACTIVE,
                "error_colour": COLOUR_ERROR,
            },
            **getattr(request, "param", dict()),
        }
    )

    class SnapcastConfig(libqtile.confreader.Config):
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

    manager_nospawn.start(SnapcastConfig)
    yield manager_nospawn


@pytest.mark.parametrize(
    "snapcast_manager,expected",
    [({}, DEFAULT_ICON_SIZE + 2 * PADDING), ({"icon_size": 20}, 20 + 2 * PADDING)],
    indirect=["snapcast_manager"],
)
def test_snapcast_icon(snapcast_manager, expected):
    info = snapcast_manager.c.widget["snapcast"].info()
    assert info["length"] == expected


@pytest.mark.parametrize(
    "snapcast_manager,expected",
    [({}, COLOUR_ACTIVE), ({"client_name": "T500"}, COLOUR_ERROR)],
    indirect=["snapcast_manager"],
)
def test_snapcast_icon_colour(snapcast_manager, expected):
    widget = snapcast_manager.c.widget["snapcast"]
    wait_for_poll(snapcast_manager)

    _, colour = widget.eval("self.status_colour")
    assert colour == COLOUR_INACTIVE

    widget.toggle_state()

    _, colour = widget.eval("self.status_colour")
    assert colour == expected

    widget.toggle_state()

    _, colour = widget.eval("self.status_colour")
    assert colour == COLOUR_INACTIVE


@pytest.mark.parametrize("response", [ERROR], indirect=True)
@pytest.mark.flaky(reruns=5)
def test_snapcast_http_error(snapcast_manager, logger):
    wait_for_poll(snapcast_manager)
    recs = logger.get_records("call")
    assert recs
    assert recs[0].levelname == "WARNING"
    assert recs[0].msg == "Unable to connect to snapcast server."


def test_snapcast_options(fake_qtile, fake_bar):
    snap = qtile_extras.widget.snapcast.SnapCast(options="-s pipewire")
    snap._configure(fake_qtile, fake_bar)
    assert snap._cmd == ["/usr/bin/snapclient", "-s", "pipewire"]
