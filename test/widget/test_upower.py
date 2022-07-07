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
import os
import shutil
import subprocess

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import pytest
from dbus_next.constants import BusType

from qtile_extras.widget.upower import UPowerWidget
from test.helpers import Retry  # noqa: I001


@Retry(ignore_exceptions=(AssertionError,))
def battery_found(manager):
    """Waits for widget to report batteries."""
    _, output = manager.c.widget["upowerwidget"].eval("len(self.batteries)")
    while int(output) == 0:
        # If there are no batteries (shouldn't happen) try looking again.
        manager.c.widget["upowerwidget"].eval(
            "import asyncio;asyncio.create_task(self._find_batteries())"
        )
        assert False
    assert True


@Retry(ignore_exceptions=(AssertionError,))
def text_hidden(manager, target):
    """Waits for widget to hide text."""
    assert manager.c.widget["upowerwidget"].info()["width"] == target


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
                    [powerwidget(**getattr(request, "param", dict()))],
                    50,
                ),
            )
        ]

    yield PowerConfig


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
@pytest.mark.parametrize(
    "powerconfig", [{"battery_name": "BAT1", "percentage_low": 0.6}], indirect=True
)
def test_upower_low_battery(manager_nospawn, powerconfig):
    manager_nospawn.start(powerconfig)
    battery_found(manager_nospawn)
    assert len(manager_nospawn.c.widget["upowerwidget"].info()["batteries"]) == 1
    assert manager_nospawn.c.widget["upowerwidget"].info()["batteries"][0]["status"] == "Low"


@upower_dbus_servive
@pytest.mark.parametrize(
    "powerconfig",
    [{"battery_name": "BAT1", "percentage_low": 0.7, "percentage_critical": 0.55}],
    indirect=True,
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
    subprocess.run(
        [
            dbussend,
            f"--bus={os.environ['DBUS_SESSION_BUS_ADDRESS']}",
            "--type=method_call",
            "--dest=test.qtileextras.upower",
            "/org/freedesktop/UPower",
            "org.freedesktop.UPower.toggle_charge",
        ]
    )

    assert manager_nospawn.c.widget["upowerwidget"].info()["charging"]
    assert manager_nospawn.c.widget["upowerwidget"].info()["batteries"][0]["ttf"] == "1:03"
    assert not manager_nospawn.c.widget["upowerwidget"].info()["batteries"][0]["tte"]


@upower_dbus_servive
@pytest.mark.parametrize(
    "powerconfig",
    [{"battery_name": "BAT1", "text_displaytime": 0.5, "fontsize": None}],
    indirect=True,
)
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
    subprocess.run(
        [
            dbussend,
            f"--bus={os.environ['DBUS_SESSION_BUS_ADDRESS']}",
            "--type=method_call",
            "--dest=test.qtileextras.upower",
            "/org/freedesktop/UPower",
            "org.freedesktop.UPower.toggle_charge",
        ]
    )

    # Click on widget shows text so it should be wider now
    manager_nospawn.c.bar["top"].fake_button_press(0, "top", 0, 0, 1)
    assert manager_nospawn.c.widget["upowerwidget"].info()["width"] != orig_width

    # Let the timer hide the text
    text_hidden(manager_nospawn, orig_width)


def test_upower_deprecated_font_colour(caplog):
    widget = UPowerWidget(font_colour="ffffff")

    assert caplog.record_tuples[0] == (
        "libqtile",
        logging.WARNING,
        "The use of `font_colour` is deprecated. "
        "Please update your config to use `foreground` instead.",
    )

    assert widget.foreground == "ffffff"
