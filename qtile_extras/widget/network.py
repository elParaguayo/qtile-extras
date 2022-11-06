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
import socket
from contextlib import contextmanager

from libqtile import bar
from libqtile.command.base import expose_command
from libqtile.log_utils import logger
from libqtile.widget import base
from libqtile.widget.wlan import get_status

PI = math.pi

WIFI_ARC_DEGREES = 75


def to_rads(degrees):
    return degrees * PI / 180.0


@contextmanager
def socket_context(*args, **kwargs):
    s = socket.socket(*args, **kwargs)
    try:
        yield s
    finally:
        s.close()


class WiFiIcon(base._Widget, base.PaddingMixin):
    """
    An simple graphical widget that shows WiFi status.

    Left-clicking the widget will show the name of the network.

    The widget can also periodically poll an external IP address to
    check whether the device is connected to the internet. To enable
    this, you need to set the `check_connection_interval`.
    """

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("font", "sans", "Default font"),
        ("fontsize", None, "Font size"),
        ("foreground", "ffffff", "Font colour for information text"),
        ("active_colour", "ffffff", "Colour for wifi strength."),
        ("inactive_colour", "666666", "Colour for wifi background."),
        ("update_interval", 1, "Polling interval in secs."),
        ("wifi_arc", 75, "Width of arc in degrees."),
        ("interface", "wlan0", "Name of wifi interface."),
        (
            "expanded_timeout",
            5,
            "Time in secs for expanded information to display when clicking on icon.",
        ),
        (
            "check_connection_interval",
            0,
            "Interval to check if device connected to internet (0 to disable)",
        ),
        ("disconnected_colour", "aa0000", "Colour when device has no internet connection"),
        ("internet_check_host", "8.8.8.8", "IP adddress to check for internet connection"),
        ("internet_check_port", 53, "Port to check for internet connection"),
        (
            "internet_check_timeout",
            5,
            "Period before internet check times out and widget reports no internet connection.",
        ),
        ("show_ssid", False, "Show SSID and signal strength."),
    ]

    _screenshots = [
        ("wifi_simple.png", ""),
        ("wifi_expanded.png", "Additional detail is visible when clicking on icon"),
    ]

    _dependencies = ["iwlib"]

    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)
        self.add_defaults(WiFiIcon.defaults)
        self.add_defaults(base.PaddingMixin.defaults)

        self.add_callbacks({"Button1": self.show_text})

        if "font_colour" in config:
            self.foreground = config["font_colour"]
            logger.warning(
                "The use of `font_colour` is deprecated. "
                "Please update your config to use `foreground` instead."
            )

        self.connections = []
        self.wifi_width = 0
        self._show_text = self.show_ssid
        self.hide_timer = None
        self.essid = ""
        self.percent = 0

        # If we're checking the internet connection then we assume we're disconnected
        # until we've verified the connection
        self.is_connected = not bool(self.check_connection_interval)

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)

        self.set_sizes()

        if self.update_interval:
            self.timeout_add(self.update_interval, self.loop)

        if self.check_connection_interval:
            self.timeout_add(self.update_interval, self.check_connection)

    def check_connection(self):
        self.qtile.run_in_executor(self._check_internet).add_done_callback(self._check_connected)

    def _check_internet(self):
        with socket_context(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(self.internet_check_timeout)
            try:
                s.connect((self.internet_check_host, self.internet_check_port))
                return True
            except (TimeoutError, OSError):
                return False

    def _check_connected(self, result):
        self.is_connected = result.result()
        self.timeout_add(self.check_connection_interval, self.check_connection)

    def loop(self):
        self.timeout_add(self.update_interval, self.loop)
        self.update()

    def update(self):
        try:
            essid, quality = get_status(self.interface)

            self.essid = essid if essid else ""
            quality = quality if essid else 0
            self.percent = quality / 70

            if self._show_text:
                self.bar.draw()
            else:
                self.draw()

        except Exception as e:
            logger.warning(f"Couldn't get wifi info. {e}")

    def draw_wifi(self, percentage):
        offset = self.padding_x

        half_arc = self.wifi_arc / 2
        x_offset = int(self.wifi_height * math.sin(to_rads(half_arc)))

        self.drawer.ctx.new_sub_path()

        self.drawer.ctx.move_to(self.padding_x + x_offset, self.padding_y + self.wifi_height)
        self.drawer.ctx.arc(
            offset + x_offset,
            self.padding_y + self.wifi_height,
            self.wifi_height,
            to_rads(270 - half_arc),
            to_rads(270 + half_arc),
        )
        self.drawer.set_source_rgb(self.inactive_colour)
        self.drawer.ctx.fill()

        self.drawer.ctx.new_sub_path()
        self.drawer.ctx.move_to(offset + x_offset, self.padding_y + self.wifi_height)
        self.drawer.ctx.arc(
            offset + x_offset,
            self.padding_y + self.wifi_height,
            self.wifi_height * percentage,
            to_rads(270 - half_arc),
            to_rads(270 + half_arc),
        )
        self.drawer.set_source_rgb(
            self.active_colour if self.is_connected else self.disconnected_colour
        )
        self.drawer.ctx.fill()

        offset += self.wifi_width + self.padding_x

        if self._show_text:
            layout = self.get_wifi_text()
            layout.draw(offset, int((self.bar.height - layout.height) / 2))

    def draw(self):
        if not self.configured:
            return

        self.drawer.clear(self.background or self.bar.background)
        self.draw_wifi(self.percent)
        self.drawer.draw(offsetx=self.offset, offsety=self.offsety, width=self.length)

    def set_sizes(self):
        self.wifi_height = self.bar.height - (self.padding_y * 2)
        width_ratio = math.sin(to_rads(self.wifi_arc / 2))
        self.wifi_width = (self.wifi_height * width_ratio) * 2
        self.wifi_width = math.ceil(self.wifi_width)

        self.icon_size = self.wifi_height

    def get_wifi_text(self, size_only=False):
        text = f"{self.essid} ({self.percent * 100:.0f}%)"

        if size_only:
            width, _ = self.drawer.max_layout_size([text], self.font, self.fontsize)
            return width

        else:
            layout = self.drawer.textlayout(
                text, self.foreground, self.font, self.fontsize, None, wrap=False
            )
            return layout

    def calculate_length(self):
        width = 0

        if not self.configured:
            return width

        width += self.padding_x

        width += self.wifi_width
        if self._show_text:
            width += self.padding_x + self.get_wifi_text(size_only=True)

        width += self.padding_x

        return width

    @expose_command
    def show_text(self):
        if self._show_text:
            return

        self._show_text = True
        self.set_hide_timer()
        self.bar.draw()

    def set_hide_timer(self):
        if self.hide_timer:
            self.hide_timer.cancel()

        self.hide_timer = self.timeout_add(self.expanded_timeout, self.hide)

    @expose_command
    def hide(self):
        if not self._show_text:
            return

        self._show_text = False
        self.bar.draw()
