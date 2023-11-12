# Copyright (c) 2020 elParaguayo
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

# type: ignore

import asyncio
import math

from dbus_next.aio import MessageBus
from dbus_next.constants import BusType
from libqtile import bar
from libqtile.log_utils import logger
from libqtile.widget import base


class UnitStatus(base._Widget, base.PaddingMixin, base.MarginMixin):
    """
    UnitStatus is a basic widget for Qtile which shows the current
    status of systemd units.

    It may not be particular useful for you and was primarily written
    as an exercise to familiarise myself with writing Qtile widgets and
    interacting with d-bus.

    The widget is incredibly basic. It subscribes to the systemd d-bus
    interface, finds the relevant service and displays an icon based
    on the current status. The widget listens for announced changes to
    the service and updates the icon accordingly.
    """

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("bus_name", "system", "Which bus to use. Accepts 'system' or 'session'."),
        ("font", "sans", "Default font"),
        ("fontsize", None, "Font size"),
        ("foreground", "ffffff", "Font colour"),
        ("unitname", "NetworkManager.service", "Name of systemd unit."),
        ("label", "NM", "Short text to display next to indicator."),
        ("colour_active", "00ff00", "Colour for active indicator"),
        ("colour_inactive", "ffffff", "Colour for active indicator"),
        ("colour_failed", "ff0000", "Colour for active indicator"),
        ("colour_dead", "666666", "Colour for dead indicator"),
        ("indicator_size", 10, "Size of indicator (None = up to margin)"),
        (
            "state_map",
            {
                "active": ("colour_active", "colour_active"),
                "inactive": ("colour_inactive", "colour_inactive"),
                "deactivating": ("colour_inactive", "colour_active"),
                "activating": ("colour_active", "colour_inactive"),
                "failed": ("colour_failed", "colour_failed"),
                "not-found": ("colour_inactive", "colour_failed"),
                "dead": ("colour_dead", "colour_dead"),
            },
            "Map of indicator colours (border, fill)",
        ),
    ]

    _screenshots = [("widget-unitstatus-screenshot.png", "")]

    _dependencies = ["dbus-next"]

    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)
        self.add_defaults(UnitStatus.defaults)
        self.add_defaults(base.PaddingMixin.defaults)
        self.add_defaults(base.MarginMixin.defaults)

        self.colours = {}

        for state, cols in self.state_map.items():
            self.colours[state] = tuple(getattr(self, col) for col in cols)

        if self.bus_name.lower() == "session":
            self.bus_type = BusType.SESSION
        else:
            if self.bus_name.lower() not in ["session", "system"]:
                logger.warning("Unknown bus name. Defaulting to system bus.")
            self.bus_type = BusType.SYSTEM

        self.state = "not-found"

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)

        self.layout = self.drawer.textlayout(
            self.label, self.foreground, self.font, self.fontsize, None, wrap=False
        )

        if self.indicator_size is not None:
            self.indicator_size = max(self.indicator_size, 6)

        max_indicator = self.bar.height - 2 * self.margin

        if self.indicator_size is None:
            self.indicator_size = max_indicator
        else:
            self.indicator_size = min(max_indicator, self.indicator_size)

        # # Set fontsize
        # if self.fontsize is None:
        #     calc = self.bar.height - self.margin * 2
        #     self.fontsize = max(calc, 1)

        self.layout.width = self.text_width()

    def _config_async(self):
        asyncio.create_task(self._connect_dbus())

    async def _connect_dbus(self):
        self.bus = await MessageBus(bus_type=self.bus_type).connect()

        introspection = await self.bus.introspect(
            "org.freedesktop.systemd1", "/org/freedesktop/systemd1"
        )

        object = self.bus.get_proxy_object(
            "org.freedesktop.systemd1", "/org/freedesktop/systemd1", introspection
        )

        self.manager = object.get_interface("org.freedesktop.systemd1.Manager")

        unit_path = await self.find_unit()

        if not unit_path:
            return

        await self._subscribe_unit(unit_path)

    async def find_unit(self):
        units = await self.manager.call_list_units()

        unit = [x for x in units if x[0] == self.unitname]

        if not unit:
            self.unit = None
            return False

        else:
            path = unit[0][6]
            return path

    async def _subscribe_unit(self, path):
        introspection = await self.bus.introspect("org.freedesktop.systemd1", path)

        object = self.bus.get_proxy_object("org.freedesktop.systemd1", path, introspection)

        self.unit = object.get_interface("org.freedesktop.systemd1.Unit")
        props = object.get_interface("org.freedesktop.DBus.Properties")

        self.state = await self.unit.get_active_state()

        props.on_properties_changed(self._changed)

        self.draw()

    def _changed(self, _interface, changed, _invalidated):
        state = changed.get("ActiveState")

        if state:
            self.state = state.value
            self.draw()

    def text_width(self):
        width, _ = self.drawer.max_layout_size([self.label], self.font, self.fontsize)
        return width

    def calculate_length(self):
        width = self.text_width()
        width = width + 3 * (self.padding_x) + self.indicator_size
        return width

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)

        self.layout.draw(
            (self.margin * 2 + self.indicator_size),
            int(self.bar.height / 2.0 - self.layout.height / 2.0) + 1,
        )

        i_margin = int((self.bar.height - self.indicator_size) / 2)

        self.draw_indicator(
            self.margin,
            i_margin,
            self.indicator_size,
            self.indicator_size,
            2,
            self.colours[self.state],
        )

        self.drawer.draw(offsetx=self.offset, offsety=self.offsety, width=self.width)

    # This is just Drawer's "_rounded_rect" but with a bigger corner radius
    def circle(self, x, y, width, height, linewidth):
        aspect = 1.0
        corner_radius = height / 3.0
        radius = corner_radius / aspect
        degrees = math.pi / 180.0

        self.drawer.ctx.new_sub_path()

        delta = radius + linewidth / 2
        self.drawer.ctx.arc(x + width - delta, y + delta, radius, -90 * degrees, 0 * degrees)
        self.drawer.ctx.arc(
            x + width - delta, y + height - delta, radius, 0 * degrees, 90 * degrees
        )
        self.drawer.ctx.arc(x + delta, y + height - delta, radius, 90 * degrees, 180 * degrees)
        self.drawer.ctx.arc(x + delta, y + delta, radius, 180 * degrees, 270 * degrees)

        self.drawer.ctx.close_path()

    def draw_indicator(self, x, y, width, height, linewidth, statecols):
        self.circle(x, y, width, height, linewidth)
        self.drawer.set_source_rgb(statecols[1])
        self.drawer.ctx.fill()
        self.drawer.set_source_rgb(statecols[0])
        self.circle(x, y, width, height, linewidth)
        self.drawer.ctx.stroke()

    def info(self):
        info = base._Widget.info(self)
        info["unit"] = self.unitname
        info["text"] = self.label
        info["state"] = self.state
        info["bus"] = self.bus_name
        return info
