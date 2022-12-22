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
import os
import tempfile

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import pytest

import qtile_extras.widget.githubnotifications
from test.helpers import Retry

ERROR = "error"

BAR_SIZE = 50
PADDING = 3
DEFAULT_ICON_SIZE = BAR_SIZE - 1 - (2 * PADDING)

COLOUR_ACTIVE = "ffffff"
COLOUR_INACTIVE = "808080"
COLOUR_ERROR = "ffff00"

REPLIES = [[], [{"message": "Dummy message"}]]


@Retry(ignore_exceptions=(AssertionError,))
def wait_for_poll(manager):
    _, state = manager.c.widget["githubnotifications"].eval("self._polling")
    assert state == "False"


@pytest.fixture
def token_file():
    with tempfile.TemporaryDirectory() as temp:
        token = os.path.join(temp, "token.file")
        with open(token, "w") as f:
            f.write("testing")
        yield token


@pytest.fixture
def response(request):
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
def githubnotification_manager(token_file, response, request, manager_nospawn, monkeypatch):
    # Patch the web request to provide dummy data
    monkeypatch.setattr("qtile_extras.widget.syncthing.requests.get", response)

    widget = qtile_extras.widget.githubnotifications.GithubNotifications(
        **{
            **{
                "token_file": token_file,
                "active_colour": COLOUR_ACTIVE,
                "inactive_colour": COLOUR_INACTIVE,
                "error_colour": COLOUR_ERROR,
            },
            **getattr(request, "param", dict()),
        }
    )

    class GithubNotificationsConfig(libqtile.confreader.Config):
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

    manager_nospawn.start(GithubNotificationsConfig)
    yield manager_nospawn


@pytest.mark.parametrize(
    "response,expected",
    [(False, COLOUR_INACTIVE), (True, COLOUR_ACTIVE), (ERROR, COLOUR_ERROR)],
    indirect=["response"],
)
def test_githubnotifications_colours(githubnotification_manager, expected):
    githubnotification_manager.c.widget["githubnotifications"].eval("self.update()")
    wait_for_poll(githubnotification_manager)
    _, colour = githubnotification_manager.c.widget["githubnotifications"].eval(
        "self.icon_colour"
    )
    assert colour == expected


@pytest.mark.parametrize(
    "response,githubnotification_manager,expected",
    [
        (
            False,
            {"token_file": "/does/not/exist"},
            ("No token_file provided.", "No access token provided."),
        ),
        (ERROR, {}, (None, "Github returned a 401 status code.")),
    ],
    indirect=["response", "githubnotification_manager"],
)
@pytest.mark.flaky(reruns=5)
def test_githubnotifications_logging(githubnotification_manager, logger, expected):
    setup, call = expected

    if setup:
        recs = logger.get_records("setup")
        assert recs
        assert recs[0].msg == setup

    if call:
        # The http request is in an asyncio future so we need to wait for
        # this to complete to check the log
        githubnotification_manager.c.widget["githubnotifications"].eval("self.update()")
        wait_for_poll(githubnotification_manager)

        recs = logger.get_records("call")
        assert recs
        assert recs[0].msg == call


@pytest.mark.parametrize(
    "response,githubnotification_manager,expected",
    [(False, {}, DEFAULT_ICON_SIZE + 2 * PADDING), (False, {"icon_size": 10}, 10 + 2 * PADDING)],
    indirect=["response", "githubnotification_manager"],
)
def test_githubnotifications_icon(githubnotification_manager, expected):
    info = githubnotification_manager.c.widget["githubnotifications"].info()
    assert info["width"] == expected


@pytest.mark.parametrize(
    "response,githubnotification_manager",
    [(False, {"token_file": "/does/not/exist"})],
    indirect=True,
)
@pytest.mark.flaky(reruns=5)
def test_githubnotifications_reload_token(githubnotification_manager, logger):
    logger.clear()
    githubnotification_manager.c.widget["githubnotifications"].reload_token()
    recs = logger.get_records("call")
    assert recs
    assert recs[0].msg == "No token_file provided."


def test_githubnotifications_timer_cancel():
    class Timer:
        def __init__(self):
            self._cancelled = False

        def cancelled(self):
            return self._cancelled

        def cancel(self):
            self._cancelled = True

    def no_op(*args, **kwargs):
        pass

    widget = qtile_extras.widget.githubnotifications.GithubNotifications()
    widget._timer = Timer()
    widget._load_token = no_op
    widget.update = no_op

    assert not widget._timer.cancelled()
    widget.reload_token()
    assert widget._timer.cancelled()
