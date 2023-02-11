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
import asyncio
import os
import shutil
import signal
import subprocess
import time
from threading import Thread

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import pytest
from dbus_next.aio import MessageBus
from dbus_next.constants import PropertyAccess
from dbus_next.message import Variant
from dbus_next.service import ServiceInterface, dbus_property, method

import qtile_extras.widget.mpris2widget as mp
from test.helpers import Retry

MPRIS_SERVICE = "org.mpris.MediaPlayer2.qtile-extras"


@Retry(ignore_exceptions=(AssertionError,))
def wait_for_player(widget):
    assert widget.info()["player"] == "qtile-extras"


@Retry(ignore_exceptions=(AssertionError,))
def assert_window_count(manager, number):
    assert len(manager.c.internal_windows()) == number


@Retry(ignore_exceptions=(AssertionError,))
def assert_is_playing(widget, playing=True):
    isplaying = widget.info()["isplaying"]
    assert isplaying if playing else not isplaying


class TestPlayer(ServiceInterface):
    @dbus_property(access=PropertyAccess.READ)
    def Identity(self) -> "s":  # noqa: F821, N802
        return "qtile-extras"


class TestPlayerControls(ServiceInterface):
    def __init__(self, *args, **kwargs):
        ServiceInterface.__init__(self, *args, **kwargs)
        self.metadata = {
            "xesam:title": Variant("s", "Never Gonna Give You Up"),
            "xesam:album": Variant("s", "Rick Rolled"),
            "xesam:artist": Variant("as", ["Rick Astley"]),
        }
        self.state = "Stopped"

    def _check_state(self, new_state):
        old_state = self.state
        self.state = new_state
        if old_state != new_state:
            self.emit_properties_changed(
                {"PlaybackStatus": self.state, "Metadata": self.metadata}
            )

    @method()
    def Play(self):  # noqa: F821, N802
        self._check_state("Playing")

    @method()
    def PlayPause(self):  # noqa: F821, N802
        if self.state == "Playing":
            state = "Paused"
        else:
            state = "Playing"
        self._check_state(state)

    @method()
    def Pause(self):  # noqa: F821, N802
        self._check_state("Paused")

    @method()
    def Stop(self):  # noqa: F821, N802
        self._check_state("Stopped")

    @dbus_property(access=PropertyAccess.READ)
    def Metadata(self) -> "a{sv}":  # noqa: F722, F821, N802
        return self.metadata

    @dbus_property(access=PropertyAccess.READ)
    def PlaybackStatus(self) -> "s":  # noqa: F821, N802
        return self.state


class FakeMprisPlayer(Thread):
    """Class that runs fake UPower interface in a thread."""

    def __init__(self, *args, **kwargs):
        Thread.__init__(self, *args, **kwargs)

    async def start_server(self):
        """Connects to the bus and publishes 3 interfaces."""
        bus = await MessageBus().connect()

        prog = TestPlayer("org.mpris.MediaPlayer2")
        controls = TestPlayerControls("org.mpris.MediaPlayer2.Player")

        # Export interfaces on the bus
        bus.export("/org/mpris/MediaPlayer2", prog)
        bus.export("/org/mpris/MediaPlayer2", controls)

        # Request the service name
        await bus.request_name(MPRIS_SERVICE)

        await asyncio.get_event_loop().create_future()

    def run(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.start_server())


@pytest.fixture()
def dbus_thread(monkeypatch):
    """
    Start a thread which publishes a fake UPower interface on dbus.

    For some reason, I can't use the "dbus" fixture so I have to recreate
    it here.
    """
    # for Github CI/Ubuntu, dbus-launch is provided by "dbus-x11" package
    launcher = shutil.which("dbus-launch")

    # If dbus-launch can't be found then tests will fail so we
    # need to skip
    if launcher is None:
        pytest.skip("dbus-launch must be installed")

    # dbus-launch prints two lines which should be set as
    # environmental variables
    result = subprocess.run(launcher, capture_output=True)

    pid = None
    for line in result.stdout.decode().splitlines():
        # dbus server addresses can have multiple "=" so
        # we use partition to split by the first one onle
        var, _, val = line.partition("=")

        # Use monkeypatch to set these variables so they are
        # removed at end of test.
        monkeypatch.setitem(os.environ, var, val)

        # We want the pid so we can kill the process when the
        # test is finished
        if var == "DBUS_SESSION_BUS_PID":
            try:
                pid = int(val)
            except ValueError:
                pass

    t = FakeMprisPlayer()
    t.daemon = True
    t.start()

    # Pause for the dbus interface to come up
    time.sleep(1)

    yield

    # Stop the bus
    if pid:
        os.kill(pid, signal.SIGTERM)


mpris_player = pytest.mark.usefixtures("dbus_thread")


@pytest.fixture(scope="function")
def mpris_manager(manager_nospawn):
    widget = mp.Mpris2(objname=MPRIS_SERVICE, scroll=False)

    class Mpris2Config(libqtile.confreader.Config):
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
                    50,
                ),
            )
        ]

    manager_nospawn.start(Mpris2Config)
    yield manager_nospawn


@pytest.mark.parametrize(
    "input,output",
    [
        ("file:///path/to/local/file", "/path/to/local/file"),
        (
            "https://open.spotify.com/image/ab67616d00001e025d8eb7e49ddb4a793f00044d",
            "https://i.scdn.co/image/ab67616d00001e025d8eb7e49ddb4a793f00044d",
        ),
    ],
)
def test_mpris2_parse_artwork(input, output):
    assert mp.parse_artwork(input) == output


@mpris_player
def test_mpris2_popup(mpris_manager):
    number = len(mpris_manager.c.internal_windows())
    widget = mpris_manager.c.widget["mpris2"]
    widget.play_pause()
    wait_for_player(widget)

    widget.toggle_player()
    assert_window_count(mpris_manager, number + 1)

    control_test = [
        ("title", "Never Gonna Give You Up"),
        ("artist", "Rick Astley"),
        ("album", "Rick Rolled"),
    ]

    for name, expected in control_test:
        _, value = widget.eval(f"self.extended_popup._updateable_controls['{name}'].text")
        assert value == expected

    _, position = widget.eval("self.extended_popup._updateable_controls['progress'].value")
    assert position == "0"

    assert_is_playing(widget)
    widget.eval("self.extended_popup._updateable_controls['stop'].button_press(0, 0, 1)")
    assert_is_playing(widget, False)
