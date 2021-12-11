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
import subprocess
from pathlib import Path

import requests
from libqtile import bar
from libqtile.log_utils import logger
from libqtile.widget import base

from qtile_extras.images import ImgMask

SNAPCAST_ICON = Path(__file__).parent / ".." / "resources" / "snapcast-icons" / "snapcast.svg"

SERVER_STATUS = "Server.GetStatus"


class SnapCast(base._Widget):
    """
    A widget to run a snapclient instance in the background.

    This is a work in progress. The plan is to add the ability for the client
    to change groups from widget.
    """

    _experimental = True
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("client_name", None, "Client name (as recognised by server)."),
        ("server_address", "localhost", "Name or IP address of server."),
        ("snapclient", "/usr/bin/snapclient", "Path to snapclient"),
        ("icon_size", None, "Icon size. None = autofit."),
        ("padding", 2, "Padding around icon (and text)."),
        (
            "active_colour",
            "ffffff",
            "Colour when client is active and connected to server",
        ),
        ("inactive_colour", "999999", "Colour when client is inactive"),
        ("error_colour", "ffff00", "Colour when client has an error (check logs)"),
    ]

    _screenshots = [("snapcast.png", "Snapclient active running in background")]

    _dependencies = ["requests"]

    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)
        self.add_defaults(SnapCast.defaults)
        self.add_callbacks(
            {
                "Button1": self.show_select,
                "Button3": self.toggle_state,
                "Button4": self.scroll_up,
                "Button5": self.scroll_down,
            }
        )
        self._id = 0
        self._proc = None
        self.img = None
        self.client_id = None
        self.current_group = {}
        self.show_text = False

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        self._load_icon()
        self._url = f"http://{self.server_address}:1780/jsonrpc"
        self.timeout_add(1, self._check_server)

    def _load_icon(self):
        self.img = ImgMask.from_path(SNAPCAST_ICON)
        self.img.attach_drawer(self.drawer)

        if self.icon_size is None:
            size = self.bar.height - 1
        else:
            size = min(self.icon_size, self.bar.height - 1)

        self.img.resize(size)
        self.icon_size = self.img.width

    def _send_request(self, method, params=dict()):
        self._id += 1
        data = {"id": self._id, "jsonrpc": "2.0", "method": method}
        if params:
            data["params"] = params

        r = requests.post(self._url, json=data)

        if not r.status_code == 200:
            logger.warning("Unable to connect to snapcast server.")
            return {}

        return r.json()

    def _find_id(self, status):
        self.client_id = None
        self.current_group = {}
        for group in status["result"]["server"]["groups"]:
            for client in group.get("clients", list()):
                if client["host"]["name"] == self.client_name:
                    self.client_id = client["id"]
                    self.current_group = {group["name"]: group["id"]}

    def _check_server(self):
        status = self._send_request(SERVER_STATUS)

        if not status:
            return

        self._find_id(status)

        self.streams = [x["id"] for x in status["result"]["server"]["streams"]]

    @property
    def status_colour(self):
        if not self._proc:
            return self.inactive_colour

        if self.client_id:
            return self.active_colour

        return self.error_colour

    def toggle_state(self):
        if self._proc is None:
            self._proc = subprocess.Popen(
                [self.snapclient], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        else:
            self._proc.terminate()
            self._proc = None

        self.draw()

    def refresh(self):
        future = self.qtile.run_in_executor(self._get_data)
        future.add_done_callback(self._read_data)

    def calculate_length(self):
        if self.img is None:
            return 0

        return self.icon_size

    def draw_highlight(self, top=False, colour="000000"):

        self.drawer.set_source_rgb(colour)

        y = 0 if top else self.bar.height - 2

        # Draw the bar
        self.drawer.fillrect(0, y, self.width, 2, 2)

    def draw(self):
        # Remove background
        self.drawer.clear(self.background or self.bar.background)

        offsety = (self.bar.height - self.img.height) // 2
        self.img.draw(colour=self.status_colour, y=offsety)
        self.drawer.draw(offsetx=self.offsetx, offsety=self.offsety, width=self.length)

    def show_select(self):
        pass

    def scroll_up(self):
        pass

    def scroll_down(self):
        pass

    def finalize(self):
        if self._proc:
            self._proc.terminate()
        base._Widget.finalize(self)
