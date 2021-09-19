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
import math

from libqtile import bar
from libqtile.log_utils import logger
from libqtile.widget import base
from libqtile.widget.wlan import get_status

PI = math.pi

WIFI_ARC_DEGREES = 75


def to_rads(degrees):
    return degrees * PI / 180.0


class WiFiIcon(base._Widget, base.PaddingMixin):
    """
    An simple graphical widget that shows WiFi status.
    """
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("font", "sans", "Default font"),
        ("fontsize", None, "Font size"),
        ("active_colour", "ffffff", "Colour for wifi strength."),
        ("inactive_colour", "666666", "Colour for wifi background."),
        ("update_interval", 1, "Polling interval in secs."),
        ("wifi_arc", 75, "Width of arc in degrees."),
        ("interface", "wlan0", "Name of wifi interface."),
        ("expanded_timeout", 5, "Time in secs for expanded information to display when clicking on icon.")
    ]

    _screenshots = [
        ("wifi_simple.png", ""),
        ("wifi_expanded.png", "Additional detail is visible when clicking on icon")
    ]

    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)
        self.add_defaults(WiFiIcon.defaults)
        self.add_defaults(base.PaddingMixin.defaults)
        self.connections = []
        self.wifi_width = 0
        self.show_text = False
        self.hide_timer = None
        self.essid = ""
        self.percent = 0

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)

        self.set_sizes()
        # self.prepare_images()

        if self.update_interval:
            self.timeout_add(self.update_interval, self.loop)

    def loop(self):
        self.timeout_add(self.update_interval, self.loop)
        self.update()

    def update(self):
        try:
            essid, quality = get_status(self.interface)

            self.essid = essid if essid else ""
            quality = quality if essid else 0
            self.percent = quality / 70

            self.draw()

        except Exception as e:
            logger.warning(f"Couldn't get wifi info. {e}")

    def draw_wifi(self, percentage):
        offset = self.padding_x

        half_arc = self.wifi_arc / 2
        x_offset = int(self.wifi_height * math.sin(to_rads(half_arc)))

        self.drawer.ctx.new_sub_path()

        self.drawer.ctx.move_to(
            self.padding_x + x_offset,
            self.padding_y + self.wifi_height
        )
        self.drawer.ctx.arc(
            offset + x_offset,
            self.padding_y + self.wifi_height,
            self.wifi_height,
            to_rads(270 - half_arc),
            to_rads(270 + half_arc)
        )
        self.drawer.set_source_rgb(self.inactive_colour)
        self.drawer.ctx.fill()

        self.drawer.ctx.new_sub_path()
        self.drawer.ctx.move_to(
            offset + x_offset,
            self.padding_y + self.wifi_height
        )
        self.drawer.ctx.arc(offset+x_offset,
                            self.padding_y + self.wifi_height,
                            self.wifi_height * percentage,
                            to_rads(270 - half_arc),
                            to_rads(270 + half_arc))
        self.drawer.set_source_rgb(self.active_colour)
        self.drawer.ctx.fill()

        offset += self.wifi_width + self.padding_x

        if self.show_text:
            layout = self.get_wifi_text()
            layout.draw(offset, int((self.bar.height - layout.height) / 2))

    def draw(self):
        if not self.configured:
            return

        self.drawer.clear(self.background or self.bar.background)
        self.draw_wifi(self.percent)
        self.drawer.draw(
            offsetx=self.offset,
            offsety=self.offsety,
            width=self.length
        )

    def set_sizes(self):
        self.wifi_height = self.bar.height - (self.padding_y * 2)
        width_ratio = math.sin(to_rads(self.wifi_arc / 2))
        self.wifi_width = (self.wifi_height * width_ratio) * 2
        self.wifi_width = math.ceil(self.wifi_width)

        self.icon_size = self.wifi_height

    def get_wifi_text(self, size_only=False):
        text = f"{self.essid} ({self.percent * 100:.0f}%)"

        if size_only:
            width, _ = self.drawer.max_layout_size(
                [text],
                self.font,
                self.fontsize
            )
            return width

        else:
            layout = self.drawer.textlayout(
                text,
                "ffffff",
                self.font,
                self.fontsize,
                None,
                wrap=False)
            return layout

    def calculate_length(self):
        width = 0

        if not self.configured:
            return width

        width += self.padding_x

        width += self.wifi_width
        if self.show_text:
            width += (self.padding_x +
                      self.get_wifi_text(size_only=True))

        width += self.padding_x

        return width

    def button_press(self, x, y, button):
        # Check if it's a right click and, if so, toggle textt
        if button == 1:
            self.show_text = True
            self.set_hide_timer()
            self.bar.draw()

    def set_hide_timer(self):
        if self.hide_timer:
            self.hide_timer.cancel()

        self.hide_timer = self.timeout_add(self.expanded_timeout, self.hide)

    def hide(self):
        self.show_text = False
        self.bar.draw()
