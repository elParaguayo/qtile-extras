# This file is copied from https://github.com/qtile/qtile
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
from dbus_next.service import ServiceInterface, dbus_property, method


@pytest.fixture(scope="function")
def fake_bar():
    class _Drawer:
        def clear(self, *args, **kwargs):
            pass

        def draw(self, *args, **kwargs):
            pass

    class _Window:
        def create_drawer(self, *args, **kwargs):
            return _Drawer()

    from libqtile.bar import Bar

    height = 24
    b = Bar([], height)
    b.height = height
    b.horizontal = True
    b.window = _Window()
    return b


TEST_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(TEST_DIR), "data")


@pytest.fixture(scope="module")
def svg_img_as_pypath():
    "Return the py.path object of a svg image"
    import py

    audio_volume_muted = os.path.join(
        DATA_DIR,
        "svg",
        "audio-volume-muted.svg",
    )
    audio_volume_muted = py.path.local(audio_volume_muted)
    return audio_volume_muted


@pytest.fixture(scope="module")
def fake_qtile():
    import asyncio

    def no_op(*args, **kwargs):
        pass

    class FakeQtile:
        def __init__(self):
            self.register_widget = no_op

        # Widgets call call_soon(asyncio.create_task, self._config_async)
        # at _configure. The coroutine needs to be run in a loop to suppress
        # warnings
        def call_soon(self, func, *args):
            coroutines = [arg for arg in args if asyncio.iscoroutine(arg)]
            if coroutines:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                for func in coroutines:
                    loop.run_until_complete(func)
                loop.close()

        def call_later(self, *args, **kwargs):
            pass

    return FakeQtile()


# Fixture that defines a minimal configurations for testing widgets.
# When used in a test, the function needs to receive a list of screens
# (including bar and widgets) as an argument. This config can then be
# passed to the manager to start.
@pytest.fixture(scope="function")
def minimal_conf_noscreen():
    class MinimalConf(libqtile.confreader.Config):
        auto_fullscreen = False
        keys = []
        mouse = []
        groups = [libqtile.config.Group("a"), libqtile.config.Group("b")]
        layouts = [libqtile.layout.stack.Stack(num_stacks=1)]
        floating_layout = libqtile.resources.default_config.floating_layout
        screens = []

    return MinimalConf


@pytest.fixture(scope="function")
def dbus(monkeypatch):
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

    # Environment is set and dbus server should be running
    yield

    # Test is over so kill dbus session
    if pid:
        os.kill(pid, signal.SIGTERM)


# Fake UPower DBus Service

BAT0 = "/org/freedesktop/UPower/device/battery_BAT0"
BAT1 = "/org/freedesktop/UPower/device/battery_BAT1"


class Power(ServiceInterface):
    def __init__(self, *args, **kwargs):
        ServiceInterface.__init__(self, *args, **kwargs)
        self._charging = False

    @method()
    def EnumerateDevices(self) -> "ao":  # noqa: F821, N802
        return [BAT0, BAT1]

    @dbus_property(access=PropertyAccess.READ)
    def OnBattery(self) -> "b":  # noqa: F821, N802
        return not self._charging

    @method()
    def toggle_charge(self):
        self._charging = not self._charging
        self.emit_properties_changed({"OnBattery": self._charging})


class Battery(ServiceInterface):
    def __init__(self, native_path, server, *args, **kwargs):
        ServiceInterface.__init__(self, *args, **kwargs)
        self._level = 50.0
        self._native_path = native_path
        self._server = server

    @dbus_property(access=PropertyAccess.READ)
    def Percentage(self) -> "d":  # noqa: F821, N802
        return self._level

    @dbus_property(access=PropertyAccess.READ)
    def TimeToFull(self) -> "x":  # noqa: F821, N802
        if self._server._charging:
            return 3780
        return 0

    @dbus_property(access=PropertyAccess.READ)
    def TimeToEmpty(self) -> "x":  # noqa: F821, N802
        if not self._server._charging:
            return 12200
        return 0

    @dbus_property(access=PropertyAccess.READ)
    def NativePath(self) -> "s":  # noqa: F821, N802
        return self._native_path


class FakeUpower(Thread):
    """Class that runs fake UPower interface in a thread."""

    def __init__(self, *args, **kwargs):
        Thread.__init__(self, *args, **kwargs)

    async def start_server(self):
        """Connects to the bus and publishes 3 interfaces."""
        bus = await MessageBus().connect()

        # Create UPower and 2 battery interfaces
        po = Power("org.freedesktop.UPower")
        bat0 = Battery("BAT0", po, "org.freedesktop.UPower.Device")
        bat1 = Battery("BAT1", po, "org.freedesktop.UPower.Device")

        # Export interfaces on the bus
        bus.export("/org/freedesktop/UPower", po)
        bus.export(BAT0, bat0)
        bus.export(BAT1, bat1)

        # Request the service name
        await bus.request_name("test.qtileextras.upower")

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

    t = FakeUpower()
    t.daemon = True
    t.start()

    # Pause for the dbus interface to come up
    time.sleep(1)

    yield

    # Stop the bus
    if pid:
        os.kill(pid, signal.SIGTERM)
