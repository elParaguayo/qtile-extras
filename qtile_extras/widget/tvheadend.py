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
import json
import os
from datetime import datetime
from pathlib import Path

import requests
from libqtile import bar, images, pangocffi
from libqtile.log_utils import logger
from libqtile.popup import Popup
from libqtile.widget import base
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

from qtile_extras import hook


def icon_path():
    """Get the path to tv icon"""
    dir_path = Path(__file__).resolve() / ".." / ".."
    dir_path = dir_path / "resources" / "tvheadend-icons"
    return str(dir_path.resolve())


class TVHJobServer:
    def __init__(self, host=None, auth=None, timeout=5):
        self.host = host
        self.auth = auth
        self.timeout = timeout
        self.recs = set()

    def _send_api_request(self, path, args=None):
        url = self.host + path

        try:
            r = requests.post(url, data=args, auth=self.auth, timeout=self.timeout)
        except (requests.ConnectionError, requests.Timeout):
            return None

        try:
            return r.json(strict=False)
        except json.decoder.JSONDecodeError:
            return list()

    def _tidy_prog(self, prog, uuid=None):
        x = prog

        return {
            "subtitle": x["disp_subtitle"],
            "title": x["disp_title"],
            "start_epoch": x["start"],
            "stop_epoch": x["stop"],
            "start": datetime.fromtimestamp(x["start"]),
            "stop": datetime.fromtimestamp(x["stop"]),
            "filename": x["filename"],
            "basename": os.path.basename(x["filename"]),
            "creator": x["creator"],
            "channelname": x["channelname"],
            "error": x["errorcode"],
            "uuid": uuid if uuid else x["uuid"],
            "duplicate": x.get("duplicate", 0) > 0,
        }

    def _check_recording(self, progs):
        dtnow = datetime.now()
        live_recs = set()
        for prog in progs:
            recording = prog["start"] <= dtnow <= prog["stop"]
            prog["recording"] = recording
            if recording:
                live_recs.add((prog["uuid"], prog["title"]))

        # Fire hooks for new recordings
        for _, title in live_recs - self.recs:
            hook.fire("tvh_recording_started", title)

        # Fire jooks for finished recordings
        for _, title in self.recs - live_recs:
            hook.fire("tvh_recording_ended", title)

        self.recs = live_recs

        return progs

    def get_upcoming(self, path, hide_duplicates=True):
        programmes = self._send_api_request(path)
        if programmes:
            programmes = [self._tidy_prog(x) for x in programmes["entries"]]
            programmes = self._check_recording(programmes)
            programmes = sorted(programmes, key=lambda x: x["start_epoch"])
            if hide_duplicates:
                programmes = [p for p in programmes if not p["duplicate"]]
        return programmes


class TVHWidget(base._Widget, base.MarginMixin):
    """
    A widget to show whether a TVHeadend server is currently recording or not.

    The widget will also show a popup displaying upcoming recordings.

    When the server is recording a red line will be shown under the icon.
    If there's an error, a yellow line will show above the icon (and
    check the logs).

    NB if you use a username and password, these are stored in plain text. You
    may therefore wish to create an unprivileged user account in TVHeadend that
    only has access to scheduled recordings data.
    """

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("refresh_interval", 30, "Time to update data"),
        ("startup_delay", 5, "Time before sending first web request"),
        ("host", "http://localhost:9981/api", "TVHeadend server address"),
        (
            "auth",
            None,
            "Auth details for accessing tvh. " "Can be None, tuple of (username, password).",
        ),
        ("auth_type", "basic", "HTTP authentication type: 'digest' or 'basic'"),
        ("tvh_timeout", 5, "Seconds before timeout for timeout request"),
        (
            "hide_duplicates",
            True,
            "Remove duplicate recordings from list of upcoming recordings.",
        ),
        ("popup_format", "{start:%a %d %b %H:%M}: {title:.40}", "Upcoming recording text."),
        (
            "popup_font",
            "monospace",
            "Font to use for displaying upcoming recordings. A monospace font " "is recommended",
        ),
        ("popup_opacity", 0.8, "Opacity for popup window."),
        ("popup_padding", 10, "Padding for popup window."),
        ("popup_display_timeout", 10, "Seconds to show recordings."),
        ("warning_colour", "aaaa00", "Highlight when there is an error."),
        ("recording_colour", "bb0000", "Highlight when TVHeadend is recording"),
        (
            "upcoming_recordings_path",
            "/dvr/entry/grid_upcoming",
            "API point for retrieving data on upcoming recordings.",
        ),
    ]

    _dependencies = ["requests"]

    _hooks = [h.name for h in hook.tvh_hooks]

    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)
        self.add_defaults(TVHWidget.defaults)
        self.add_defaults(base.MarginMixin.defaults)
        self.data = []
        self.surfaces = {}
        self.iconsize = 0
        self.popup = None
        self.add_callbacks({"Button1": self.toggle_info})
        self._rec = None

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        self.setup_images()

        if isinstance(self.auth, tuple):
            auth = HTTPDigestAuth if self.auth_type == "digest" else HTTPBasicAuth
            self.auth = auth(*self.auth)

        self.tvh = TVHJobServer(host=self.host, auth=self.auth, timeout=self.tvh_timeout)

        self.timeout_add(self.startup_delay, self.refresh)

    def _get_data(self):
        try:
            data = self.tvh.get_upcoming(
                path=self.upcoming_recordings_path, hide_duplicates=self.hide_duplicates
            )

        except (requests.exceptions.Timeout, requests.ConnectionError):
            logger.info("Couldn't connect to TVH server")
            data = None

        return data

    def _read_data(self, future):
        self.data = future.result()

        self.timeout_add(1, self.draw)
        self.timeout_add(self.refresh_interval, self.refresh)

    def setup_images(self):
        d_images = images.Loader(icon_path())(
            "icon",
        )

        for name, img in d_images.items():
            new_height = self.bar.height - 1
            img.resize(height=new_height)
            self.iconsize = img.width
            self.surfaces[name] = img.pattern

    def refresh(self):
        future = self.qtile.run_in_executor(self._get_data)
        future.add_done_callback(self._read_data)

    def calculate_length(self):
        return self.iconsize

    def draw_highlight(self, top=False, colour="000000"):
        self.drawer.set_source_rgb(colour)

        y = 0 if top else self.bar.height - 2

        # Draw the bar
        self.drawer.fillrect(0, y, self.width, 2, 2)

    def draw(self):
        # Remove background
        self.drawer.clear(self.background or self.bar.background)

        self.drawer.ctx.set_source(self.surfaces["icon"])
        self.drawer.ctx.paint()

        if self.data is None:
            self.draw_highlight(top=True, colour=self.warning_colour)

        elif self.is_recording:
            self.draw_highlight(top=False, colour=self.recording_colour)

        self.draw_at_default_position()

    @property
    def is_recording(self):
        if not self.data:
            return False

        return any(p["recording"] for p in self.data)

    def toggle_info(self):
        if self.popup:
            try:
                self.hide_timer.cancel()
            except AttributeError:
                pass
            self.kill_popup()

        else:
            self.show_recs()

    @property
    def bar_on_top(self):
        return self.bar.screen.top == self.bar

    def kill_popup(self):
        self.popup.kill()
        self.popup = None

    def show_recs(self):
        lines = []

        if not self.data:
            lines.append("No upcoming recordings.")

        else:
            lines.append("Upcoming recordings:")
            for rec in self.data:
                lines.append(self.popup_format.format(**rec))

        self.popup = Popup(
            self.qtile,
            width=self.bar.screen.width,
            height=self.bar.screen.height,
            font=self.popup_font,
            horizontal_padding=self.popup_padding,
            vertical_padding=self.popup_padding,
            opacity=self.popup_opacity,
        )

        text = pangocffi.markup_escape_text("\n".join(lines))

        self.popup.text = text

        self.popup.height = self.popup.layout.height + (2 * self.popup.vertical_padding)
        self.popup.width = self.popup.layout.width + (2 * self.popup.horizontal_padding)

        self.popup.x = min(self.offsetx, self.bar.width - self.popup.width)

        if self.bar_on_top:
            self.popup.y = self.bar.height
        else:
            self.popup.y = self.bar.screen.height - self.popup.height - self.bar.height

        self.popup.place()
        self.popup.draw_text()
        self.popup.unhide()
        self.popup.draw()

        self.hide_timer = self.timeout_add(self.popup_display_timeout, self.kill_popup)

    def info(self):
        info = base._Widget.info(self)
        info["recording"] = self.is_recording
        info["scheduled_recordings"] = len(self.data)
        return info
