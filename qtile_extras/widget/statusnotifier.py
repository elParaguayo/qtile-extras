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

from libqtile.log_utils import logger
from libqtile.widget.statusnotifier import StatusNotifier as QtileStatusNotifier
from libqtile.widget.statusnotifier import StatusNotifierItem, host

from qtile_extras.popup.menu import PopupMenu
from qtile_extras.resources.dbusmenu import DBusMenu

if TYPE_CHECKING:
    from typing import Any, Callable, Optional

NO_MENU = "/NO_DBUSMENU"


async def attach_menu(self):
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
        self.menu = DBusMenu(self.service, menu_path, self.bus)
        await self.menu.start()


def get_menu(self, root: int = 0, callback: Optional[Callable] = None):
    if self.menu:
        self.menu.get_menu(root, callback=callback)


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
        ("menu_foreground_disabled", "aaaaaa", "Font colour for disabled menu items"),
        (
            "menu_foreground_highlighted",
            None,
            "Font colour for highlighted item (None to use menu_foreground value)",
        ),
        ("menu_background", "333333", "Background colour for menu"),
        ("menu_border", "111111", "Menu border colour"),
        ("menu_border_width", 0, "Width of menu border"),
        ("menu_icon_size", 12, "Size of icons in menu (where available)"),
        ("menu_offset_x", 0, "Fine tune x position of menu"),
        ("menu_offset_y", 0, "Fine tune y position of menu"),
        ("separator_colour", "555555", "Colour of menu separator"),
        (
            "highlight_colour",
            "0060A0",
            "Colour of highlight for menu items (None for no highlight)",
        ),
        ("highlight_radius", 0, "Radius for menu highlight"),
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
            "foreground_disabled": self.menu_foreground_disabled,
            "foreground_highlighted": self.menu_foreground_highlighted,
            "highlight": self.highlight_colour,
            "show_menu_icons": self.show_menu_icons,
            "hide_after": self.hide_after,
            "colour_above": self.separator_colour,
            "opacity": self.opacity,
            "row_height": self.menu_row_height,
            "menu_width": self.menu_width,
            "icon_size": self.menu_icon_size,
            "highlight_radius": self.highlight_radius,
            "border": self.menu_border,
            "border_width": self.menu_border_width,
        }

        self.session = os.environ.get("DBUS_SESSION_BUS_ADDRESS")
        self.host = host
        self.menu = None

    def _configure(self, qtile, bar):
        host.display_menu_callback = self.display_menu
        QtileStatusNotifier._configure(self, qtile, bar)

        if qtile.core.name == "wayland" and self.menu_border_width:
            logger.warning("Menu border is currently unavailable on Wayland.")
            self.menu_config["border_width"] = 0

    async def _config_async(self):
        def draw(x=None):
            self.bar.draw()

        def attach_menu(item):
            task = asyncio.create_task(item.attach_menu())
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
        self.selected_item.get_menu(callback=self.display_menu)

    def display_menu(self, menu_items):
        if not menu_items:
            return

        if self.menu and not self.menu._killed:
            self.menu.kill()

        self.menu = PopupMenu.from_dbus_menu(self.qtile, menu_items, **self.menu_config)

        screen = self.bar.screen

        if screen.top == self.bar:
            x = min(self.offsetx, self.bar.width - self.menu.width - 2 * self.menu_border_width)
            y = self.bar.height

        elif screen.bottom == self.bar:
            x = min(self.offsetx, self.bar.width - self.menu.width - 2 * self.menu_border_width)
            y = screen.height - self.bar.height - self.menu.height - 2 * self.menu_border_width

        elif screen.left == self.bar:
            x = self.bar.width
            y = min(self.offsety, screen.height - self.menu.height - 2 * self.menu_border_width)

        else:
            x = screen.width - self.bar.width - self.menu.width - 2 * self.menu_border_width
            y = min(self.offsety, screen.height - self.menu.height - 2 * self.menu_border_width)

        # Adjust the position for any user-defined settings
        x += self.menu_offset_x
        y += self.menu_offset_y

        self.menu.show(x, y)
