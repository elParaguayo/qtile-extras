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
import time
from functools import partial
from typing import TYPE_CHECKING

from dbus_next import InterfaceNotFoundError, InvalidIntrospectionError, Variant
from dbus_next.aio import MessageBus
from dbus_next.errors import DBusError
from libqtile.log_utils import logger

from qtile_extras.resources.dbusmenu.dbusmenu import DBUS_MENU_SPEC

if TYPE_CHECKING:
    from typing import Callable


MENU_INTERFACE = "com.canonical.dbusmenu"


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
        show_menu_callback: Callable | None = None,
        **kwargs,
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
        self.show_menu_callback = show_menu_callback

    # TODO: Need a method to update properties based on a "PropertiesChanged" event

    def __repr__(self):
        """Custom repr to help debugging."""
        txt = f"'{self.label.replace('_', '')}'" if self.label else self.item_type
        if self.children_display == "submenu":
            txt += "*"
        return f"<DBusMenuItem ({self.id}:{txt})>"

    def click(self):
        if self.children_display == "submenu":
            self.menu.get_menu(self.id, self.show_menu_callback)
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

    def __init__(
        self,
        service: str,
        path: str,
        bus: MessageBus | None = None,
        no_cache_menus: bool = False,
        layout_callback: Callable | None = None,
        display_menu_callback: Callable | None = None,
    ):
        self.service = service
        self.path = path
        self.bus = bus
        self._menus: dict[int, dict[str, int | list[DBusMenuItem]]] = {}
        self._interface = None
        self.no_cache_menus = no_cache_menus
        self.layout_callbacks = []
        self.display_menu_callback = display_menu_callback
        if layout_callback is not None:
            self.layout_callbacks.append(layout_callback)

    async def start(self):
        """
        Connect to session bus and create object representing menu interface.
        """
        if self.bus is None:
            self.bus = await MessageBus().connect()

        try:
            introspection = await self.bus.introspect(self.service, self.path)

            obj = self.bus.get_proxy_object(self.service, self.path, introspection)

            self._interface = obj.get_interface(MENU_INTERFACE)

        # Catch errors which indicate a failure to connect to the menu interface.
        except InterfaceNotFoundError:
            logger.info(
                "Cannot find %s interface at %s. Falling back to default spec.",
                MENU_INTERFACE,
                self.service,
            )
            try:
                obj = self.bus.get_proxy_object(self.service, self.path, DBUS_MENU_SPEC)
                self._interface = obj.get_interface(MENU_INTERFACE)
            except InterfaceNotFoundError:
                logger.warning(
                    "Could not find %s interface at %s and unable to use default spec.",
                    MENU_INTERFACE,
                    self.service,
                )
                return False
        except (DBusError, InvalidIntrospectionError):
            logger.warning("Path %s does not present a valid dbusmenu object", self.path)
            return False

        # Menus work by giving each menu item an ID and actions are
        # toggled by sending this ID back to the application. These
        # IDs are updated regularly so we subscribe to a signal to make
        # we can keep the menu up to date.
        self._interface.on_layout_updated(self._layout_updated)

        return True

    def _layout_updated(self, revision, parent):
        """
        Checks whether we have already requested this menu and, if so, check if
        the revision number is less than the updated one.
        The updated menu is not requested at this point as it could be invalidated
        again before it is required.
        """
        if parent in self._menus and self._menus[parent]["revision"] < revision:
            del self._menus[parent]

        for callback in self.layout_callbacks:
            callback(self)

    async def _get_menu(self, root):
        """
        Method to retrieve the menu layout from the DBus interface.
        """

        if self._interface is None:
            return None, None

        needs_update = True

        # Alert the app that we're about to draw a menu
        # Returns a boolean confirming whether menu should be refreshed
        try:
            needs_update = await self._interface.call_about_to_show(root)
        except (DBusError, AttributeError):
            pass

        # Check if the menu needs updating or if we've never drawn it before
        if needs_update or self.no_cache_menus or root not in self._menus:
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

    def get_menu(self, root: int = 0, callback: Callable | None = None):
        """
        Method called by widget to request the menu.
        Callback needs to accept a list of DBusMenuItems.
        """
        if self.display_menu_callback is None and callback is None:
            logger.warning("Missing callback for displaying menu.")
            return

        func = callback if callback is not None else self.display_menu_callback

        task = asyncio.create_task(self._get_menu(root))
        task.add_done_callback(partial(self.parse_menu, root, func))
        return

    def parse_menu(self, root, callback, task):
        update_needed, returned_menu = task.result()
        menu = []

        if update_needed is None:
            return

        elif update_needed == self.MENU_UPDATED:
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

                menu_item = DBusMenuItem(
                    self, id, **self._fix_menu_keys(menudict), show_menu_callback=callback
                )
                menu.append(menu_item)

            # Store this menu in case we need to draw it again
            self._menus[root] = {"revision": revision, "menu": menu}
        elif update_needed == self.MENU_USE_STORED:
            menu = self._menus[root]["menu"]

        # Send menu to the callback
        callback(menu)

    async def click(self, id):
        """Sends "clicked" event for the given item to the application."""
        try:
            await self._interface.call_about_to_show(id)
        except DBusError:
            pass

        try:
            await self._interface.call_event(
                id,  # ID of clicked menu item
                "clicked",  # Event type
                Variant("s", ""),  # "Data"
                int(time.time()),  # Timestamp
            )
        except DBusError:
            logger.warning("Unable to send click event on StatusNotifier menu.")

        # Ugly hack: delete all stored menus if the menu has been clicked
        # This will force a reload when the menu is next generated.
        self._menus = {}

    def stop(self):
        self._interface.off_layout_updated(self._layout_updated)
