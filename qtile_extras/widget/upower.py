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

import asyncio
from enum import Enum, auto

from dbus_next.aio import MessageBus
from dbus_next.constants import BusType
from libqtile import bar
from libqtile.log_utils import logger
from libqtile.widget import base

from qtile_extras import hook

PROPS_IFACE = "org.freedesktop.DBus.Properties"
UPOWER_SERVICE = "org.freedesktop.UPower"
UPOWER_INTERFACE = "org.freedesktop.UPower"
UPOWER_PATH = "/org/freedesktop/UPower"
UPOWER_DEVICE = UPOWER_INTERFACE + ".Device"
UPOWER_BUS = BusType.SYSTEM


class BatteryState(Enum):
    NONE = auto()
    FULL = auto()
    LOW = auto()
    CRITICAL = auto()


class UPowerWidget(base._Widget):
    """
    A graphical widget to display laptop battery level.

    The widget uses dbus to read the battery information from the UPower
    interface.

    The widget will display one icon for each battery found or users can
    specify the name of the battery if they only wish to display one.

    Clicking on the widget will display the battery level and the time to
    empty/full.

    All colours can be customised as well as low/critical percentage levels.
    """

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("font", "sans", "Default font"),
        ("fontsize", None, "Font size"),
        ("foreground", "ffffff", "Font colour for information text"),
        ("battery_height", 10, "Height of battery icon"),
        ("battery_width", 20, "Size of battery icon"),
        ("battery_name", None, "Battery name. None = all batteries"),
        ("border_charge_colour", "8888ff", "Border colour when charging."),
        ("border_colour", "dbdbe0", "Border colour when discharging."),
        ("border_critical_colour", "cc0000", "Border colour when battery low."),
        ("fill_normal", "dbdbe0", "Fill when normal"),
        ("fill_low", "aa00aa", "Fill colour when battery low"),
        ("fill_critical", "cc0000", "Fill when critically low"),
        ("fill_charge", None, "Override fill colour when charging"),
        ("margin", 2, "Margin on sides of widget"),
        ("spacing", 5, "Space between batteries"),
        ("percentage_low", 0.20, "Low level threshold."),
        ("percentage_critical", 0.10, "Critical level threshold."),
        (
            "text_charging",
            "({percentage:.0f}%) {ttf} until fully charged",
            "Text to display when charging.",
        ),
        (
            "text_discharging",
            "({percentage:.0f}%) {tte} until empty",
            "Text to display when on battery.",
        ),
        ("text_displaytime", 5, "Time for text to remain before hiding"),
    ]

    _screenshots = [
        ("battery_normal.png", "Normal"),
        ("battery_low.png", "Low"),
        ("battery_critical.png", "Critical"),
        ("battery_charging.png", "Charging"),
        ("battery_multiple.png", "Multiple batteries"),
        ("battery_textdisplay.gif", "Showing text"),
    ]

    _dependencies = ["dbus-next"]

    _hooks = [h.name for h in hook.upower_hooks]

    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)
        self.add_defaults(UPowerWidget.defaults)

        if "font_colour" in config:
            self.foreground = config["font_colour"]
            logger.warning(
                "The use of `font_colour` is deprecated. "
                "Please update your config to use `foreground` instead."
            )

        self.batteries = []
        self.charging = False

        # Initial variables to hide text
        self.show_text = False
        self.hide_timer = None

        self.configured = False

        self.add_callbacks({"Button1": self.toggle_text})

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)

        # Define colours
        self.colours = [
            (self.percentage_critical, self.fill_critical),
            (self.percentage_low, self.fill_low),
            (100, self.fill_normal),
        ]
        self.status = [
            (self.percentage_critical, "Critical"),
            (self.percentage_low, "Low"),
            (100, "Normal"),
        ]
        self.borders = {True: self.border_charge_colour, False: self.border_colour}
        if self.fontsize is None:
            self.fontsize = self.bar.height - self.bar.height / 5

    async def _config_async(self):
        await self._setup_dbus()

    async def _setup_dbus(self):
        # Set up connection to DBus
        self.bus = await MessageBus(bus_type=UPOWER_BUS).connect()
        introspection = await self.bus.introspect(UPOWER_SERVICE, UPOWER_PATH)
        object = self.bus.get_proxy_object(UPOWER_SERVICE, UPOWER_PATH, introspection)

        self.props = object.get_interface("org.freedesktop.DBus.Properties")
        self.props.on_properties_changed(self.upower_change)

        self.upower = object.get_interface(UPOWER_INTERFACE)

        # Get battery details from DBus
        self.batteries = await self.find_batteries()

        # Is laptop charging?
        self.charging = not await self.upower.get_on_battery()

        self.configured = await self._update_battery_info()

    def max_text_length(self):
        # Generate text string based on status
        if self.charging:
            text = self.text_charging.format(percentage=100, ttf="99:99")
        else:
            text = self.text_discharging.format(percentage=100, tte="99:99")

        # Calculate width of text
        width, _ = self.drawer.max_layout_size([text], self.font, self.fontsize)

        return width

    def calculate_length(self):
        # Start with zero width and we'll add to it
        bar_length = 0

        if not self.configured:
            return 0

        # We can use maths to simplify if more than one battery
        num_batteries = len(self.batteries)

        if num_batteries:
            # Icon widths
            length = (
                (self.margin * 2)
                + (self.spacing * (num_batteries - 1))
                + (self.battery_width * num_batteries)
            )

            bar_length += length

            # Add text width if it's being displayed
            if self.show_text:
                bar_length += (self.max_text_length() + self.spacing) * num_batteries

        return bar_length

    async def find_batteries(self):
        # Get all UPower devices that are named "battery"
        batteries = await self.upower.call_enumerate_devices()

        batteries = [b for b in batteries if "battery" in b]

        if not batteries:
            logger.warning("No batteries found. No icons will be displayed.")
            return []

        # Get DBus object for each battery
        battery_devices = []
        for battery in batteries:
            bat = {}

            introspection = await self.bus.introspect(UPOWER_SERVICE, battery)
            battery_obj = self.bus.get_proxy_object(UPOWER_SERVICE, battery, introspection)
            battery_dev = battery_obj.get_interface(UPOWER_DEVICE)
            props = battery_obj.get_interface(PROPS_IFACE)

            bat["device"] = battery_dev
            bat["props"] = props
            bat["name"] = await battery_dev.get_native_path()
            bat["flags"] = BatteryState.NONE
            bat["fraction"] = 0.5

            battery_devices.append(bat)

        # If user only wants named battery, get it here
        if self.battery_name:
            battery_devices = [b for b in battery_devices if b["name"] == self.battery_name]

            if not battery_devices:
                err = "No battery found matching {}.".format(self.battery_name)
                logger.warning(err)
                return []

        # Listen for change signals on DBus
        for battery in battery_devices:
            battery["props"].on_properties_changed(self.battery_change)

        await self._update_battery_info(False)

        return battery_devices

    def upower_change(self, _interface, _changed, _invalidated):
        # Update the charging status
        asyncio.create_task(self._upower_change())

    async def _upower_change(self):
        charging = not await self.upower.get_on_battery()
        if charging != self.charging:
            if charging:
                hook.fire("up_power_connected")
            else:
                hook.fire("up_power_disconnected")
        self.charging = charging
        asyncio.create_task(self._update_battery_info())

    def battery_change(self, _interface, _changed, _invalidated):
        # The batteries are polled every 2 mins by DBus so let's just update
        # when we get any signal
        asyncio.create_task(self._update_battery_info())

    async def _update_battery_info(self, draw=True):
        for battery in self.batteries:
            dev = battery["device"]
            percentage = await dev.get_percentage()
            battery["fraction"] = percentage / 100.0
            battery["percentage"] = percentage
            if self.charging:
                if battery["flags"] in (BatteryState.LOW, BatteryState.CRITICAL):
                    battery["flags"] = BatteryState.NONE
                ttf = await dev.get_time_to_full()
                if ttf == 0 and battery["flags"] != BatteryState.FULL:
                    hook.fire("up_battery_full", battery["name"])
                    battery["flags"] = BatteryState.FULL
                battery["ttf"] = self.secs_to_hm(ttf)
                battery["tte"] = ""
            else:
                if battery["flags"] == BatteryState.FULL:
                    battery["flags"] = BatteryState.NONE
                tte = await dev.get_time_to_empty()
                battery["tte"] = self.secs_to_hm(tte)
                battery["ttf"] = ""
            status = next(x[1] for x in self.status if battery["fraction"] <= x[0])
            if status == "Low":
                if battery["flags"] != BatteryState.LOW and not self.charging:
                    hook.fire("up_battery_low", battery["name"])
                    battery["flags"] = BatteryState.LOW
            elif status == "Critical":
                if battery["flags"] != BatteryState.CRITICAL and not self.charging:
                    hook.fire("up_battery_critical", battery["name"])
                    battery["flags"] = BatteryState.CRITICAL

            battery["status"] = status

        if draw:
            self.qtile.call_soon(self.bar.draw)

        return True

    def draw(self):
        if not self.configured:
            return
        # Remove background
        self.drawer.clear(self.background or self.bar.background)

        # Define an offset for widgets
        offset = self.margin

        # Work out top of battery
        top_margin = (self.bar.height - self.battery_height) / 2

        # Loop over each battery
        for battery in self.batteries:
            # Get battery energy level
            percentage = battery["fraction"]

            # Get the appropriate fill colour
            if self.charging and self.fill_charge:
                fill = self.fill_charge
            else:
                # This finds the first value in self_colours which is greater than
                # the current battery level and returns the colour string
                fill = next(x[1] for x in self.colours if percentage <= x[0])

            # Choose border colour
            if (percentage <= self.percentage_critical) and not self.charging:
                border = self.border_critical_colour
            else:
                border = self.borders[self.charging]

            # Draw the border
            self.drawer._rounded_rect(
                offset, top_margin, self.battery_width, self.battery_height, 1
            )

            self.drawer.set_source_rgb(border)
            self.drawer.ctx.stroke()

            # Work out size of bar inside icon
            fill_width = 2 + (self.battery_width - 6) * percentage

            # Draw the filling of the battery
            self.drawer._rounded_rect(
                offset + 2, top_margin + 2, fill_width, (self.battery_height - 4), 0
            )
            self.drawer.set_source_rgb(fill)
            self.drawer.ctx.fill()

            # Increase offset for next battery
            offset = offset + self.spacing + self.battery_width

            if self.show_text:
                # Generate text based on status and format time-to-full or
                # time-to-empty
                if self.charging:
                    text = self.text_charging.format(**battery)
                else:
                    text = self.text_discharging.format(**battery)

                # Create a text box
                layout = self.drawer.textlayout(
                    text, self.foreground, self.font, self.fontsize, None, wrap=False
                )

                # We want to centre this vertically
                y_offset = (self.bar.height - layout.height) / 2

                # Set the layout as wide as the widget so text is centred
                layout.width = self.max_text_length()

                # Draw it
                layout.draw(offset, y_offset)

                # Increase the offset
                offset += layout.width

        # Redraw the bar
        self.drawer.draw(offsetx=self.offset, offsety=self.offsety, width=self.length)

    def secs_to_hm(self, secs):
        # Basic maths to convert seconds to h:mm format
        m, _ = divmod(secs, 60)
        h, m = divmod(m, 60)

        # Need to mke sure minutes are zero padded in case single digit
        return "{}:{:02d}".format(h, m)

    def toggle_text(self):
        if not self.show_text:
            self.show_text = True

            # Start a timer to hide the text
            self.hide_timer = self.timeout_add(self.text_displaytime, self.hide)
        else:
            self.show_text = False

            # Cancel the timer as no need for it if text is hidden already
            if self.hide_timer:
                self.hide_timer.cancel()

        self.bar.draw()

    def hide(self):
        # Self-explanatory!
        self.show_text = False
        self.bar.draw()

    def info(self):
        info = base._Widget.info(self)
        info["batteries"] = [
            {k: v for k, v in x.items() if k not in ["device", "props", "flags"]}
            for x in self.batteries
        ]
        info["charging"] = self.charging
        info["levels"] = self.status
        return info

    def finalize(self):
        self.props.off_properties_changed(self.upower_change)
        self.bus.disconnect()
        self.bus = None
        base._Widget.finalize(self)
