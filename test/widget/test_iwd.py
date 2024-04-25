# Copyright (c) 2023 elParaguayo
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

import pytest
from dbus_next import Variant
from dbus_next._private.address import get_session_bus_address
from dbus_next.aio import MessageBus
from dbus_next.constants import PropertyAccess
from dbus_next.service import ServiceInterface, dbus_property, method
from libqtile.bar import Bar
from libqtile.config import Screen

from qtile_extras.widget.iwd import (
    IWD,
    IWD_DEVICE,
    IWD_MANAGER,
    IWD_NETWORK,
    IWD_SERVICE,
    IWD_STATION,
    IWD_STATION_DIAGNOSTIC,
)
from test.conftest import BareConfig
from test.helpers import Retry


class Device(ServiceInterface):
    def __init__(self, *args, device_name="", powered=True, **kwargs):
        ServiceInterface.__init__(self, IWD_DEVICE, *args, **kwargs)
        self._name = device_name
        self._powered = powered

    @dbus_property(access=PropertyAccess.READ)
    def Name(self) -> "s":  # noqa: F821, N802
        return self._name

    @dbus_property(access=PropertyAccess.READ)
    def Powered(self) -> "b":  # noqa: F821, N802
        return self._powered


class Station(ServiceInterface):
    def __init__(self, *args, state="", connected_network="", **kwargs):
        ServiceInterface.__init__(self, IWD_STATION, *args, **kwargs)
        self._state = state
        self._connected_network = connected_network
        self._scanning = False

    @dbus_property(access=PropertyAccess.READ)
    def State(self) -> "s":  # noqa: F821, N802
        return self._state

    @dbus_property(access=PropertyAccess.READ)
    def ConnectedNetwork(self) -> "o":  # noqa: F821, N802
        return self._connected_network

    @dbus_property(access=PropertyAccess.READ)
    def Scanning(self) -> "b":  # noqa: F821, N802
        return self._scanning

    @method()
    def Scan(self) -> None:  # noqa: N802
        self._scanning = not self._scanning
        self.emit_properties_changed({"Scanning": self._scanning})


class StationDiagnostics(ServiceInterface):
    def __init__(self, *args, **kwargs):
        ServiceInterface.__init__(self, IWD_STATION_DIAGNOSTIC, *args, **kwargs)

    @method()
    def GetDiagnostics(self) -> "a{sv}":  # noqa: F821, N802, F722
        return {"RSSI": Variant("n", -75)}


class Network(ServiceInterface):
    def __init__(self, *args, connected=False, name="", known="", network_type="", **kwargs):
        ServiceInterface.__init__(self, IWD_NETWORK, *args, **kwargs)
        self._connected = connected
        self._name = name
        self._known = known
        self._type = network_type

    @dbus_property(access=PropertyAccess.READ)
    def Name(self) -> "s":  # noqa: F821, N802
        return self._name

    @dbus_property(access=PropertyAccess.READ)
    def Connected(self) -> "b":  # noqa: F821, N802
        return self._connected

    @dbus_property(access=PropertyAccess.READ)
    def KnownNetwork(self) -> "o":  # noqa: F821, N802
        return self._known

    @dbus_property(access=PropertyAccess.READ)
    def Type(self) -> "s":  # noqa: F821, N802
        return self._type

    @method()
    def Connect(self):  # noqa: F821, N802
        pass


class KnownNetwork(ServiceInterface):
    def __init__(self, *args, **kwargs):
        ServiceInterface.__init__(self, IWD_SERVICE + ".KnownNetwork", *args, **kwargs)


class AgentManager(ServiceInterface):
    def __init__(self, *args, **kwargs):
        ServiceInterface.__init__(self, IWD_MANAGER, *args, **kwargs)

    @method()
    def RegisterAgent(self, path: "o") -> None:  # noqa: F821, N802
        pass

    @method()
    def UnregisterAgent(self, path: "o") -> None:  # noqa: F821, N802
        pass


class IWDService(Thread):
    """Class that runs fake IWD service in a thread."""

    async def start_server(self):
        """Connects to the bus and publishes 3 interfaces."""
        bus = await MessageBus().connect()
        root = ServiceInterface("test.qtile_extras.root")
        bus.export("/", root)

        iwd_root = "/net/connman/iwd"
        device_root = iwd_root + "/0/3"
        connected_network = device_root + "/12345678_psk"
        open_network = device_root + "/24681357_open"
        eap_network = device_root + "/11223344_8021x"
        known_network = iwd_root + "/12345678_psk"

        bus.export(iwd_root, AgentManager())

        device = Device(device_name="wlan0")
        station = Station(state="connected", connected_network=connected_network)
        diagnostics = StationDiagnostics()

        bus.export(device_root, device)
        bus.export(device_root, station)
        bus.export(device_root, diagnostics)

        bus.export(known_network, KnownNetwork())

        bus.export(
            connected_network,
            Network(connected=True, name="qtile_extras", known=known_network, network_type="psk"),
        )

        # We need to include a known network path here otherwise dbus_next will spit out an error about an
        # invalid path (according to spec, empty strings are not allowed...)
        bus.export(open_network, Network(name="open_network", network_type="open", known="/"))
        bus.export(eap_network, Network(name="8021x_network", network_type="8021x", known="/"))

        # Request the service name
        await bus.request_name(IWD_SERVICE)

        await asyncio.get_event_loop().create_future()

    def run(self):
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self.start_server())


@pytest.fixture()
def dbus_thread(monkeypatch):
    """Start a thread which publishes a fake bluez interface on dbus."""
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

    t = IWDService()
    t.daemon = True
    t.start()

    # Pause for the dbus interface to come up
    time.sleep(1)

    yield

    # Stop the bus
    if pid:
        os.kill(pid, signal.SIGTERM)


@pytest.fixture
def widget(monkeypatch):
    """Patch the widget to use the fake dbus service."""

    def force_session_bus(bus_type):
        return get_session_bus_address()

    # Make dbus_next always return the session bus address even if system bus is requested
    monkeypatch.setattr("dbus_next.message_bus.get_bus_address", force_session_bus)

    yield IWD


@pytest.fixture
def iwd_manager(request, widget, dbus_thread, manager_nospawn):
    class IWDConfig(BareConfig):
        screens = [Screen(top=Bar([widget(**getattr(request, "param", dict()))], 20))]

    manager_nospawn.start(IWDConfig)

    yield manager_nospawn


@Retry(ignore_exceptions=(AssertionError,))
def wait_for_text(widget, text):
    assert widget.info()["text"] == text


@Retry(ignore_exceptions=(AssertionError,))
def wait_for_menu(manager, hidden=False):
    windows = len(manager.c.internal_windows())
    if hidden:
        assert windows == 1
    else:
        assert windows == 2


def config(**kwargs):
    return pytest.mark.parametrize("iwd_manager", [kwargs], indirect=True)


def test_defaults(iwd_manager):
    widget = iwd_manager.c.widget["iwd"]
    wait_for_text(widget, "qtile_extras (50%)")


@config(interface="wlan0")
def test_named_interface(iwd_manager):
    widget = iwd_manager.c.widget["iwd"]
    wait_for_text(widget, "qtile_extras (50%)")


@config(interface="wlan1")
# @pytest.mark.flaky(reruns=5)
@pytest.mark.xfail
def test_invalid_interface(iwd_manager, logger):
    widget = iwd_manager.c.widget["iwd"]
    wait_for_text(widget, "Error")
    assert "The interface 'wlan1' was not found." in logger.text


@config(format="{ssid} {rssi} {quality}")
def test_string_format(iwd_manager):
    widget = iwd_manager.c.widget["iwd"]
    wait_for_text(widget, "qtile_extras -75 50")


@config(password_entry_app=None)
# @pytest.mark.flaky(reruns=5)
@pytest.mark.xfail
def test_no_password_entry_app(iwd_manager, logger):
    widget = iwd_manager.c.widget["iwd"]
    wait_for_text(widget, "qtile_extras (50%)")
    assert "No password entry app provided. Agent will not be started." in logger.text


@config(password_entry_app="qtileextraapp")
# @pytest.mark.flaky(reruns=5)
@pytest.mark.xfail
def test_invalid_password_entry_app(iwd_manager, logger):
    widget = iwd_manager.c.widget["iwd"]
    wait_for_text(widget, "qtile_extras (50%)")
    assert "Cannot find password entry app. Agent will not be started." in logger.text


@config(password_entry_args="This should be a list")
@pytest.mark.xfail
def test_bad_password_entry_args(iwd_manager, logger):
    widget = iwd_manager.c.widget["iwd"]
    wait_for_text(widget, "qtile_extras (50%)")
    assert "password_entry_args must be a list. Agent will not be started." in logger.text


def test_menu(iwd_manager):
    widget = iwd_manager.c.widget["iwd"]
    wait_for_text(widget, "qtile_extras (50%)")
    iwd_manager.c.bar["top"].fake_button_press(0, "top", 0, 0, 1)
    wait_for_menu(iwd_manager)

    windows = iwd_manager.c.internal_windows()
    menu = [win for win in windows if win.get("name", "") == "popupmenu"]
    items = menu[0]["controls"]
    assert items[0]["text"] == "Connected to:"
    assert items[1]["text"] == "qtile_extras"
    assert items[-1]["text"] == "Scan for networks"

    networks = set(items[x]["text"] for x in range(3, 6))
    expected = {"Visible networks:", "8021x_network (8021x)", "open_network (open)"}
    assert networks == expected

    widget.eval("self.menu.controls[-1].button_press(0, 0, 1)")
    widget.eval("self.menu.kill()")
    wait_for_menu(iwd_manager, hidden=True)
    iwd_manager.c.bar["top"].fake_button_press(0, "top", 0, 0, 1)
    wait_for_menu(iwd_manager)
    windows = iwd_manager.c.internal_windows()
    menu = [win for win in windows if win.get("name", "") == "popupmenu"]
    items = menu[0]["controls"]
    assert items[-1]["text"] == "Scanning..."


def test_scan_command(iwd_manager):
    widget = iwd_manager.c.widget["iwd"]
    wait_for_text(widget, "qtile_extras (50%)")

    widget.scan()
    iwd_manager.c.bar["top"].fake_button_press(0, "top", 0, 0, 1)
    wait_for_menu(iwd_manager)
    windows = iwd_manager.c.internal_windows()
    menu = [win for win in windows if win.get("name", "") == "popupmenu"]
    items = menu[0]["controls"]
    assert items[-1]["text"] == "Scanning..."
