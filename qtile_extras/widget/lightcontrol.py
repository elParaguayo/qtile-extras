# Copyright (c) 2021 elParaguayo
# Copyright (c) 2022 ronniedroid
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

import shutil
import subprocess
from pathlib import Path
import re
import math

from libqtile import bar, confreader, images
from libqtile.command.base import expose_command
from libqtile.log_utils import logger
from libqtile.widget import base

from qtile_extras.popup.toolkit import PopupRelativeLayout, PopupSlider, PopupText
from qtile_extras.widget.mixins import ExtendedPopupMixin

BRIGHTNESS_NOTIFICATION = PopupRelativeLayout(
    width=200,
    height=50,
    controls=[
        PopupText(
            text="Brightness:",
            name="text",
            pos_x=0.1,
            pos_y=0.1,
            height=0.2,
            width=0.8,
            v_align="middle",
            h_align="center",
        ),
        PopupSlider(
            name="brightness",
            pos_x=0.1,
            pos_y=0.3,
            width=0.7,
            height=0.8,
            colour_below="00ffff",
            bar_border_size=2,
            bar_border_margin=1,
            bar_size=6,
            marker_size=0,
            end_margin=0,
        ),
    ],
)

class LightControlWidget(base._Widget, ExtendedPopupMixin):
    """
    The widget is very simple and, so far, just allows controls for
    brightness up, down.
    Brightness control is handled by running the appropriate light command.
    The widget is updated instantly when brightness is changed via this
    code, but will also update on an interval (i.e. it will reflect
    changes to brightness made by other programs).
    The widget displays brightness level via an icon, bar or both. The icon
    is permanently visible while the bar only displays when the brightness
    is changed and will hide after a user-defined period.
    Alternatively, if you select the `popup` mode then no widget will
    appear on the bar and, instead, a small popup will be displayed.
    The layout of the popup can be customised via the `popup_layout` parameter.
    Users should provide a _PopupLayout object. The layout should have at least one
    of the following controls: a PopupSlider named `brightness` and a PopupText control
    named `text` as these controls will be updated whenever the brightness changes.
    """

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("font", "sans", "Default font"),
        ("fontsize", None, "Font size"),
        ("foreground", "ffffff", "Font colour"),
        ("mode", "bar", "Display mode: 'icon', 'bar', 'both', 'popup'."),
        ("hide_interval", 5, "Timeout before bar is hidden after update"),
        ("text_format", "{brightness}%", "String format"),
        ("bar_width", 75, "Width of display bar"),
        ("bar_colour_low", "000099", "Colour of bar if low brightness"),
        ("bar_colour_medium", "009900", "Colour of bar if medium brightness"),
        ("bar_colour_high", "990000", "Colour of bar if high brightness"),
        ("fill_colour_low", "404040", "Colour of icon fill if low brightness"),
        ("fill_colour_medium", "000099", "Colour of icon fill if medium brightness"),
        ("fill_colour_high", "009900", "Colour of icon fill if high brightness"),
        ("fill_colour_full", "990000", "Colour of icon fill if full brightness"),
        ("border_colour_low", "404040", "Colour of icon border if low brightness"),
        ("border_colour_medium", "000099", "Colour of icon border if medium brightness"),
        ("border_colour_high", "009900", "Colour of icon border if high brightness"),
        ("border_colour_full", "990000", "Colour of icon border if full brightness"),
        ("background_fill", "404040", "Colour of icon background"),
        ("show_border", True, "Show border or not?"),
        ("show_background", True, "Show background or not?"),
        ("limit_low", 40, "Max percentage for low range"),
        ("limit_normal", 70, "Max percentage for normal range"),
        ("limit_high", 100, "Max percentage for high range"),
        ("update_interval", 5, "Interval to update widget (e.g. if changes made in other apps)."),
        ("theme_path", None, "Path to theme icons."),
        ("step", 5, "Amount to increase brightness by"),
        ("device", "sysfs/backlight/intel_backlight", "Name of device found with 'Light -L'"),
        ("icon_size", None, "Size of the brightness icon"),
        ("padding", 0, "Padding before icon"),
        ("popup_layout", BRIGHTNESS_NOTIFICATION, "Layout for popup mode"),
        ("popup_hide_timeout", 5, "Time before popup hides"),
        (
            "popup_show_args",
            {"relative_to": 2, "relative_to_bar": True, "y": 50},
            "Control position of popup",
        ),
    ]

    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)
        ExtendedPopupMixin.__init__(self, **config)
        self.add_defaults(ExtendedPopupMixin.defaults)
        self.add_defaults(LightControlWidget.defaults)

        self.add_callbacks(
            {
                "Button4": self.brightness_up,
                "Button5": self.brightness_down,
            }
        )

        # Set up necessary variables
        self.brightness = 0
        self.oldbrightness = 0

        # Variable to store icons
        self.surfaces = {}

        # Work out what we need to display
        self.show_bar = self.mode in ["bar", "both"]
        self.show_icon = self.mode in ["icon", "both"]
        self.show_border = True
        self.show_background = True

        # Define some variables to prevent early errors
        self.iconsize = 0
        self.text_width = 0

        # Variables for the timers we need
        self.update_timer = None
        self.hide_timer = None

        # Start of with bar hidden
        self.hidden = True

        # Map bar colours for brightness level
        self.colours = [
            (self.limit_normal, self.bar_colour_medium),
            (self.limit_high, self.bar_colour_high),
            (self.limit_low, self.bar_colour_low),
        ]

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)

        self.get_brightness()

        if self.mode in ["icon", "both"] and not self.theme_path:
            logger.error("You must set the `theme_path` when using icons")
            raise confreader.ConfigError("No theme_path provided.")

        if self.show_icon:
            try:
                self.setup_images()
            except images.LoadingError:
                logger.error(f"Could not find brightness icons at {self.theme_path}.")
                raise confreader.ConfigError("Brightness icons not found.")

        # Minimum size needed to display text
        self.text_width = self.max_text_width()

        # Bar size is bigger of needed space and user-defined size
        self.bar_size = max(self.text_width, self.bar_width)

        # Start the refresh timer (to check if brightness changed elsewhere)
        self.set_refresh_timer()

    def max_text_width(self):
        # Calculate max width of text given defined layout
        txt_width, _ = self.drawer.max_layout_size(
            [self.text_format.format(brightness=100)], self.font, self.fontsize
        )

        return txt_width

    def calculate_length(self):
        # Size depends on what's being shown
        # Start with zero width and add to it
        width = 0

        # Showing icons?
        if self.show_icon:
            width += self._icon_size + self.padding

        # Showing bar?
        if self.show_bar and not self.hidden:
            width += self.bar_size

        return width

    def status_change(self, bri):
        # Something's changed so let's update display
        # Unhide bar
        self.hidden = False

        # Get new values
        self.brightness = bri

        # Restart timer
        self.set_refresh_timer()

        # If we're showing the bar then set timer to hide it
        if self.show_bar:
            self.set_hide_timer()

        if self.mode == "popup":
            self.update_or_show_popup()

        # Draw
        self.bar.draw()

    def _update_popup(self):
        brightness = self.brightness / 100
        label = f"Brightness {brightness:.0%}"
        self.extended_popup.update_controls(brightness=brightness, text=label)

    def setup_images(self):
        # Load icons
        names = (
            "weather-clear",
            "weather-clear-night",
        )

        d_images = images.Loader(self.theme_path)(*names)

        self._icon_size = self.icon_size if self.icon_size is not None else self.bar.height - 1
        self._icon_padding = (self.bar.height - self._icon_size) // 2

        for name, img in d_images.items():
            img.resize(height=self._icon_size)
            self.icon_width = img.width
            self.surfaces[name] = img.pattern

    def draw(self):
        # Define an offset for x placement
        x_offset = 0
        x = (self.icon_size + self.padding) / 2
        y = self.bar.height / 2
        circle_size = self.icon_size - self.padding

        if self.brightness <= 30:
            start = math.pi/1.5
            end = math.pi * 1.3
            border_fill = self.border_colour_low
            fill = self.fill_colour_low
        elif self.brightness <= 50:
            start = math.pi/2
            end = math.pi * 1.5
            border_fill = self.border_colour_medium
            fill = self.fill_colour_medium
        elif self.brightness <= 70:
            start = math.pi/3
            end = math.pi * 1.6
            border_fill = self.border_colour_high
            fill = self.fill_colour_high
        else:
            start = 0
            end = math.pi*2
            border_fill = self.border_colour_full
            fill = self.fill_colour_full

        # Clear the widget
        self.drawer.clear(self.background or self.bar.background)

        # Which icon do we need?
        if self.show_icon:
            x_offset += self.padding


            if self.show_background:
                self.drawer.ctx.new_sub_path()
                self.drawer.ctx.arc(x, y, circle_size, 0, 2*math.pi)
                self.drawer.set_source_rgb(self.background_fill)
                self.drawer.ctx.fill()
            if self.show_border:
                self.drawer.ctx.new_sub_path()
                self.drawer.ctx.arc(x, y, circle_size, 0, 2*math.pi)
                self.drawer.set_source_rgb(border_fill)
                self.drawer.ctx.stroke()
            self.drawer.ctx.arc(x, y, circle_size, start, end)
            self.drawer.set_source_rgb(fill)
            self.drawer.ctx.fill()
            
            # Increase offset
            x_offset += self.icon_size

        # Does bar need to be displayed
        if self.show_bar and not self.hidden:

            # Text and colour depends on the brightness level
            text = self.text_format.format(brightness=self.brightness)
            fill = next(x[1] for x in self.colours if self.brightness <= x[0])

            # Set bar colours
            self.drawer.set_source_rgb(fill)

            # Draw the bar
            self.drawer.fillrect(x_offset, 0, self.bar_size * (self.brightness / 100), self.height, 1)

            # Create a text box
            layout = self.drawer.textlayout(
                text, self.foreground, self.font, self.fontsize, None, wrap=False
            )

            # We want to centre this vertically
            y_offset = (self.bar.height - layout.height) / 2

            # Set the layout as wide as the widget so text is centred
            layout.width = self.bar_size

            # Add the text to our drawer
            layout.draw(x_offset, y_offset)

        self.drawer.draw(offsetx=self.offset, offsety=self.offsety, width=self.length)

    def refresh(self):
        # Check the brightness levels to see if they've changed
        # Callback will be triggered if they have
        self.get_brightness()

        # Restart timer
        self.set_refresh_timer()

    def set_refresh_timer(self):

        # Delete old timer
        if self.update_timer:
            self.update_timer.cancel()

        # Start new timer
        self.update_timer = self.timeout_add(self.update_interval, self.refresh)

    def set_hide_timer(self):
        # Cancel old timer
        if self.hide_timer:
            self.hide_timer.cancel()

        # Set new timer
        self.hide_timer = self.timeout_add(self.hide_interval, self.hide)

    def hide(self):
        # Hide the widget
        self.hidden = True
        self.bar.draw()

    def _run(self, cmd):

        if not shutil.which("light"):
            logger.warning("'light' is not installed. Unable to set brightness.")
            return

        cmd_get = "light -G -s {}".format(self.device)
        
        # Run the light command to capture brightness value
        if cmd == "get":
            proc = subprocess.run(cmd_get.split(), capture_output=True, text=True).stdout
        else:
            subprocess.run(cmd.split())
            proc = subprocess.run(cmd_get.split(), capture_output=True, text=True).stdout


        matched = re.findall(r'\d+\.\d+', proc)
        self.brightness = int(float(matched[0]))

        # If brightness status has changed
        # then we need to trigger callback
        if self.brightness != self.oldbrightness:
            self.status_change(self.brightness)

            # Record old values
            self.oldbrightness = self.brightness

    def get_brightness(self):
        self._run("get")

    @expose_command()
    def brightness_up(self, *args, **kwargs):
        """Increase brightness"""
        cmd = "light -A {} -s {}".format(self.step, self.device)
        self._run(cmd)

    @expose_command()
    def brightness_down(self, *args, **kwargs):
        """Decrease brightness"""
        cmd = "light -U {} -s {}".format(self.step, self.device)
        self._run(cmd)

    @expose_command()
    def info(self):
        info = base._Widget.info(self)
        info["brightness"] = self.brightness
        return info
