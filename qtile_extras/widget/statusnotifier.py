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
from libqtile.widget.helpers.status_notifier import StatusNotifierItem, host
from libqtile.widget.statusnotifier import StatusNotifier as QtileStatusNotifier

from qtile_extras.resources.dbusmenu import DBusMenu
from qtile_extras.widget.mixins import DbusMenuMixin

if TYPE_CHECKING:
    from typing import Callable, Optional

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


StatusNotifierItem.attach_menu = attach_menu
StatusNotifierItem.get_menu = get_menu


class StatusNotifier(QtileStatusNotifier, DbusMenuMixin):
    """
    A modified version of the default Qtile StatusNotifier widget.

    Added the ability to render context menus by right-clicking on the
    icon.
    """

    _experimental = True

    _dependencies = ["dbus-next", "xdg"]

    _screenshots = [("statusnotifier.png", "Widget showing Remmina icon and context menu.")]

    def __init__(self, **config):
        QtileStatusNotifier.__init__(self, **config)
        self.add_defaults(DbusMenuMixin.defaults)
        self.add_defaults(StatusNotifier.defaults)
        DbusMenuMixin.__init__(self, **config)
        self.add_callbacks({"Button3": self.show_menu})

        self.session = os.environ.get("DBUS_SESSION_BUS_ADDRESS")
        self.host = host

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

    def show_menu(self):
        if not self.selected_item:
            return
        self.selected_item.get_menu(callback=self.display_menu)
