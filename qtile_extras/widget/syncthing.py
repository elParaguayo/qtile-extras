# Copyright (c) 2022 elParaguayo
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
from pathlib import Path
from typing import Any

import requests
from libqtile import bar
from libqtile.log_utils import logger
from libqtile.widget import base

from qtile_extras import hook
from qtile_extras.images import ImgMask
from qtile_extras.widget.mixins import ProgressBarMixin

ICON_FOLDER = Path(__file__).parent.parent / "resources" / "syncthing"
ICON_PATH = (ICON_FOLDER / "syncthing.svg").resolve().as_posix()

API_COMPLETION = "/rest/db/completion"


class Syncthing(base._Widget, ProgressBarMixin):
    """
    A widget to show the sync status of a Syncthing server.

    By default, the widget displays an icon in the bar which is grey when
    no syncing is occurring but changes to white when syncing starts.

    The widget can be configured to monitor a specific device or folder. By
    default, it monitors the local device at the ``server`` address.

    Note: there is no verification of SSL certificates when connecting to the
    host. If this is a problem for you, please start an issue on the github
    page.
    """

    orientations = base.ORIENTATION_HORIZONTAL

    defaults: list[tuple[str, Any, str]] = [
        ("api_key", None, "API key for the Syncthing server instance."),
        ("update_interval", 5, "Time before updating status."),
        ("update_interval_syncing", 1, "Time before updating while syncing."),
        ("hide_on_idle", True, "Hide widget if no sync in progress."),
        ("server", "http://localhost:8384", "Syncthing API server."),
        ("icon_colour_sync", "ffffff", "Colour for Syncthing logo when syncing."),
        ("icon_colour_idle", "999999", "Colour for Syncthing logo when idle."),
        ("icon_colour_error", "ffff00", "Colour for Syncthing logo when there's an error."),
        ("icon_size", None, "Icon size. None = autofit."),
        ("padding", 2, "Padding around icon."),
        ("bar_height", 10, "Height of sync progress bar."),
        ("show_bar", False, "Show progress bar when syncing."),
        ("show_icon", True, "Show icon."),
        ("bar_text_format", "{percentage:.0%}", "Format string to display text on progress bar."),
        ("bar_colour", "008888", "Bar colour."),
        (
            "filter",
            {},
            "Limit the status check to a specific folder or device. "
            "Takes a dictionary where the key is either 'folder' or 'device' and the value is the appropriate ID. "
            "An empty 'folder' will aggregate all folders. An empty 'device' will use the local device. "
            "Default (empty dictionary) aggregates all folders on local device.",
        ),
    ]

    _dependencies = ["requests"]

    _hooks = [h.name for h in hook.syncthing_hooks]

    def __init__(self, length=bar.CALCULATED, **config):
        base._Widget.__init__(self, length, **config)
        ProgressBarMixin.__init__(self, **config)
        self.add_defaults(ProgressBarMixin.defaults)
        self.add_defaults(Syncthing.defaults)
        self._error = False
        self._stop_log_spam = False
        self.is_syncing = False
        self.bar_value = 0.0

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        if self.api_key is None:
            logger.warning("API key not set.")
            self._error = True
        self._load_icon()
        self.qtile.call_soon(self.update)

    def _load_icon(self):
        self.img = ImgMask.from_path(ICON_PATH)
        self.img.attach_drawer(self.drawer)

        if self.icon_size is None:
            size = self.bar.height - 1 - (self.padding * 2)
        else:
            size = min(self.icon_size, self.bar.height - 1)

        self.img.resize(size)
        self.icon_size = self.img.width

    def calculate_length(self):
        width = 0

        if self.hide_on_idle and not self.is_syncing:
            return width

        if self.show_icon and self.img:
            width += self.icon_size + self.padding

        if self.show_bar and self.is_syncing:
            width += self.bar_width + self.padding

        if width:
            width += self.padding

        return width

    def _send_request(self, endpoint, **params):
        if self.api_key:
            headers = {"X-API-Key": self.api_key}
        else:
            headers = {}

        r = requests.get(f"{self.server}{endpoint}", headers=headers, params=params, verify=False)

        if not r.status_code == 200:
            if not self._error:
                self._error = True
                if not self._stop_log_spam:
                    logger.warning("%s error accessing Syncthing server.", r.status_code)
                    self._stop_log_spam = True
            return {}

        self._stop_log_spam = False
        return r.json()

    def update(self):
        data = self._send_request(API_COMPLETION, **self.filter)

        old_sync = self.is_syncing

        self.bar_value = data["completion"] / 100.0
        self.is_syncing = data["needBytes"] > 0

        self.qtile.call_later(
            self.update_interval_syncing if self.is_syncing else self.update_interval, self.update
        )

        if old_sync != self.is_syncing:
            if self.is_syncing:
                hook.fire("st_sync_started")
            else:
                hook.fire("st_sync_stopped")

        if old_sync != self.is_syncing and (self.hide_on_idle or self.show_bar):
            self.bar.draw()
        else:
            self.draw()

    def draw(self):
        if not self.calculate_length():
            return

        self.drawer.clear(self.background or self.bar.background)

        x_offset = self.padding

        if self.show_icon:
            if self._error:
                icon_colour = self.icon_colour_error
            elif self.is_syncing:
                icon_colour = self.icon_colour_sync
            else:
                icon_colour = self.icon_colour_idle
            offsety = (self.bar.height - self.img.height) // 2
            self.img.draw(colour=icon_colour, x=x_offset, y=offsety)
            x_offset += self.img.width + self.padding

        if self.show_bar and self.is_syncing:
            self.draw_bar(
                x_offset=x_offset, bar_text=self.bar_text_format.format(percentage=self.bar_value)
            )

        self.drawer.draw(offsetx=self.offsetx, offsety=self.offsety, width=self.length)
