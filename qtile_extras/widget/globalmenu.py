# Copyright (c) 2022 elParaguayo
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
from typing import TYPE_CHECKING

from libqtile import hook
from libqtile.widget import base

from qtile_extras.popup.menu import PopupMenu
from qtile_extras.resources.dbusmenu import DBusMenu
from qtile_extras.resources.global_menu import registrar

if TYPE_CHECKING:
    from typing import Any


class GlobalMenu(base._TextBox):
    """
    A widget to display a Global Menu (File Edit etc.) in your bar.

    Only works with apps that export their menu via DBus.

    This is not currently available on Wayland backends but I may try to see
    if I can get it working at some point!
    """

    orientations = base.ORIENTATION_HORIZONTAL

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
        ("padding", 3, "Padding between items in menu bar"),
    ]  # type: list[tuple[str, Any, str]]

    _dependencies = ["dbus-next"]

    _screenshots = [("globalmenu.png", "Showing VLC menu in the bar.")]

    supported_backends = {"x11"}

    def __init__(self, **config):
        base._TextBox.__init__(self, **config)
        self.add_defaults(GlobalMenu.defaults)
        self.root = None
        self.items = []
        self.app_menus = {}
        self.main_menu = None
        self.current_wid = None
        self.add_callbacks({"Button1": self.show_menu})
        self.menu = None
        self.item_pos = 0

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

    async def _config_async(self):
        if not registrar.started:
            await registrar.start()

        registrar.add_callback(self.client_updated)
        self.set_hooks()
        self.hook_response(startup=True)

    def client_updated(self, wid):
        if wid in self.app_menus:
            del self.app_menus[wid]

        if wid == self.current_wid:
            asyncio.create_task(self.get_window_menu(wid))

    def set_hooks(self):
        hook.subscribe.focus_change(self.hook_response)
        hook.subscribe.client_killed(self.client_killed)

    def hook_response(self, *args, startup=False):
        if not startup and self.bar.screen != self.qtile.current_screen:
            self.items = []
            self.bar.draw()
            return

        self.current_wid = self.qtile.current_window.wid if self.qtile.current_window else None
        if self.current_wid and self.current_wid in registrar.windows:
            asyncio.create_task(self.get_window_menu(self.current_wid))
        elif not startup:
            self.items = []
            self.bar.draw()

    def client_killed(self, client):
        wid = client.wid
        if wid in self.app_menus:
            registrar.window_closed(client.wid)
            del self.app_menus[wid]

    async def get_window_menu(self, wid):
        service, path = registrar.get_menu(wid)
        menu = self.app_menus.get(wid)
        if not menu:
            menu = DBusMenu(
                service,
                path,
                no_cache_menus=True,
                layout_callback=self.layout_updated,
                display_menu_callback=self.display_menu,
            )
            await menu.start()
            self.app_menus[wid] = menu

        self.main_menu = menu
        self.main_menu.get_menu(callback=self.parse_root_menu)

    def layout_updated(self, menu: DBusMenu):
        if menu is self.main_menu:
            self.main_menu.get_menu(callback=self.parse_root_menu)

    def parse_root_menu(self, menu):
        self.root = menu
        self.items = []
        for item in menu:
            layout = self.drawer.textlayout(
                item.label.replace("_", ""),
                self.foreground,
                self.font,
                self.fontsize,
                self.fontshadow,
                markup=self.markup,
            )
            self.items.append(layout)

        self.bar.draw()

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)
        padding = self.padding if self.padding is not None else 0
        offset = padding
        for item in self.items:
            item.draw(offset, int(self.bar.height / 2.0 - self.layout.height / 2.0) + 1)
            offset += item.width + padding

        self.drawer.draw(offsetx=self.offsetx, offsety=self.offsety, width=self.width)

    def calculate_length(self):
        if not self.items:
            return 0

        if self.padding is not None:
            total_padding = self.padding * (len(self.items) + 1)
        else:
            total_padding = 0

        return sum(item.width for item in self.items) + total_padding

    def find_text_at_pos(self, x, y):
        """Returns menu ID for clicked text."""
        offset = self.padding
        val = x if self.bar.horizontal else y

        if val < offset:
            return None

        for item in self.items:
            offset += item.width
            if val < offset:
                index = self.items.index(item)
                self.item_pos = offset - item.width - self.padding // 2
                return self.root[index]
            offset += self.padding

        return None

    def button_press(self, x, y, button):
        self.selected_item = self.find_text_at_pos(x, y)

        name = "Button{0}".format(button)
        if name in self.mouse_callbacks:
            self.mouse_callbacks[name]()

    def show_menu(self):
        if not self.selected_item or not self.main_menu:
            return
        self.main_menu.get_menu(root=self.selected_item.id)

    def display_menu(self, menu_items):
        if not menu_items:
            return

        if self.menu is not None:
            self.menu.kill()

        self.menu = PopupMenu.from_dbus_menu(self.qtile, menu_items, **self.menu_config)

        if self.bar.screen.top == self.bar:
            x = min(self.offsetx + self.item_pos, self.bar.width - self.menu.width)
            y = self.bar.height

        else:
            x = min(self.offsetx + self.item_pos, self.bar.width - self.menu.width)
            y = self.bar.screen.height - self.bar.height - self.menu.height

        # Adjust the position by the screen's offset
        x += self.bar.screen.x
        y += self.bar.screen.y

        self.menu.show(x, y)

    def finalize(self):
        registrar.remove_callback(self.client_updated)
        registrar.finalize()
        for item in self.items:
            item.finalize()
        base._TextBox.finalize(self)
