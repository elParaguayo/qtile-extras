# Copyright (c) 2023 elParaguayo
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
from libqtile.command.base import expose_command
from libqtile.utils import create_task
from libqtile.widget.bluetooth import Bluetooth as QBluetooth
from libqtile.widget.bluetooth import DeviceState

from qtile_extras.popup.menu import PopupMenuSeparator
from qtile_extras.widget.mixins import MenuMixin


class Bluetooth(QBluetooth, MenuMixin):
    """
    Modified version of the stock Qtile widget.

    The only difference is to add a context menu (on Button 3) to show
    options for all adapters and devices.
    """

    def __init__(self, **config):
        QBluetooth.__init__(self, **config)
        self.add_defaults(MenuMixin.defaults)
        MenuMixin.__init__(self, **config)
        self.add_callbacks({"Button3": self.show_devices})

    @expose_command
    def show_devices(
        self,
        x=None,
        y=None,
        centered=False,
        warp_pointer=False,
        relative_to=1,
        relative_to_bar=False,
        hide_on_timeout=None,
    ):
        """Show menu with available adapters and devices."""
        self.display_menu(
            menu_items=self._get_menu_items(),
            x=x,
            y=y,
            centered=centered,
            warp_pointer=warp_pointer,
            relative_to=relative_to,
            relative_to_bar=relative_to_bar,
            hide_on_timeout=hide_on_timeout,
        )

    def _get_menu_items(self):
        menu_items = []

        pmi = self.create_menu_item
        pms = self.create_menu_separator

        for adapter in self.adapters.values():
            menu_items.append(pmi(f"Adapter: {adapter.name}", enabled=False))
            for text, action in self._get_adapter_menu(adapter)[:2]:  # Remove the "exit" option
                menu_items.append(pmi(text, mouse_callbacks={"Button1": action}))
            menu_items.append(pms())

        def action(device):
            return {
                "mouse_callbacks": {"Button1": lambda device=device: create_task(device.action())}
            }

        connected = [d for d in self.devices.values() if d.status == DeviceState.CONNECTED]
        disconnected = [d for d in self.devices.values() if d.status == DeviceState.PAIRED]
        unpaired = [d for d in self.devices.values() if d.status == DeviceState.UNPAIRED]

        all_devices = [
            (connected, "Connected"),
            (disconnected, "Disconnected"),
            (unpaired, "Unpaired"),
        ]

        for devices, header in all_devices:
            if devices:
                if menu_items and not isinstance(menu_items[-1], PopupMenuSeparator):
                    menu_items.append(pms())

                menu_items.append(pmi(f"{header} devices:", enabled=False))

            for device in devices:
                menu_items.append(pmi(device.name, **action(device)))

        return menu_items
