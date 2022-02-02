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
from __future__ import annotations

import asyncio
import os
import time
from functools import partial
from typing import TYPE_CHECKING

from dbus_next import InterfaceNotFoundError, InvalidIntrospectionError, Variant
from dbus_next.aio import MessageBus
from dbus_next.errors import DBusError
from libqtile.log_utils import logger
from libqtile.widget.statusnotifier import StatusNotifier as QtileStatusNotifier
from libqtile.widget.statusnotifier import StatusNotifierItem, host

from qtile_extras.popup.menu import PopupMenu

if TYPE_CHECKING:
    from typing import Any, Callable


MENU_INTERFACE = "com.canonical.dbusmenu"
NO_MENU = "/NO_DBUSMENU"


class DBusMenuItem:  # noqa: E303
    """Simple class definition to represent a DBus Menu item."""

    def __init__(
        self,
        menu,
        id: int,
        item_type: str = "",
        enabled: bool = True,
        visible: bool = True,
        icon_name: str = "",
        icon_data: list[bytes] = list(),
        shortcut: list[list[str]] = list(),
        label: str = "",
        toggle_type: str = "",
        toggle_state: int = 0,
        children_display: str = "",
    ):
        self.menu = menu
        self.id = id
        self.item_type = item_type
        self.enabled = enabled
        self.visible = visible
        self.icon_name = icon_name
        self.icon_data = icon_data
        self.shortcut = shortcut
        self.toggle_type = toggle_type
        self.toggle_state = toggle_state
        self.children_display = children_display
        self.label = label

    # TODO: Need a method to update properties based on a "PropertiesChanged" event

    def __repr__(self):
        """Custom repr to help debugging."""
        txt = f"'{self.label.replace('_','')}'" if self.label else self.item_type
        if self.children_display == "submenu":
            txt += "*"
        return f"<DBusMenuItem ({self.id}:{txt})>"

    def click(self):
        if self.children_display == "submenu":
            self.menu.parent.get_menu(self.id)
        else:
            asyncio.create_task(self.menu.click(self.id))


class DBusMenu:  # noqa: E303
    """
    Class object to connect DBusMenu interface and and interact with applications.
    """

    MENU_UPDATED = 0
    MENU_USE_STORED = 1
    MENU_NOT_FOUND = 2

    item_key_map = [
        ("type", "item_type"),
        ("icon-name", "icon_name"),
        ("icon-data", "icon_data"),
        ("toggle-state", "toggle_state"),
        ("children-display", "children_display"),
        ("toggle-type", "toggle_type"),
    ]

    def __init__(self, parent, service: str, path: str, bus: MessageBus | None = None):
        self.parent = parent
        self.service = service
        self.path = path
        self.bus = bus
        self._menus: dict[int, dict[str, int | list[DBusMenuItem]]] = {}

    async def start(self):
        """
        Connect to session bus and create object representing menu interface.
        """
        if self.bus is None:
            self.bus = await MessageBus().connect()

        try:
            introspection = await self.bus.introspect(self.service, self.path)

            self._bus_object = self.bus.get_proxy_object(self.service, self.path, introspection)

            self._interface = self._bus_object.get_interface(MENU_INTERFACE)

            # Menus work by giving each menu item an ID and actions are
            # toggled by sending this ID back to the application. These
            # IDs are updated regularly so we subscribe to a signal to make
            # we can keep the menu up to date.
            self._interface.on_layout_updated(self._layout_updated)

            return True

        # Catch errors which indicate a failure to connect to the menu interface.
        except InterfaceNotFoundError:
            logger.warning(f"Cannot find {MENU_INTERFACE} interface at {self.service}")
            return False
        except (DBusError, InvalidIntrospectionError):
            logger.warning(f"Path {self.path} does not present a valid dbusmenu object")
            return False

    def _layout_updated(self, revision, parent):
        """
        Checks whether we have already requested this menu and, if so, check if
        the revision number is less than the updated one.
        The updated menu is not requested at this point as it could be invalidated
        again before it is required.
        """
        if parent in self._menus and self._menus[parent]["revision"] < revision:
            del self._menus[parent]

    async def _get_menu(self, root):
        """
        Method to retrieve the menu layout from the DBus interface.
        """
        # Alert the app that we're about to draw a menu
        # Returns a boolean confirming whether menu should be refreshed
        try:
            needs_update = await self._interface.call_about_to_show(root)
        except DBusError:
            # Catch scenario where menu may be unavailable
            self.menu = None
            return self.MENU_NOT_FOUND, None

        # Check if the menu needs updating or if we've never drawn it before
        if needs_update or root not in self._menus:

            menu = await self._interface.call_get_layout(
                root,  # ParentID
                1,  # Recursion depth
                [],  # Property names (empty = all)
            )

            return self.MENU_UPDATED, menu

        return self.MENU_USE_STORED, None

    # TODO: Probably a better way of dealing with this...
    def _fix_menu_keys(self, item):
        for old, new in self.item_key_map:
            if old in item:
                item[new] = item.pop(old)

        for key in item:
            item[key] = item[key].value

        return item

    def get_menu(self, callback: Callable, root: int = 0):
        """
        Method called by widget to request the menu.
        Callback needs to accept a list of DBusMenuItems.
        """
        task = asyncio.create_task(self._get_menu(root))
        task.add_done_callback(partial(self.parse_menu, root, callback))
        return

    def parse_menu(self, root, callback, task):
        update_needed, returned_menu = task.result()

        if update_needed == self.MENU_UPDATED:

            # Remember the menu revision ID so we know whether to update or not
            revision, layout = returned_menu

            # Menu is array of id, dict confirming there is a submenu
            # (the submenu is the main menu) and the menu items.
            _, _, menuitems = layout

            menu = []

            for item in menuitems:
                # Each item is a list of item ID, dictionary of item properties
                # and a list for submenus
                id, menudict, _ = item.value

                menu_item = DBusMenuItem(self, id, **self._fix_menu_keys(menudict))
                menu.append(menu_item)

            # Store this menu in case we need to draw it again
            self._menus[root] = {"revision": revision, "menu": menu}
        elif update_needed == self.MENU_USE_STORED:
            menu = self._menus[root]["menu"]

        # Send menu to the callback
        callback(menu)

    async def click(self, id):
        """Sends "clicked" event for the given item to the application."""
        await self._interface.call_event(
            id,  # ID of clicked menu item
            "clicked",  # Event type
            Variant("s", ""),  # "Data"
            int(time.time()),  # Timestamp
        )

        # Ugly hack: delete all stored menus if the menu has been clicked
        # This will force a reload when the menu is next generated.
        self._menus = {}


async def attach_menu(self, display_menu_callback: Callable | None = None):
    self.display_menu_callback = display_menu_callback
    self.menu = None

    # Check if the default action for this item should be to show a context menu
    try:
        self.is_context_menu = await self.item.get_item_is_menu()
    except AttributeError:
        self.is_context_menu = False

    # Get the path of the attached menu
    menu_path = await self.item.get_menu()

    # If there is a menu then create and start the menu object
    if menu_path and menu_path != NO_MENU:
        self.menu = DBusMenu(self, self.service, menu_path, self.bus)
        await self.menu.start()


def get_menu(self, root: int = 0):
    if self.menu:
        self.menu.get_menu(self.display_menu_callback, root)


StatusNotifierItem.attach_menu = attach_menu  # type: ignore
StatusNotifierItem.get_menu = get_menu  # type: ignore


class StatusNotifier(QtileStatusNotifier):
    """
    A modified version of the default Qtile StatusNotifier widget.

    Added the ability to render context menus by right-clicking on the
    icon.
    """

    _experimental = True

    defaults = [
        ("menu_font", "sans", "Font for menu text"),
        ("menu_fontsize", 12, "Font size for menu text"),
        ("menu_foreground", "ffffff", "Font colour for menu text"),
        ("menu_background", "333333", "Background colour for menu"),
        ("separator_colour", "555555", "Colour of menu separator"),
        (
            "highlight_colour",
            "0060A0",
            "Colour of highlight for menu items (None for no highlight)",
        ),
        (
            "menu_row_height",
            None,
            (
                "Height of menu row (NB text entries are 2 rows tall, separators are 1 row tall.) "
                '"None" will attempt to calculate height based on font size.'
            ),
        ),
        ("menu_width", 200, "Context menu width"),
        ("show_menu_icons", True, "Show icons in context menu"),
        ("hide_after", 0.5, "Time in seconds before hiding menu atfer mouse leave"),
        ("opacity", 1, "Menu opactity"),
    ]  # type: list[tuple[str, Any, str]]

    _dependencies = ["dbus-next", "xdg"]

    _screenshots = [("statusnotifier.png", "Widget showing Remmina icon and context menu.")]

    def __init__(self, **config):
        QtileStatusNotifier.__init__(self, **config)
        self.add_defaults(StatusNotifier.defaults)
        self.add_callbacks({"Button3": self.show_menu})

        self.menu_config = {
            "background": self.menu_background,
            "font": self.menu_font,
            "fontsize": self.menu_fontsize,
            "foreground": self.menu_foreground,
            "highlight": self.highlight_colour,
            "show_menu_icons": self.show_menu_icons,
            "hide_after": self.hide_after,
            "colour_above": self.separator_colour,
            "opacity": self.opacity,
            "row_height": self.menu_row_height,
            "menu_width": self.menu_width,
        }

        self.session = os.environ.get("DBUS_SESSION_BUS_ADDRESS")
        self.host = host

    def _configure(self, qtile, bar):
        host.display_menu_callback = self.display_menu
        QtileStatusNotifier._configure(self, qtile, bar)

    async def _config_async(self):
        def draw(x=None):
            self.bar.draw()

        def attach_menu(item):
            task = asyncio.create_task(item.attach_menu(display_menu_callback=self.display_menu))
            task.add_done_callback(draw)

        await host.start(on_item_added=attach_menu, on_item_removed=draw, on_icon_changed=draw)

    # TO BE REMOVED ONCE qtile/qtile/pr3060 is merged
    def find_icon_at_pos(self, x, y):
        """returns StatusNotifierItem object for icon in given position"""
        offset = self.padding
        val = x if self.bar.horizontal else y

        if val < offset:
            return None

        for icon in self.available_icons:
            offset += self.icon_size
            if val < offset:
                return icon
            offset += self.padding

        return None

    def show_menu(self):
        if not self.selected_item:
            return
        self.selected_item.get_menu()

    def display_menu(self, menu_items):
        self.menu = PopupMenu.from_dbus_menu(self.qtile, menu_items, **self.menu_config)

        screen = self.bar.screen

        if screen.top == self.bar:
            x = min(self.offsetx, self.bar.width - self.menu.width)
            y = self.bar.height

        elif screen.bottom == self.bar:
            x = min(self.offsetx, self.bar.width - self.menu.width)
            y = screen.height - self.bar.height - self.menu.height

        elif screen.left == self.bar:
            x = self.bar.width
            y = min(self.offsety, screen.height - self.menu.height)

        else:
            x = screen.width - self.bar.width - self.menu.width
            y = min(self.offsety, screen.height - self.menu.height)

        self.menu.show(x, y)
