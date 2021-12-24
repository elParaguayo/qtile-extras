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
import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import pytest

import qtile_extras.widget.network


def get_status(interface):
    if interface == "ERROR":
        raise Exception("Test Error Handling")
    else:
        return ("Test Network", 42)


@pytest.fixture(scope="function")
def wifiicon(monkeypatch):
    monkeypatch.setattr("qtile_extras.widget.network.get_status", get_status)
    yield qtile_extras.widget.network.WiFiIcon


@pytest.fixture(scope="function")
def wifi_manager(wifiicon):
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
                    [wifiicon()],
                    30,
                ),
            )
        ]

    yield WifiConfig


def test_wifiicon(manager_nospawn, wifi_manager):
    manager_nospawn.start(wifi_manager)

    manager_nospawn.c.widget["wifiicon"].eval("self.loop()")

    # Icon width is 60 (wifi_width: 30 + 2x padding_x: 3)
    assert manager_nospawn.c.widget["wifiicon"].info()["width"] == 36

    # Click on widget to show text
    manager_nospawn.c.bar["top"].fake_button_press(0, "top", 0, 0, 1)
    assert manager_nospawn.c.widget["wifiicon"].info()["width"] == 157

    # Hide the text
    manager_nospawn.c.widget["wifiicon"].eval("self.hide()")
    assert manager_nospawn.c.widget["wifiicon"].info()["width"] == 36
