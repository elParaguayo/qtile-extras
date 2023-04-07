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
import logging

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import pytest
from dbus_next.errors import InterfaceNotFoundError, InvalidIntrospectionError
from libqtile.log_utils import init_log

import qtile_extras.resources.dbusmenu
import qtile_extras.widget
from qtile_extras.resources.dbusmenu import DBusMenuItem
from test.helpers import Retry  # noqa: I001


@Retry(ignore_exceptions=(AssertionError,))
def wait_for_icon(widget, hidden=True, prop="width"):
    width = widget.info()[prop]
    if hidden:
        assert width == 0
    else:
        assert width > 0


@Retry(ignore_exceptions=(AssertionError,))
def wait_for_menu(manager, hidden=True):
    windows = len(manager.c.internal_windows())
    if hidden:
        assert windows == 1
    else:
        assert windows == 2


@Retry(ignore_exceptions=(AssertionError,))
def check_fullscreen(windows, fullscreen=True):
    full = windows()[0]["fullscreen"]
    assert full is fullscreen


@pytest.fixture(scope="function")
def sni_config(request, manager_nospawn):
    """
    Fixture provides a manager instance with StatusNotifier in the bar.

    Widget can be customised via parameterize.
    """

    class SNIConfig(libqtile.confreader.Config):
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
                    [qtile_extras.widget.StatusNotifier(**getattr(request, "param", dict()))],
                    50,
                ),
            )
        ]

    yield SNIConfig


@pytest.mark.usefixtures("dbus")
def test_statusnotifier_menu(manager_nospawn, sni_config):
    """Check `activate` method when left-clicking widget."""
    manager_nospawn.start(sni_config)
    widget = manager_nospawn.c.widget["statusnotifier"]

    group = manager_nospawn.c.group
    assert widget.info()["width"] == 0

    # Load test window and icon should appear
    manager_nospawn.test_window("TestSNIMenu", export_sni=True)
    wait_for_icon(widget, hidden=False)

    assert len(manager_nospawn.c.windows()) == 1

    manager_nospawn.c.bar["top"].fake_button_press(0, "top", 10, 0, 3)
    wait_for_menu(manager_nospawn, hidden=False)

    menu = [x for x in manager_nospawn.c.internal_windows() if x.get("name", "") == "popupmenu"][
        0
    ]
    assert menu
    assert menu["controls"]

    # Hacky way to press menu item. Last item is "Quit"
    widget.eval("self.menu.controls[-1].button_press(0, 0, 1)")
    wait_for_icon(widget, hidden=True)
    assert len(group.info()["windows"]) == 0


@pytest.mark.parametrize(
    "position, coords",
    [("top", (0, 50)), ("bottom", (0, 502)), ("left", (50, 0)), ("right", (548, 0))],
)
@pytest.mark.usefixtures("dbus")
def test_statusnotifier_menu_positions(
    manager_nospawn, sni_config, position, coords, backend_name
):
    """Check menu positioning."""
    screen = libqtile.config.Screen(
        **{position: libqtile.bar.Bar([qtile_extras.widget.StatusNotifier()], 50)}
    )

    sni_config.screens = [screen]
    manager_nospawn.start(sni_config)
    widget = manager_nospawn.c.widget["statusnotifier"]

    # Launch window and wait for icon to appear
    try:
        manager_nospawn.test_window("TestSNIMenuPosition", export_sni=True)
        prop = {"prop": "height"} if position in ["left", "right"] else {}
        wait_for_icon(widget, hidden=False, **prop)

        # Click the button (hacky way of doing it)
        widget.eval("self.selected_item = self.available_icons[0];self.show_menu()")
        wait_for_menu(manager_nospawn, hidden=False)
    except AssertionError:
        pytest.xfail("This test is flaky so we allow failures for now.")

    # Get menu and check menu positioning is adjusted
    menu = [x for x in manager_nospawn.c.internal_windows() if x.get("name", "") == "popupmenu"][
        0
    ]
    assert (menu["x"], menu["y"]) == coords


def test_statusnotifier_dbusmenuitem_repr():
    """Usefulf for debugging dbus menus."""
    item1 = DBusMenuItem("", 0, label="Test item1", children_display="submenu")
    item2 = DBusMenuItem("", 1, label="Test item2")

    assert repr(item1) == "<DBusMenuItem (0:'Test item1'*)>"
    assert repr(item2) == "<DBusMenuItem (1:'Test item2')>"


@pytest.mark.asyncio
async def test_statusnotifier_dbusmenu_errors(monkeypatch, caplog):
    init_log(logging.INFO)

    class MockBus:
        error = InterfaceNotFoundError()

        async def connect(self):
            class Bus:
                async def introspect(self, *args, **kwargs):
                    raise MockBus.error

                def get_proxy_object(self, service, path, introspection):
                    raise MockBus.error

            return Bus()

    monkeypatch.setattr("qtile_extras.resources.dbusmenu.MessageBus", MockBus)

    menu = qtile_extras.resources.dbusmenu.DBusMenu("test.qtile_extras.menu", "/DBusMenu")

    started = await menu.start()

    assert not started
    assert caplog.record_tuples == [
        (
            "libqtile",
            logging.INFO,
            "Cannot find com.canonical.dbusmenu interface at test.qtile_extras.menu. Falling back to default spec.",
        ),
        (
            "libqtile",
            logging.WARNING,
            "Could not find com.canonical.dbusmenu interface at test.qtile_extras.menu and unable to use default spec.",
        ),
    ]

    caplog.clear()

    MockBus.error = InvalidIntrospectionError()

    started = await menu.start()

    assert not started
    assert caplog.record_tuples == [
        ("libqtile", logging.WARNING, "Path /DBusMenu does not present a valid dbusmenu object")
    ]
