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
import time
from pathlib import Path
from uuid import getnode

from libqtile import bar
from libqtile.command.base import expose_command
from libqtile.log_utils import logger
from libqtile.utils import create_task
from libqtile.widget import base

from qtile_extras.images import ImgMask
from qtile_extras.resources.snapcast import SnapControl, SnapMprisPlayer
from qtile_extras.resources.snapcast.snapcontrol import (
    CLIENT_ONCONNECT,
    CLIENT_ONDISCONNECT,
    GROUP_ONSTREAMCHANGED,
    SERVER_GETSTATUS,
    SERVER_ONDISCONNECT,
)

SNAPCAST_ICON = Path(__file__).parent / ".." / "resources" / "snapcast-icons" / "snapcast.svg"


class SnapGroup:
    @classmethod
    def from_json(cls, data):
        obj = cls()
        obj.id = data["id"]
        obj.stream = data["stream_id"]
        obj.clients = [SnapClient.from_json(c) for c in data["clients"]]
        obj.clients = list(filter(lambda c: not c.inactive, obj.clients))
        return obj

    @property
    def inactive(self):
        return not self.clients


class SnapStream:
    @classmethod
    def from_json(cls, data):
        obj = cls()
        obj.id = data["id"]
        return obj


class SnapClient:
    @classmethod
    def from_json(cls, data):
        obj = cls()
        obj.id = data["id"]
        obj.name = data["config"]["name"]
        obj.mac = data["host"]["mac"]
        obj.inactive = (int(time.time()) - data["lastSeen"]["sec"]) > 30
        return obj


class SnapCast(base._Widget):
    """
    A widget to run a snapclient instance in the background.

    Stream metadata can be displayed via the ``Mpris2`` widget if ``enable_mpris2``
    is set to ``True``. Playback control may also be available if supported by the current
    stream.

    This is a work in progress. The plan is to add the ability for the client
    to change groups from widget.
    """

    _experimental = True
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("client_id", None, "Client id (if blank, will use MAC address)."),
        ("server_address", "localhost", "Name or IP address of server."),
        ("server_port", 1705, "Port the snapserver is running on"),
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
        self.mac = ":".join(f"{getnode():012x}"[i : i + 2] for i in range(0, 12, 2))
        self._proc = None
        self.img = None
        self.current_group = {}
        self.show_text = False
        self.groups = []
        self.streams = []
        self.snapclient_id = self.client_id or self.mac
        self.stream = None

        if "client_name" in config:
            logger.warning("The 'client_name' option is deprecated.")

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        self._cmd = [self.snapclient]
        if self.options:
            self._cmd.extend(shlex.split(self.options))
        self._cmd.extend(["--hostID", self.snapclient_id])
        self._load_icon()
        self.timeout_add(1, self._check_server)

    async def _config_async(self):
        self.control = SnapControl(self.server_address, self.server_port)
        self.control.subscribe(CLIENT_ONCONNECT, self.on_client_connection_event)
        self.control.subscribe(CLIENT_ONDISCONNECT, self.on_client_connection_event)
        self.control.subscribe(SERVER_ONDISCONNECT, self.on_server_connection_lost)
        self.control.subscribe(GROUP_ONSTREAMCHANGED, self.on_client_connection_event)
        await self.control.start()
        if self.enable_mpris2:
            self.mpris = SnapMprisPlayer(
                "org.mpris.MediaPlayer2.QtileSnapcastWidget", self.control, self
            )

    def on_server_connection_lost(self, _params):
        pass

    def on_client_connection_event(self, _params):
        self._check_server()

    def _load_icon(self):
        self.img = ImgMask.from_path(SNAPCAST_ICON)
        self.img.attach_drawer(self.drawer)

        if self.icon_size is None:
            size = self.bar.height - 1 - (self.padding * 2)
        else:
            size = min(self.icon_size, self.bar.height - 1)

        self.img.resize(size)
        self.icon_size = self.img.width

    def _find_client(self):
        stream = None
        for group in self.groups:
            for client in group.clients:
                if self.client_id and client.id == self.client_id:
                    stream = group.stream
                    break
                elif client.mac == self.mac:
                    stream = group.stream
                    break
            else:
                continue
            break

        self.stream = stream
        self.draw()

    def _check_server(self):
        self.control.send(SERVER_GETSTATUS, callback=self._check_response)

    def _check_response(self, reply, error):
        if error:
            logger.warning("Error received when checking server status: %s.", error)
            self.streams = []
            self.timeout_add(self.server_reconnect_interval, self._check_server)
            return

        self.streams = [SnapStream.from_json(s) for s in reply["server"]["streams"]]
        self.groups = [SnapGroup.from_json(g) for g in reply["server"]["groups"]]
        self._find_client()
        self.groups = list(filter(lambda g: not g.inactive, self.groups))

    @property
    def status_colour(self):
        if not self._proc:
            return self.inactive_colour

        if self.stream:
            return self.active_colour

        return self.error_colour

    @expose_command()
    def toggle_state(self):
        """Toggle Snapcast on and off."""
        if self._proc is None:
            self._proc = subprocess.Popen(
                self._cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            if self.enable_mpris2:
                self.start_mpris2()
        else:
            if self.enable_mpris2:
                self.stop_mpris2()
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

    def start_mpris2(self):
        task = create_task(self.mpris.start())
        task.add_done_callback(self._mpris_started)

    def _mpris_started(self, task):
        if not task.result():
            logger.warning("Could not start mpris interface for snapcast.")

    def stop_mpris2(self):
        self.mpris.stop()

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
