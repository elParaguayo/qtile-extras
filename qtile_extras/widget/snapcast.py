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
    GROUP_SETCLIENTS,
    GROUP_SETSTREAM,
    SERVER_GETSTATUS,
    SERVER_ONDISCONNECT,
)
from qtile_extras.widget.mixins import MenuMixin

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

    def __contains__(self, other):
        return any(other in c.id for c in self.clients)


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
        obj.name = data["config"]["name"] or data["host"]["name"]
        obj.mac = data["host"]["mac"]
        obj.inactive = (int(time.time()) - data["lastSeen"]["sec"]) > 30
        return obj

    def __eq__(self, other):
        if isinstance(other, SnapClient):
            return self.id == other.id
        elif isinstance(other, str):
            return self.id == other

        return False


class SnapCast(base._Widget, MenuMixin):
    """
    A widget to run a snapclient instance in the background.

    Stream metadata can be displayed via the ``Mpris2`` widget if ``enable_mpris2``
    is set to ``True``. Playback control may also be available if supported by the current
    stream.

    Right-clicking on the widget will toggle the player while left-clicking will open a
    menu to provide additional control. Users can move the client between groups and change
    the group's stream.
    """

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
        self.add_defaults(MenuMixin.defaults)
        MenuMixin.__init__(self, **config)
        self.add_callbacks(
            {
                "Button1": self.show_stream_options,
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
        self.mpris = None
        self.finalising = False

        if "client_name" in config:
            logger.warning("The 'client_name' option is deprecated.")

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        self._cmd = [self.snapclient]
        if self.options:
            self._cmd.extend(shlex.split(self.options))
        if self.server_address:
            self._cmd.extend(["-h", self.server_address])
        self._cmd.extend(["--hostID", self.snapclient_id])
        self._load_icon()

    async def _config_async(self):
        self.control = SnapControl(self.server_address, self.server_port)
        self.control.subscribe(SERVER_ONDISCONNECT, self.on_server_connection_lost)
        self.control.subscribe(CLIENT_ONCONNECT, self.on_update)
        self.control.subscribe(CLIENT_ONDISCONNECT, self.on_update)
        self.control.subscribe(GROUP_ONSTREAMCHANGED, self.on_update)

        await self._start_control()

    async def _start_control(self):
        connected = await self.control.start()
        if not connected:
            self.timeout_add(1, self._start_control())
            return

        self._check_server()

        if self.enable_mpris2:
            self.mpris = SnapMprisPlayer(
                "org.mpris.MediaPlayer2.QtileSnapcastWidget", self.control, self
            )
            if self._proc is not None:
                self.start_mpris2()

    def on_server_connection_lost(self, _params):
        self.stop_mpris2()
        if not self.finalising:
            create_task(self._start_control())
            self.draw()

    def on_update(self, _params):
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

        # Sometimes we get a client connect event but client doesn't appear in list of
        # groups. Therefore, there won't always be a new notification so, if we can't find
        # our client, we should poll intermittently to check if it appears in a group.
        if stream is None:
            self.timeout_add(self.server_reconnect_interval, self._check_server)

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

        if self.stream and (self.control is not None and self.control.connected):
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
        if self.mpris is None:
            return

        task = create_task(self.mpris.start())
        task.add_done_callback(self._mpris_started)

    def _mpris_started(self, task):
        if not task.result():
            logger.warning("Could not start mpris interface for snapcast.")

    def stop_mpris2(self):
        if self.mpris is not None:
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
        self.draw_at_default_position()

    def finalize(self):
        self.finalising = True
        if self._proc:
            self._proc.terminate()
        base._Widget.finalize(self)

    @expose_command
    def show_stream_options(
        self,
        x=None,
        y=None,
        centered=False,
        warp_pointer=False,
        relative_to=1,
        relative_to_bar=False,
        hide_on_timeout=None,
    ):
        """Show a menu to change group/stream."""
        if not (self.snapclient_id and self.stream):
            return

        item = self.create_menu_item
        sep = self.create_menu_separator

        current_group = [g for g in self.groups if self.snapclient_id in g]
        other_groups = [g for g in self.groups if self.snapclient_id not in g]

        if not current_group:
            return
        menu = []

        cg = current_group[0]
        other_clients = [c for c in cg.clients if c != self.snapclient_id]
        menu.append(item(text=f"Currently listening to:\n{cg.stream}", row_span=4))
        if other_clients:
            menu.append(
                item(
                    text=("Synced with:\n" f"{', '.join(c.name for c in other_clients)}"),
                    row_span=4,
                )
            )
        menu.append(sep())

        if other_groups:
            menu.append(item(text="Join other group:"))
            for group in other_groups:
                menu.append(
                    item(
                        text=(
                            f"Listening to:\n{group.stream}\n"
                            f"Synced with {', '.join(c.name for c in group.clients)}"
                        ),
                        row_span=5,
                        mouse_callbacks={"Button1": lambda g=group: self._switch_group(g)},
                    )
                )

        if len(cg.clients) > 1:
            menu.append(
                item(
                    text="Move client to new group",
                    mouse_callbacks={"Button1": lambda g=cg: self._move_to_new_group(g)},
                )
            )

        menu.append(sep())

        other_streams = [s for s in self.streams if s.id != self.stream]
        if other_streams:
            menu.append(item(text="Change group stream:"))
            for stream in other_streams:
                menu.append(
                    item(
                        text=stream.id,
                        mouse_callbacks={
                            "Button1": lambda s=stream, g=current_group[0]: self._switch_stream(
                                s, g
                            )
                        },
                    )
                )

        self.display_menu(
            menu,
            x=x,
            y=y,
            centered=centered,
            warp_pointer=warp_pointer,
            relative_to=relative_to,
            relative_to_bar=relative_to_bar,
            hide_on_timeout=hide_on_timeout,
        )

    def _switch_group(self, group):
        params = {"clients": [c.id for c in group.clients] + [self.snapclient_id], "id": group.id}
        self.control.send(GROUP_SETCLIENTS, params=params)
        self._check_server()

    def _move_to_new_group(self, current_group):
        params = {
            "clients": [c.id for c in current_group.clients if c.id != self.snapclient_id],
            "id": current_group.id,
        }
        self.control.send(GROUP_SETCLIENTS, params=params)
        self._check_server()

    def _switch_stream(self, stream, group):
        params = {"stream_id": stream.id, "id": group.id}
        self.control.send(GROUP_SETSTREAM, params=params)
        self._check_server()
