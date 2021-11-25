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
from dbus_next.constants import BusType, PropertyAccess
from dbus_next.service import ServiceInterface, dbus_property, method

from qtile_extras.widget.upower import UPowerWidget
from test.helpers import Retry  # noqa: I001

BAT0 = "/org/freedesktop/UPower/device/battery_BAT0"
BAT1 = "/org/freedesktop/UPower/device/battery_BAT1"


@Retry(ignore_exceptions=(AssertionError, ))
def battery_found(manager):
    """Waits for widget to report batteries."""
    _, output = manager.c.widget["upowerwidget"].eval("len(self.batteries)")
    while int(output) == 0:
        # If there are no batteries (shouldn't happen) try looking again.
        manager.c.widget["upowerwidget"].eval("import asyncio;asyncio.create_task(self._find_batteries())")
        assert False
    assert True


@Retry(ignore_exceptions=(AssertionError, ))
def text_hidden(manager, target):
    """Waits for widget to hide text."""
    assert manager.c.widget["upowerwidget"].info()["width"] == target


class Power(ServiceInterface):
    def __init__(self, *args, **kwargs):
        ServiceInterface.__init__(self, *args, **kwargs)
        self._charging = False

    @method()
    def enumerate_devices(self) -> 'ao':  # noqa: F821
        return [BAT0, BAT1]

    @dbus_property(access=PropertyAccess.READ)
    def on_battery(self) -> 'b':  # noqa: F821
        return not self._charging

    @method()
    def toggle_charge(self):
        self._charging = not self._charging
        self.emit_properties_changed({'on_battery': self._charging})


class Battery(ServiceInterface):
    def __init__(self, native_name, server, *args, **kwargs):
        ServiceInterface.__init__(self, *args, **kwargs)
        self._level = 50.0
        self._native_name = native_name
        self._server = server

    @dbus_property(access=PropertyAccess.READ)
    def Percentage(self) -> 'd':  # noqa: F821, N802
        return self._level

    @dbus_property(access=PropertyAccess.READ)
    def TimeToFull(self) -> 'x':  # noqa: F821, N802
        if self._server._charging:
            return 3780
        return 0

    @dbus_property(access=PropertyAccess.READ)
    def TimeToEmpty(self) -> 'x':  # noqa: F821, N802
        if not self._server._charging:
            return 12200
        return 0

    @dbus_property(access=PropertyAccess.READ)
    def NativeName(self) -> 's':  # noqa: F821, N802
        return self._native_name


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


@pytest.fixture
def powerwidget(monkeypatch):
    """Patch the widget to use the fake dbus service."""
    monkeypatch.setattr("qtile_extras.widget.upower.UPOWER_SERVICE", "test.qtileextras.upower")
    monkeypatch.setattr("qtile_extras.widget.upower.UPOWER_BUS", BusType.SESSION)
    yield UPowerWidget


@pytest.fixture(scope="function")
def powerconfig(request, powerwidget):
    """Config for the UPower widget. Parameters set via request."""
    class PowerConfig(libqtile.confreader.Config):
        auto_fullscreen = True
        keys = [
        ]
        mouse = []
        groups = [
            libqtile.config.Group("a"),
        ]
        layouts = [libqtile.layout.Max()]
        floating_layout = libqtile.resources.default_config.floating_layout
        screens = [
            libqtile.config.Screen(
                top=libqtile.bar.Bar(
                    [
                        powerwidget(**getattr(request, "param", dict()))
                    ],
                    50,
                ),
            )
        ]

    yield PowerConfig


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


upower_dbus_servive = pytest.mark.usefixtures("dbus_thread")


@upower_dbus_servive
def test_upower_all_batteries(manager_nospawn, powerconfig):
    manager_nospawn.start(powerconfig)
    battery_found(manager_nospawn)
    assert len(manager_nospawn.c.widget["upowerwidget"].info()["batteries"]) == 2


@upower_dbus_servive
@pytest.mark.parametrize("powerconfig", [{"battery_name": "BAT1"}], indirect=True)
def test_upower_named_battery(manager_nospawn, powerconfig):
    manager_nospawn.start(powerconfig)
    battery_found(manager_nospawn)
    assert len(manager_nospawn.c.widget["upowerwidget"].info()["batteries"]) == 1
    assert manager_nospawn.c.widget["upowerwidget"].info()["batteries"][0]["name"] == "BAT1"
    assert manager_nospawn.c.widget["upowerwidget"].info()["batteries"][0]["status"] == "Normal"


@upower_dbus_servive
@pytest.mark.parametrize("powerconfig", [{"battery_name": "BAT1", "percentage_low": 0.6}], indirect=True)
def test_upower_low_battery(manager_nospawn, powerconfig):
    manager_nospawn.start(powerconfig)
    battery_found(manager_nospawn)
    assert len(manager_nospawn.c.widget["upowerwidget"].info()["batteries"]) == 1
    assert manager_nospawn.c.widget["upowerwidget"].info()["batteries"][0]["status"] == "Low"


@upower_dbus_servive
@pytest.mark.parametrize(
    "powerconfig",
    [{"battery_name": "BAT1", "percentage_low": 0.7, "percentage_critical": 0.55}],
    indirect=True
)
def test_upower_critical_battery(manager_nospawn, powerconfig):
    manager_nospawn.start(powerconfig)
    battery_found(manager_nospawn)
    assert len(manager_nospawn.c.widget["upowerwidget"].info()["batteries"]) == 1
    assert manager_nospawn.c.widget["upowerwidget"].info()["batteries"][0]["status"] == "Critical"


@upower_dbus_servive
@pytest.mark.parametrize("powerconfig", [{"battery_name": "BAT1"}], indirect=True)
def test_upower_charging(manager_nospawn, powerconfig):
    manager_nospawn.start(powerconfig)
    battery_found(manager_nospawn)
    assert len(manager_nospawn.c.widget["upowerwidget"].info()["batteries"]) == 1
    assert manager_nospawn.c.widget["upowerwidget"].info()["batteries"][0]["name"] == "BAT1"
    assert not manager_nospawn.c.widget["upowerwidget"].info()["charging"]
    assert manager_nospawn.c.widget["upowerwidget"].info()["batteries"][0]["tte"] == "3:23"
    assert not manager_nospawn.c.widget["upowerwidget"].info()["batteries"][0]["ttf"]

    # Trigger our method to toggle the charging state of the batteries
    dbussend = shutil.which("dbus-send")
    subprocess.run([
        dbussend,
        f"--bus={os.environ['DBUS_SESSION_BUS_ADDRESS']}",
        "--type=method_call",
        "--dest=test.qtileextras.upower",
        "/org/freedesktop/UPower",
        "org.freedesktop.UPower.toggle_charge"
    ])

    assert manager_nospawn.c.widget["upowerwidget"].info()["charging"]
    assert manager_nospawn.c.widget["upowerwidget"].info()["batteries"][0]["ttf"] == "1:03"
    assert not manager_nospawn.c.widget["upowerwidget"].info()["batteries"][0]["tte"]


@upower_dbus_servive
@pytest.mark.parametrize("powerconfig", [{"battery_name": "BAT1", "text_displaytime": 0.5}], indirect=True)
def test_upower_show_text(manager_nospawn, powerconfig):
    manager_nospawn.start(powerconfig)
    battery_found(manager_nospawn)
    assert len(manager_nospawn.c.widget["upowerwidget"].info()["batteries"]) == 1
    assert manager_nospawn.c.widget["upowerwidget"].info()["batteries"][0]["name"] == "BAT1"
    orig_width = manager_nospawn.c.widget["upowerwidget"].info()["width"]

    # Click on widget shows text so it should be wider now
    manager_nospawn.c.bar["top"].fake_button_press(0, "top", 0, 0, 1)
    assert manager_nospawn.c.widget["upowerwidget"].info()["width"] != orig_width

    # Click again to hide text so it's back to original width
    manager_nospawn.c.bar["top"].fake_button_press(0, "top", 0, 0, 1)
    assert manager_nospawn.c.widget["upowerwidget"].info()["width"] == orig_width

    # Check this still works when battery is charging
    # Trigger our method to toggle the charging state of the batteries
    dbussend = shutil.which("dbus-send")
    subprocess.run([
        dbussend,
        f"--bus={os.environ['DBUS_SESSION_BUS_ADDRESS']}",
        "--type=method_call",
        "--dest=test.qtileextras.upower",
        "/org/freedesktop/UPower",
        "org.freedesktop.UPower.toggle_charge"
    ])

    # Click on widget shows text so it should be wider now
    manager_nospawn.c.bar["top"].fake_button_press(0, "top", 0, 0, 1)
    assert manager_nospawn.c.widget["upowerwidget"].info()["width"] != orig_width

    # Let the timer hide the text
    text_hidden(manager_nospawn, orig_width)
