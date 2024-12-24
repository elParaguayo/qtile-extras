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
import contextlib
import shlex
import subprocess
from pathlib import Path

from libqtile import bar
from libqtile.command.base import expose_command
from libqtile.widget import base

from qtile_extras.images import ImgMask
from qtile_extras.resources.snapcast import SnapControl, SnapMprisPlayer

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
        ("server_port", 1780, "Port the snapserver is running on"),
        ("enable_mpris2", False, "Broadcast metadata on Mpris2 interface"),
        ("snapclient", "/usr/bin/snapclient", "Path to snapclient"),
        ("options", "", "Options to be passed to snapclient."),
        ("icon_size", None, "Icon size. None = autofit."),
        ("padding", 2, "Padding around icon (and text)."),
        (
            "active_colour",
            "ffffff",
            "Colour when client is active and connected to server",
        ),
        ("inactive_colour", "999999", "Colour when client is inactive"),
        ("error_colour", "ffff00", "Colour when client has an error (check logs)"),
        (
            "server_reconnect_interval",
            15,
            "Interval before retrying to find player on server after failed attempt",
        ),
    ]

    _dependencies = ["requests", "websockets"]

    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)
        self.add_defaults(SnapCast.defaults)
        self.add_callbacks(
            {
                "Button3": self.toggle_state,
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
        self._cmd = [self.snapclient]
        if self.options:
            self._cmd.extend(shlex.split(self.options))
        self._load_icon()
        self._url = f"http://{self.server_address}:1780/jsonrpc"
        self.timeout_add(1, self._check_server)

    async def _config_async(self):
        self.control = SnapControl("192.168.1.100", 1780)
        self.control.subscribe(self._on_message)
        await self.control.start()
        if self.enable_mpris2:
            self.mpris = SnapMprisPlayer(
                "org.mpris.MediaPlayer2.QtileSnapcastWidget", self.control, self
            )
            await self.mpris.start()

    def _on_message(self, message):
        if "method" not in message:
            return

        params = message["params"]

        match message["method"]:
            case "Client.OnConnect":
                self.on_connect(params)
            case "Client.OnDisconnect":
                self.on_disconnect(params)
            case _:
                pass

    def on_connect(self, params):
        if params["client"]["host"]["name"] == self.client_name:
            self.client_id = params["client"]["id"]
            self._check_server()

    def on_disconnect(self, params):
        if params["client"]["host"]["name"] == self.client_name:
            self.client_id = None

    def _load_icon(self):
        self.img = ImgMask.from_path(SNAPCAST_ICON)
        self.img.attach_drawer(self.drawer)

        if self.icon_size is None:
            size = self.bar.height - 1 - (self.padding * 2)
        else:
            size = min(self.icon_size, self.bar.height - 1)

        self.img.resize(size)
        self.icon_size = self.img.width

    def _find_id(self, status):
        self.current_group = {}
        for group in status["server"]["groups"]:
            for client in group.get("clients", list()):
                if client["host"]["name"] == self.client_name:
                    self.client_id = client["id"]
                    self.current_group = {group["name"]: group["id"]}

    def _check_server(self):
        self.control.send(SERVER_STATUS, callback=self._check_response)

    def _check_response(self, reply):
        if not reply:
            self.streams = []
            self.timeout_add(self.server_reconnect_interval, self._check_server)
            return

        if self.client_id is None:
            self._find_id(reply)

        self.streams = [x["id"] for x in reply["server"]["streams"]]

    @property
    def status_colour(self):
        if not self._proc:
            return self.inactive_colour

        if self.client_id:
            return self.active_colour

        return self.error_colour

    @expose_command()
    def toggle_state(self):
        """Toggle Snapcast on and off."""
        if self._proc is None:
            self._proc = subprocess.Popen(
                self._cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        else:
            self._proc.terminate()
            # Use wait() to prevent zombie process but don't block indefinitely
            with contextlib.suppress(subprocess.TimeoutExpired):
                self._proc.wait(timeout=2)
            self._proc = None

        self.draw()

    @expose_command
    def stop(self):
        if self._proc:
            self.toggle_state()

    def calculate_length(self):
        if self.img is None:
            return 0

        return self.icon_size + 2 * self.padding

    def draw(self):
        # Remove background
        self.drawer.clear(self.background or self.bar.background)

        offsety = (self.bar.height - self.img.height) // 2
        self.img.draw(colour=self.status_colour, x=self.padding, y=offsety)
        self.drawer.draw(offsetx=self.offsetx, offsety=self.offsety, width=self.length)

    def finalize(self):
        if self._proc:
            self._proc.terminate()
        base._Widget.finalize(self)
