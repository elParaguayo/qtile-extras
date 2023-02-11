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
import tempfile

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import pytest
from dbus_next import Message, Variant
from dbus_next.aio import MessageBus
from dbus_next.constants import MessageType
from libqtile.log_utils import init_log

import qtile_extras.widget.brightnesscontrol
from test.helpers import Retry  # noqa: I001

upower_dbus_service = pytest.mark.usefixtures("dbus_thread")


async def patched_signal_receiver(callback, **kwargs):
    """Add signal receiver on bus created by test."""
    bus = await MessageBus(bus_address=os.environ["DBUS_SESSION_BUS_ADDRESS"]).connect()

    msg = await bus.call(
        Message(
            message_type=MessageType.METHOD_CALL,
            destination="org.freedesktop.DBus",
            interface="org.freedesktop.DBus",
            path="/org/freedesktop/DBus",
            member="AddMatch",
            signature="s",
            body=["type='signal',path='/org/freedesktop/UPower'"],
        )
    )

    if msg.message_type == MessageType.METHOD_RETURN:
        bus.add_message_handler(callback)
        return True

    assert False


@Retry(ignore_exceptions=(AssertionError,))
def widget_hidden(widget):
    """Waits for widget to hide text."""
    assert widget.info()["width"] == 0


@pytest.fixture(scope="function")
def brightdevice():
    with tempfile.TemporaryDirectory() as brightnessdir:
        with open(os.path.join(brightnessdir, "brightness"), "w") as b:
            b.write(str(600))

        with open(os.path.join(brightnessdir, "max_brightness"), "w") as w:
            w.write(str(1000))

        yield brightnessdir


@pytest.fixture(scope="function")
def bright_manager(request, manager_nospawn, brightdevice, monkeypatch):
    """
    Fixture provides a manager instance but needs to be configured with
    tuple that will initiate a datetime object to be parsed for
    datetime.now.
    """
    monkeypatch.setattr(
        "qtile_extras.widget.brightnesscontrol.add_signal_receiver", patched_signal_receiver
    )

    class BrightConfig(libqtile.confreader.Config):
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
                    [
                        qtile_extras.widget.brightnesscontrol.BrightnessControl(
                            device=brightdevice, **getattr(request, "param", dict())
                        )
                    ],
                    50,
                ),
            )
        ]

    manager_nospawn.start(BrightConfig)
    yield manager_nospawn


def test_brightness_defaults(bright_manager):
    """Check widget values behave as expected."""
    widget = bright_manager.c.widget["brightnesscontrol"]

    info = widget.info()
    assert info["brightness"] == 600
    assert info["max_brightness"] == 1000
    assert info["min_brightness"] == 100

    widget.brightness_up()
    info = widget.info()
    assert info["brightness"] == 650

    for _ in range(10):
        widget.brightness_up()

    info = widget.info()
    assert info["brightness"] == info["max_brightness"]

    for _ in range(20):
        widget.brightness_down()

    info = widget.info()
    assert info["brightness"] == info["min_brightness"]

    widget.set_brightness_value(610)
    info = widget.info()
    assert info["brightness"] == 610

    widget.set_brightness_percent(0.45)
    info = widget.info()
    assert info["brightness"] == 450


@pytest.mark.parametrize(
    "bright_manager", [{"max_brightness": 800, "min_brightness": 200}], indirect=True
)
def test_brightness_limits(bright_manager):
    """Check brightness is limited to defined values."""
    widget = bright_manager.c.widget["brightnesscontrol"]

    info = widget.info()
    assert info["brightness"] == 600
    assert info["max_brightness"] == 800
    assert info["min_brightness"] == 200

    for _ in range(10):
        widget.brightness_up()

    info = widget.info()
    assert info["brightness"] == info["max_brightness"]

    for _ in range(20):
        widget.brightness_down()

    info = widget.info()
    assert info["brightness"] == info["min_brightness"]


@pytest.mark.parametrize("bright_manager", [{"max_brightness": 1200}], indirect=True)
def test_brightness_restrict_max_brightness(bright_manager):
    """Check max brightness is limited to defined value if higher than system limit."""
    widget = bright_manager.c.widget["brightnesscontrol"]

    info = widget.info()
    assert info["brightness"] == 600
    assert info["max_brightness"] == 1000

    for _ in range(10):
        widget.brightness_up()

    info = widget.info()
    assert info["brightness"] == info["max_brightness"]


@pytest.mark.parametrize(
    "bright_manager", [{"max_brightness": 800, "max_brightness_path": None}], indirect=True
)
def test_brightness_restrict_no_max_brightness_path(bright_manager):
    """Check max brightness is limited to defined value when no system value."""
    widget = bright_manager.c.widget["brightnesscontrol"]

    info = widget.info()
    assert info["brightness"] == 600
    assert info["max_brightness"] == 800

    for _ in range(10):
        widget.brightness_up()

    info = widget.info()
    assert info["brightness"] == info["max_brightness"]


@pytest.mark.parametrize(
    "bright_manager", [{"max_brightness": None, "max_brightness_path": None}], indirect=True
)
def test_brightness_restrict_no_max_brightness_default(bright_manager):
    """Check max brightness is set to default when no defined values."""
    widget = bright_manager.c.widget["brightnesscontrol"]

    info = widget.info()
    assert info["brightness"] == 600
    assert info["max_brightness"] == 500

    for _ in range(10):
        widget.brightness_up()

    info = widget.info()
    assert info["brightness"] == info["max_brightness"]


@upower_dbus_service
@pytest.mark.parametrize(
    "bright_manager", [{"enable_power_saving": True, "brightness_on_battery": 450}], indirect=True
)
def test_brightness_power_saving(bright_manager):
    """Check widget responds to power events."""

    def toggle_power():
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

    widget = bright_manager.c.widget["brightnesscontrol"]

    info = widget.info()
    assert info["brightness"] == 600
    assert info["max_brightness"] == 1000
    assert info["min_brightness"] == 100

    # First toggle puts device on battery power
    # Brightness should change to 450
    toggle_power()
    info = widget.info()
    assert info["brightness"] == 450

    # Second toggle puts device on mains power
    # Brightness should change to 100%
    toggle_power()
    info = widget.info()
    assert info["brightness"] == 1000


def test_brightness_logging_no_max(caplog):
    init_log(logging.INFO)
    with tempfile.TemporaryDirectory() as tempdir:
        with open(os.path.join(tempdir, "brightness"), "w") as f:
            f.write(str(500))

        _ = qtile_extras.widget.BrightnessControl(
            max_brightness_path=None, max_brightness=None, device=tempdir
        )

    assert caplog.record_tuples == [
        (
            "libqtile",
            logging.WARNING,
            "No maximum brightness defined. "
            "Setting to default value of 500. "
            "The script may behave unexpectedly.",
        )
    ]


def test_brightness_logging_power_saving(caplog):
    """Test log messages for power saving levels."""
    init_log(logging.INFO)
    with tempfile.TemporaryDirectory() as tempdir:
        with open(os.path.join(tempdir, "brightness"), "w") as f:
            f.write(str(500))

        widget = qtile_extras.widget.BrightnessControl(
            max_brightness_path=None,
            max_brightness=100,
            brightness_on_battery="100",
            brightness_on_mains="ten%",
            device=tempdir,
        )

    # No log here as we're not tracking this property
    widget.update(0, {"DifferentProperty": Variant("b", True)}, 0)
    assert caplog.record_tuples == []

    # on_battery value is a string
    widget.update(0, {"OnBattery": Variant("b", True)}, 0)
    assert caplog.record_tuples == [
        ("libqtile", logging.WARNING, "Unrecognised value for brightness: 100")
    ]

    caplog.clear()

    # on_mains value is a string ending in % but can't be parsed
    widget.update(0, {"OnBattery": Variant("b", False)}, 0)

    assert caplog.record_tuples == [
        ("libqtile", logging.ERROR, "Incorrectly formatted brightness: ten%")
    ]


def test_brightness_logging_invalid_file(caplog):
    """Test log messages when no brightness device."""
    path = "/non_existent/file"

    init_log(logging.INFO)

    widget = qtile_extras.widget.BrightnessControl(
        max_brightness_path=None, max_brightness=100, device=path
    )

    # Will fail to read device during init
    assert caplog.record_tuples == [
        (
            "libqtile",
            logging.ERROR,
            f"Unexpected error when reading {path}/brightness: "
            f"[Errno 2] No such file or directory: '{path}/brightness'.",
        ),
        (
            "libqtile",
            logging.WARNING,
            "Current value was not read. Module may behave unexpectedly.",
        ),
    ]

    caplog.clear()

    # Will also fail when trying to write
    # Need to catch AttributeError as self.bar.draw will fail
    with pytest.raises(AttributeError):
        widget.update(0, {"OnBattery": Variant("b", True)}, 0)

    assert caplog.record_tuples == [
        (
            "libqtile",
            logging.ERROR,
            f"Unexpected error when writing brightness value: "
            f"[Errno 2] No such file or directory: '{path}/brightness'.",
        )
    ]


def test_brightness_logging_invalid_value(caplog):
    """Test log messages for invalid brightness value"""
    init_log(logging.INFO)
    with tempfile.TemporaryDirectory() as tempdir:
        with open(os.path.join(tempdir, "brightness"), "w") as f:
            f.write("INVALID")

        _ = qtile_extras.widget.BrightnessControl(
            max_brightness_path=None, max_brightness=1000, device=tempdir
        )

    assert caplog.record_tuples == [
        ("libqtile", logging.ERROR, f"Unexpected value when reading {tempdir}/brightness."),
        (
            "libqtile",
            logging.WARNING,
            "Current value was not read. Module may behave unexpectedly.",
        ),
    ]


@pytest.mark.parametrize("bright_manager", [{"timeout_interval": 0.5}], indirect=True)
def test_brightness_hide_bar(bright_manager):
    """Check max brightness is set to default when no defined values."""
    widget = bright_manager.c.widget["brightnesscontrol"]
    assert widget.info()["width"] == 0

    widget.brightness_up()
    assert widget.info()["width"] == 75

    widget_hidden(widget)


def test_brightness_deprecated_font_colour(caplog):
    with tempfile.TemporaryDirectory() as tempdir:
        with open(os.path.join(tempdir, "brightness"), "w") as f:
            f.write(str(500))

        widget = qtile_extras.widget.BrightnessControl(font_colour="ffffff")

    assert caplog.record_tuples[0] == (
        "libqtile",
        logging.WARNING,
        "The use of `font_colour` is deprecated. "
        "Please update your config to use `foreground` instead.",
    )

    assert widget.foreground == "ffffff"
