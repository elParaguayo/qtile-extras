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
from typing import TYPE_CHECKING

from libqtile.widget.statusnotifier import StatusNotifier as QtileStatusNotifier
from libqtile.widget.statusnotifier import StatusNotifierItem, host

from qtile_extras.popup.menu import PopupMenu
from qtile_extras.resources.dbusmenu import DBusMenu

if TYPE_CHECKING:
    from typing import Any, Callable

NO_MENU = "/NO_DBUSMENU"


async def attach_menu(self, display_menu_callback: Callable | None = None):
    # self.display_menu_callback = display_menu_callback
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
        self.menu = DBusMenu(
            self.service, menu_path, self.bus, display_menu_callback=display_menu_callback
        )
        await self.menu.start()


def get_menu(self, root: int = 0):
    if self.menu:
        self.menu.get_menu(root)


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
        if not menu_items:
            return

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
