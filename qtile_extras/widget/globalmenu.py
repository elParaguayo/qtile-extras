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

from typing import TYPE_CHECKING

from libqtile import hook
from libqtile.backend.base.window import Internal
from libqtile.utils import create_task
from libqtile.widget import base

from qtile_extras.resources.dbusmenu import DBusMenu
from qtile_extras.resources.global_menu import registrar
from qtile_extras.widget.mixins import DbusMenuMixin

if TYPE_CHECKING:
    from typing import Any  # noqa: F401


class GlobalMenu(base._TextBox, DbusMenuMixin):
    """
    A widget to display a Global Menu (File Edit etc.) in your bar.

    Only works with apps that export their menu via DBus.

    Wayland support is "experimental" at best. Expect unexpected behaviour!
    """

    orientations = base.ORIENTATION_HORIZONTAL

    _experimental = True

    defaults = [
        ("padding", 3, "Padding between items in menu bar"),
    ]  # type: list[tuple[str, Any, str]]

    _dependencies = ["dbus-next"]

    _screenshots = [("globalmenu.png", "Showing VLC menu in the bar.")]

    def __init__(self, **config):
        base._TextBox.__init__(self, **config)
        self.add_defaults(DbusMenuMixin.defaults)
        self.add_defaults(GlobalMenu.defaults)
        DbusMenuMixin.__init__(self, **config)
        self.root = None
        self.items = []
        self.app_menus = {}
        self.main_menu = None
        self.current_wid = None
        self.add_callbacks({"Button1": self.show_menu})
        self.item_pos = 0

    async def _config_async(self):
        if not registrar.started:
            await registrar.start()

        registrar.add_callback(self.client_updated)
        self.set_hooks()
        self.hook_response(startup=True)

    def clear(self):
        self.items = []
        self.bar.draw()

    def client_updated(self, wid):
        if wid in self.app_menus:
            del self.app_menus[wid]

        if wid == self.current_wid:
            create_task(self.get_window_menu(wid))

    def set_hooks(self):
        hook.subscribe.focus_change(self.hook_response)
        hook.subscribe.client_killed(self.client_killed)

    def clear_hooks(self):
        hook.unsubscribe.focus_change(self.hook_response)
        hook.unsubscribe.client_killed(self.client_killed)

    def hook_response(self, *args, startup=False):
        if not startup and self.bar.screen != self.qtile.current_screen:
            self.clear()
            return

        self.current_wid = self.qtile.current_window.wid if self.qtile.current_window else None
        if self.current_wid:
            create_task(self.get_window_menu(self.current_wid))
        elif not startup:
            self.clear()

    def client_killed(self, client):
        wid = client.wid
        pid = client.get_pid()
        if wid in self.app_menus:
            registrar.window_closed(client.wid)
            del self.app_menus[wid]

        if pid in registrar.pids:
            del registrar.pids[pid]

    async def get_window_menu(self, wid):
        win = self.qtile.windows_map.get(wid)
        if not win:
            self.clear()
            return
        if wid in registrar.windows:
            service, path = registrar.get_menu(wid)
        elif not isinstance(win, Internal) and win.get_pid() in registrar.pids:
            # If we can't find the window ID, let's try searching by PID
            service, path = registrar.get_menu_by_pid(win.get_pid())
        else:
            self.clear()
            return

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

    def set_menu_position(self, x, y):
        if self.bar.screen.top == self.bar:
            x = min(self.offsetx + self.item_pos, self.bar.width - self.menu.width)
            y = self.bar.height

        else:
            x = min(self.offsetx + self.item_pos, self.bar.width - self.menu.width)
            y = self.bar.screen.height - self.bar.height - self.menu.height

        return x, y

    def finalize(self):
        registrar.remove_callback(self.client_updated)
        registrar.finalize()
        for item in self.items:
            item.finalize()
        for menu in self.app_menus.values():
            menu.stop()
        self.app_menus.clear()
        self.clear_hooks()
        base._TextBox.finalize(self)
