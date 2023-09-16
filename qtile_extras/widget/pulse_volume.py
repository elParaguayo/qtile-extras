# -*- coding: utf-8 -*-
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
from libqtile.widget.pulse_volume import PulseVolume as QPulseVolume

from qtile_extras.popup.menu import PopupMenuItem
from qtile_extras.widget.mixins import MenuMixin


class PulseVolume(QPulseVolume, MenuMixin):
    """
    Same as qtile's ``PulseVolume`` widget but includes the ability to
    select the default output sink via the ``select_sink()`` command. This is
    bound to the middle-click button on the widget by default.
    """

    defaults = [("menu_width", 300, "Width of list showing available sinks.")]

    def __init__(self, **config):
        QPulseVolume.__init__(self, **config)
        self.add_defaults(MenuMixin.defaults)
        self.add_defaults(PulseVolume.defaults)
        MenuMixin.__init__(self, **config)
        self.add_callbacks({"Button2": self.select_sink})

    async def set_sink(self, sink):
        if not self.pulse.connected:
            return

        await self.pulse.default_set(sink)

    async def show_sinks(self):
        if not self.pulse.connected:
            return

        sinks = await self.pulse.sink_list()
        if not sinks:
            return

        menu_items = [PopupMenuItem(text="Select output sink:", enabled=False)]

        def _callback(team):
            return {
                "mouse_callbacks": {"Button1": lambda sink=sink: create_task(self.set_sink(sink))}
            }

        for sink in sinks:
            menu_items.append(PopupMenuItem(text=sink.description, **_callback(sink)))

        self.display_menu(menu_items)

    @expose_command()
    def select_sink(self):
        """Select output sink from available sinks."""
        create_task(self.show_sinks())
