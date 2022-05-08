#!/usr/bin/env python3
"""
This creates a minimal window using GTK that works the same in both X11 or Wayland.

GTK sets the window class via `--name <class>`, and then we manually set the window
title and type. Therefore this is intended to be called as:

    python window.py --name <class> <title> <type>

where <type> is "normal" or "notification"

The window will close itself if it receives any key or button press events.
"""
# flake8: noqa

# This is needed otherwise the window will use any Wayland session it can find even if
# WAYLAND_DISPLAY is not set.
import os

if os.environ.get("WAYLAND_DISPLAY"):
    os.environ["GDK_BACKEND"] = "wayland"
else:
    os.environ["GDK_BACKEND"] = "x11"

# Disable GTK ATK bridge, which appears to trigger errors with e.g. test_strut_handling
# https://wiki.gnome.org/Accessibility/Documentation/GNOME2/Mechanics
os.environ["NO_AT_BRIDGE"] = "1"

import sys
from pathlib import Path

import gi

gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, Gtk

from dbus_next import Message, Variant
from dbus_next.glib import MessageBus
from dbus_next.constants import MessageType, PropertyAccess
from dbus_next.service import ServiceInterface, dbus_property, method, signal


icon_path = Path(__file__).parent / ".." / "resources" / "icons" / "menuitem.png"


class GlobalMenu(ServiceInterface):
    """
    Simplified GlobalMenu interface.
    """

    def __init__(self, window, kill, *args):
        ServiceInterface.__init__(self, *args)
        self.window = window
        self.kill = kill

    @signal()
    def LayoutUpdated(self) -> "ui":
        return [1, 0]

    @method()
    def AboutToShow(self, id: "i") -> "b":
        return True

    @method()
    def GetLayout(self, parent_id: "i", recursion_depth: "i", properties: "as") -> "u(ia{sv}av)":

        if parent_id == 0:
            return [
                1,
                [
                    1,
                    {},
                    [
                        Variant(
                            "(ia{sv}av)",
                            [
                                1,
                                {
                                    "enabled": Variant("b", True),
                                    "visible": Variant("b", True),
                                    "label": Variant("s", "Qtile"),
                                    "children-display": Variant("s", "submenu"),
                                },
                                [],
                            ],
                        ),
                        Variant(
                            "(ia{sv}av)",
                            [
                                2,
                                {
                                    "enabled": Variant("b", True),
                                    "visible": Variant("b", True),
                                    "label": Variant("s", "Test"),
                                },
                                [],
                            ],
                        ),
                    ],
                ],
            ]

        elif parent_id == 1:
            return [
                1,
                [
                    1,
                    {},
                    [
                        Variant(
                            "(ia{sv}av)",
                            [
                                10,
                                {
                                    "enabled": Variant("b", True),
                                    "visible": Variant("b", True),
                                    "label": Variant("s", "Item 1"),
                                },
                                [],
                            ],
                        ),
                        Variant(
                            "(ia{sv}av)",
                            [
                                11,
                                {
                                    "enabled": Variant("b", True),
                                    "visible": Variant("b", True),
                                    "label": Variant("s", "Quit"),
                                },
                                [],
                            ],
                        ),
                    ],
                ],
            ]

    @method()
    def Event(self, id: "i", event_id: "s", data: "v", timestamp: "u"):
        if id == 11:
            self.kill()


class SNIMenu(ServiceInterface):
    """
    Simplified DBusMenu interface.

    Only exports methods, properties and signals required by
    StatusNotifier widget.
    """

    def __init__(self, window, kill, *args):
        ServiceInterface.__init__(self, *args)
        self.window = window
        self.kill = kill

    @signal()
    def LayoutUpdated(self) -> "ui":
        return [1, 0]

    @method()
    def AboutToShow(self, id: "i") -> "b":
        return True

    @method()
    def GetLayout(self, parent_id: "i", recursion_depth: "i", properties: "as") -> "u(ia{sv}av)":
        with open(icon_path.as_posix(), "rb") as icon:
            raw = icon.read()

        return [
            1,
            [
                1,
                {},
                [
                    Variant(
                        "(ia{sv}av)",
                        [
                            0,
                            {
                                "enabled": Variant("b", True),
                                "visible": Variant("b", True),
                                "label": Variant("s", "Test Menu"),
                                "children-display": Variant("s", "submenu"),
                                "icon-data": Variant("ay", bytes(raw)),
                            },
                            [],
                        ],
                    ),
                    Variant(
                        "(ia{sv}av)",
                        [
                            1,
                            {
                                "enabled": Variant("b", True),
                                "visible": Variant("b", True),
                                "label": Variant("s", "Quit"),
                                "icon-data": Variant("s", icon_path.as_posix()),
                            },
                            [],
                        ],
                    ),
                ],
            ],
        ]

    @method()
    def Event(self, id: "i", event_id: "s", data: "v", timestamp: "u"):
        if id == 1:
            self.kill()


class SNItem(ServiceInterface):
    """
    Simplified StatusNotifierItem interface.

    Only exports methods, properties and signals required by
    StatusNotifier widget.
    """

    def __init__(self, window, *args):
        ServiceInterface.__init__(self, *args)
        self.window = window
        self.fullscreen = False

    @method()
    def Activate(self, x: "i", y: "i"):
        if self.fullscreen:
            self.window.unfullscreen()
        else:
            self.window.fullscreen()

        self.fullscreen = not self.fullscreen

    @dbus_property(PropertyAccess.READ)
    def IconName(self) -> "s":
        return ""

    @dbus_property(PropertyAccess.READ)
    def IconPixmap(self) -> "a(iiay)":
        return [[32, 32, bytes([100] * (32 * 32 * 4))]]

    @dbus_property(PropertyAccess.READ)
    def AttentionIconPixmap(self) -> "a(iiay)":
        return []

    @dbus_property(PropertyAccess.READ)
    def OverlayIconPixmap(self) -> "a(iiay)":
        return []

    @dbus_property(PropertyAccess.READ)
    def IsMenu(self) -> "b":
        return False

    @dbus_property(PropertyAccess.READ)
    def Menu(self) -> "s":
        return "/DBusMenu"

    @signal()
    def NewIcon(self):
        pass

    @signal()
    def NewAttentionIcon(self):
        pass

    @signal()
    def NewOverlayIcon(self):
        pass


if __name__ == "__main__":

    # GTK consumes the `--name <class>` args
    if len(sys.argv) > 1:
        title = sys.argv[1]
    else:
        title = "TestWindow"

    if len(sys.argv) > 2:
        window_type = sys.argv[2]
    else:
        window_type = "normal"

    # Check if we want to export a StatusNotifierItem interface
    sni = "export_sni_interface" in sys.argv

    global_menu = "export_global_menu" in sys.argv

    win = Gtk.Window(title=title)
    win.connect("destroy", Gtk.main_quit)
    win.connect("key-press-event", Gtk.main_quit)
    win.set_default_size(100, 100)

    if window_type == "notification":
        if os.environ["GDK_BACKEND"] == "wayland":
            try:
                gi.require_version("GtkLayerShell", "0.1")
                from gi.repository import GtkLayerShell
            except ValueError:
                sys.exit(1)
            win.add(Gtk.Label(label="This is a test notification"))
            GtkLayerShell.init_for_window(win)

        else:
            win.set_type_hint(Gdk.WindowTypeHint.NOTIFICATION)

    elif window_type == "normal":
        win.set_type_hint(Gdk.WindowTypeHint.NORMAL)

    if sni:
        bus = MessageBus().connect_sync()

        item = SNItem(win, "org.kde.StatusNotifierItem")
        menu = SNIMenu(win, Gtk.main_quit, "com.canonical.dbusmenu")

        # Export interfaces on the bus
        bus.export("/StatusNotifierItem", item)
        bus.export("/DBusMenu", menu)

        # Request the service name
        bus.request_name_sync(f"test.qtile.window-{title.replace(' ','-')}")

        msg = bus.call_sync(
            Message(
                message_type=MessageType.METHOD_CALL,
                destination="org.freedesktop.StatusNotifierWatcher",
                interface="org.freedesktop.StatusNotifierWatcher",
                path="/StatusNotifierWatcher",
                member="RegisterStatusNotifierItem",
                signature="s",
                body=[bus.unique_name],
            )
        )

    if global_menu:
        bus = MessageBus().connect_sync()

        menu = GlobalMenu(win, Gtk.main_quit, "com.canonical.dbusmenu")

        # Export interfaces on the bus
        bus.export("/GlobalMenu", menu)

        # Request the service name
        bus.request_name_sync(f"test.qtile.window-global-menu-{title.replace(' ','-')}")

    win.show_all()

    if global_menu:
        wid = win.get_property("window").get_xid()
        msg = bus.call_sync(
            Message(
                message_type=MessageType.METHOD_CALL,
                destination="com.canonical.AppMenu.Registrar",
                interface="com.canonical.AppMenu.Registrar",
                path="/com/canonical/AppMenu/Registrar",
                member="RegisterWindow",
                signature="uo",
                body=[wid, "/GlobalMenu"],
            )
        )

    Gtk.main()
