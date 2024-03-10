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
from libqtile.widget.pulse_volume import pulse

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
        if not pulse.pulse.connected:
            return

        await pulse.pulse.default_set(sink)

    async def show_sinks(
        self,
        x=None,
        y=None,
        centered=False,
        warp_pointer=False,
        relative_to=1,
        relative_to_bar=False,
        hide_on_timeout=None,
    ):
        if not pulse.pulse.connected:
            return

        sinks = await pulse.pulse.sink_list()
        if not sinks:
            return

        pmi = self.create_menu_item

        menu_items = [pmi(text="Select output sink:", enabled=False)]

        def _callback(team):
            return {
                "mouse_callbacks": {"Button1": lambda sink=sink: create_task(self.set_sink(sink))}
            }

        for sink in sinks:
            menu_items.append(pmi(text=sink.description, **_callback(sink)))

        self.display_menu(
            menu_items,
            x=x,
            y=y,
            centered=centered,
            warp_pointer=warp_pointer,
            relative_to=relative_to,
            relative_to_bar=relative_to_bar,
            hide_on_timeout=hide_on_timeout,
        )

    @expose_command()
    def select_sink(
        self,
        x=None,
        y=None,
        centered=False,
        warp_pointer=False,
        relative_to=1,
        relative_to_bar=False,
        hide_on_timeout=None,
    ):
        """Select output sink from available sinks."""
        task = self.show_sinks(
            x=x,
            y=y,
            centered=centered,
            warp_pointer=warp_pointer,
            relative_to=relative_to,
            relative_to_bar=relative_to_bar,
            hide_on_timeout=hide_on_timeout,
        )
        create_task(task)
