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

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import pytest

from test.helpers import Retry

try:
    import qtile_extras.widget.network
except ImportError as e:
    if "iwlib" in str(e):
        pytest.skip("No iwlib installed", allow_module_level=True)
    else:
        raise e


def get_status(interface):
    if interface == "ERROR":
        raise Exception("Test Error Handling")
    else:
        return ("Test Network", 42)


@Retry(ignore_exceptions=(AssertionError,))
def assert_connected(widget, state):
    _, connected = widget.eval("self.is_connected")
    assert connected == state


@pytest.fixture(scope="function")
def wifiicon(monkeypatch):
    monkeypatch.setattr("qtile_extras.widget.network.get_status", get_status)
    yield qtile_extras.widget.network.WiFiIcon


@pytest.fixture(scope="function")
def wifi_manager(wifiicon, request, manager_nospawn):
    class WifiConfig(libqtile.confreader.Config):
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
                    [wifiicon(**getattr(request, "param", dict()))],
                    30,
                ),
            )
        ]

    manager_nospawn.start(WifiConfig)
    yield manager_nospawn


def test_wifiicon(wifi_manager):
    wifi_manager.c.widget["wifiicon"].eval("self.loop()")

    # Icon width is 60 (wifi_width: 30 + 2x padding_x: 3)
    assert wifi_manager.c.widget["wifiicon"].info()["width"] == 36

    # Click on widget to show text - width should be bigger now
    wifi_manager.c.bar["top"].fake_button_press(0, "top", 0, 0, 1)
    assert wifi_manager.c.widget["wifiicon"].info()["width"] > 36

    # Hide the text
    wifi_manager.c.widget["wifiicon"].eval("self.hide()")
    assert wifi_manager.c.widget["wifiicon"].info()["width"] == 36

    # Call exposed command to toggle text
    wifi_manager.c.widget["wifiicon"].show_text()
    assert wifi_manager.c.widget["wifiicon"].info()["width"] > 36


def test_wifiicon_deprecated_font_colour(caplog):
    widget = qtile_extras.widget.network.WiFiIcon(font_colour="ffffff")

    assert caplog.record_tuples[0] == (
        "libqtile",
        logging.WARNING,
        "The use of `font_colour` is deprecated. "
        "Please update your config to use `foreground` instead.",
    )

    assert widget.foreground == "ffffff"


@pytest.mark.parametrize(
    "wifi_manager,expected",
    [
        ({"check_connection_interval": 1}, "True"),
        (
            {
                "check_connection_interval": 1,
                "internet_check_timeout": 1,
                "internet_check_host": "192.168.192.168",
            },
            "False",
        ),
    ],
    indirect=["wifi_manager"],
)
def test_wifiicon_internet_check(wifi_manager, expected):
    widget = wifi_manager.c.widget["wifiicon"]

    widget.eval("self.is_connected = None")

    assert_connected(widget, expected)
