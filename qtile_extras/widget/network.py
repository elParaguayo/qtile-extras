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
from libqtile import bar
from libqtile.command.base import expose_command
from libqtile.log_utils import logger
from libqtile.widget import base
from libqtile.widget.wlan import get_status

from qtile_extras.widget.mixins import ConnectionCheckMixin, GraphicalWifiMixin


class WiFiIcon(base._Widget, base.PaddingMixin, GraphicalWifiMixin, ConnectionCheckMixin):
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
        ("interface", "wlan0", "Name of wifi interface."),
        (
            "expanded_timeout",
            5,
            "Time in secs for expanded information to display when clicking on icon.",
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
        self.add_defaults(GraphicalWifiMixin.defaults)
        self.add_defaults(ConnectionCheckMixin.defaults)
        GraphicalWifiMixin.__init__(self)
        ConnectionCheckMixin.__init__(self)

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

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)

        self.set_wifi_sizes()

        if self.update_interval:
            self.timeout_add(self.update_interval, self.loop)

        ConnectionCheckMixin._configure(self)

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

        except Exception:
            logger.exception("Couldn't get wifi info.")

    def draw_wifi_text(self):
        offset = self.wifi_width + 2 * self.wifi_padding_x
        layout = self.get_wifi_text()
        layout.draw(offset, int((self.bar.height - layout.height) / 2))

    def draw(self):
        if not self.configured:
            return

        self.drawer.clear(self.background or self.bar.background)
        self.draw_wifi(
            self.percent,
            foreground=self.active_colour if self.is_connected else self.disconnected_colour,
            background=self.inactive_colour,
        )
        if self._show_text:
            self.draw_wifi_text()
        self.drawer.draw(offsetx=self.offset, offsety=self.offsety, width=self.length)

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
