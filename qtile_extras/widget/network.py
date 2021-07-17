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

import asyncio
import math

from dbus_next.aio import MessageBus
from dbus_next.constants import BusType
from dbus_next.errors import DBusError

from libqtile import bar
from libqtile.images import Img
from libqtile.log_utils import logger
from libqtile.utils import hex
from libqtile.widget import base

PI = math.pi

WIFI_ARC_DEGREES = 75

CONNECTION_WIFI = 1
CONNECTION_WIRED = 2

STATUS_DISCONNECTED = 0
STATUS_DISCONNECTING = 1
STATUS_CONNECTING = 2
STATUS_CONNECTED = 3


# A basic ethernet icon in SVG format. Needs to be formatted to set "colour" value
ETHERNET_ICON = """
<svg width="64" height="64" viewBox="0 0 16.933333 16.933334">
  <g>>
    <path
       id="ethernet"
       style="fill:none;stroke:{colour};stroke-width:1.5;stroke-miterlimit:4;stroke-dasharray:none"
       d="m 2.0972881,3.4124532 v 8.1354208 h 3.602881 v 1.973006 h 5.5329959 v -1.973006 h 3.60288 V 3.4124532 Z" />
  </g>
</svg>
"""


def to_rads(degrees):
    return degrees * PI / 180.0


class NetworkConnection:
    """
    Base network connection object. Defines the attributes that the widget
    expects to see.
    """
    def __init__(self, callback=None, connection_type=CONNECTION_WIFI, name="", strength=0, status=STATUS_DISCONNECTED):
        self.callback = callback
        self.connection_type = connection_type
        self._name = name
        self._strength = strength
        self._status = status

    @property
    def is_wifi(self):
        return self.connection_type == CONNECTION_WIFI

    @property
    def is_wired(self):
        return self.connection_type == CONNECTION_WIRED

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        oldvalue = self._name
        self._name = value
        if value != oldvalue and self.callback:
            self.callback()

    @property
    def strength(self):
        return self._strength

    @strength.setter
    def strength(self, value):
        oldvalue = self._strength
        self._strength = value
        if value != oldvalue and self.callback:
            self.callback()

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        oldvalue = self._status
        self._status = value
        if value != oldvalue and self.callback:
            self.callback()


class BackendBase:
    """
    Base network backend object.

    A new backend should be defined for the various systems available
    e.g. NetworkManager, iwd, systemd-networkd
    """
    def __init__(self, parent, *args, **kwargs):
        self.parent = parent

    def _configure(self):
        pass

    async def _config_async(self):
        pass

    def poll(self):
        pass


class IWD(BackendBase):
    _status_map = {
        "disconnected": STATUS_DISCONNECTED,
        "disconnecting": STATUS_DISCONNECTING,
        "connecting": STATUS_CONNECTING,
        "connected": STATUS_CONNECTED
    }

    def __init__(self, parent, *args, **kwargs):
        BackendBase.__init__(self, parent, *args, **kwargs)
        self.connection = None

    async def _config_async(self):
        self.bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        self.path = None

        # Find station
        base = self.bus.get_proxy_object(
            "net.connman.iwd",
            "/",
            await self.bus.introspect("net.connman.iwd", "/")
        )

        objman = base.get_interface("org.freedesktop.DBus.ObjectManager")
        objs = await objman.call_get_managed_objects()

        for path in objs:
            if "net.connman.iwd.Station" in objs[path]:
                self.path = path
                break
        else:
            logger.info("Cannot find iwd station on dbus.")

        if self.path:
            await self.get_station()
            await self.get_status()
            task = asyncio.create_task(self.update_connection())
            task.add_done_callback(self.connection_updated)

    async def get_station(self):
        base = self.bus.get_proxy_object(
            "net.connman.iwd",
            self.path,
            await self.bus.introspect("net.connman.iwd", self.path)
        )

        self.station = base.get_interface("net.connman.iwd.Station")
        self.diagnostics = base.get_interface("net.connman.iwd.StationDiagnostic")
        self._props = base.get_interface("org.freedesktop.DBus.Properties")

        self._props.on_properties_changed(self._state_changed)
        self.connection = NetworkConnection(
            callback=self.parent.update,
            connection_type=CONNECTION_WIFI
        )
        status = await self.station.get_state()
        self.connection.status = self._status_map.get(status, STATUS_DISCONNECTED)

    async def get_status(self):
        pass

    def _state_changed(self, interface, properties, invalidated):
        if "State" in properties:
            state = properties["State"].value
            status = self._status_map.get(state, STATUS_DISCONNECTED)
            self.connection.status = status

            if status in [STATUS_CONNECTED, STATUS_CONNECTING]:
                task = asyncio.create_task(self.update_connection())
                task.add_done_callback(self.connection_updated)
                self.poll()

    async def update_connection(self):
        path = await self.station.get_connected_network()
        obj = self.bus.get_proxy_object(
            "net.connman.iwd",
            path,
            await self.bus.introspect("net.connman.iwd", path)
        )
        network = obj.get_interface("net.connman.iwd.Network")
        return await network.get_name()

    def connection_updated(self, task):
        network = task.result()
        self.connection.name = network

    async def get_diagnostics(self):
        try:
            return await self.diagnostics.call_get_diagnostics()
        except DBusError:
            return None

    def update_diagnostics(self, task):
        diags = task.result()
        if diags is not None:
            strength = min((getattr(diags.get("RSSI"), "value", -100) + 100) * 2, 100)
            self.connection.strength = strength

    def poll(self):
        task = asyncio.create_task(self.get_diagnostics())
        task.add_done_callback(self.update_diagnostics)

    @property
    def connections(self):
        return [self.connection]


class NetworkManager(BackendBase):
    NM_DEVICE_ETHERNET = "ethernet"
    NM_DEVICE_WIFI = "wifi"
    NM_DEVICE_VPN = "vpn"
    NM_INTERFACE = ".NetworkManager"
    NM_CONNECTIVITY_UNKNOWN = 0
    NM_CONNECTIVITY_NONE = 1
    NM_CONNECTIVITY_PORTAL = 2
    NM_CONNECTIVITY_LIMITED = 3
    NM_CONNECTIVITY_FULL = 4


class NetworkWidget(base._Widget, base.PaddingMixin):
    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("font", "sans", "Default font"),
        ("fontsize", None, "Font size"),
        ("active_colour", "ffffff", "Colour for wifi strength and ethernet indicator."),
        ("inactive_colour", "666666", "Colour for wifi background and inactive ethernet indicator."),
        ("error_colour", "ffff00", "Error indicator text colour"),
        ("update_interval", None, "Polling interval in secs. 'None' to listen for dbus events only."),
        ("backend", "iwd", "Network manager. Available choices: iwd, networkmanager."),
        ("wifi_arc", 75, "Width of arc in degrees")
    ]

    _managers = {
        "iwd": IWD,
        "networkmanager": NetworkManager
    }

    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)
        self.add_defaults(NetworkWidget.defaults)
        self.add_defaults(base.PaddingMixin.defaults)
        self.connections = []
        self.wifi_width = 0
        self.show_text = False
        self.hide_timer = None
        self.images = {}

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)

        self.set_sizes()
        self.prepare_images()

        manager = self._managers.get(self.backend, None)
        if manager is None:
            logger.warning("Invalid backend supplied. Network widget unavailable.")
            return
        self.manager = manager(self)
        self.manager._configure()
        self.qtile.call_soon(asyncio.create_task, self.manager._config_async())
 
        if self.update_interval:
            self.timeout_add(self.update_interval, self.loop)

    def loop(self):
        self.timeout_add(self.update_interval, self.loop)
        self.manager.poll()

    def draw_connections(self):
        offset = self.padding_x

        for connection in self.manager.connections:
            if connection is None:
                return
            if connection.is_wifi:
                self.draw_wifi(offset, connection.strength)
                offset += self.wifi_width + self.padding_x

                if self.show_text:
                    layout = self.get_wifi_text(connection)
                    layout.draw(offset, int((self.height - layout.height)/2))
                    offset += layout.width + self.padding_x

            else:
                self.draw_wired(offset)
                offset += self.padding_x + self.icon_size

        if not self.manager.connections:
            self.draw_wifi(offset, 0)

    def draw_wifi(self, offset, strength):
        percentage = strength / 100.0

        half_arc = self.wifi_arc / 2
        x_offset = int(self.wifi_height * math.sin(to_rads(half_arc)))

        self.drawer.ctx.new_sub_path()
        self.drawer.ctx.move_to(offset+x_offset, self.padding_y + self.wifi_height)
        self.drawer.ctx.arc(offset+x_offset,
                            self.padding_y + self.wifi_height,
                            self.wifi_height,
                            to_rads(270 - half_arc),
                            to_rads(270 + half_arc))
        self.drawer.set_source_rgb(self.inactive_colour)
        self.drawer.ctx.fill()

        self.drawer.ctx.new_sub_path()
        self.drawer.ctx.move_to(offset+x_offset, self.padding_y + self.wifi_height)
        self.drawer.ctx.arc(offset+x_offset,
                            self.padding_y + self.wifi_height,
                            self.wifi_height * percentage,
                            to_rads(270 - half_arc),
                            to_rads(270 + half_arc))
        self.drawer.set_source_rgb(self.active_colour)
        self.drawer.ctx.fill()

    def draw_wired(self, offset):
        self.drawer.ctx.translate(offset, self.padding_y)
        self.drawer.ctx.set_source(self.images["lan-inactive"])
        self.drawer.ctx.paint()
        self.drawer.ctx.translate(-offset, -self.padding_y)

    def draw_error(self, offset):
        layout = self.drawer.textlayout("!",
                                        self.error_colour,
                                        self.font,
                                        self.fontsize,
                                        None,
                                        wrap=False)

        layout.width = self.wifi_width
        y_offset = int((self.bar.height - layout.height) / 2)
        layout.draw(offset, y_offset)

    def draw(self):
        if not self.configured:
            return

        self.update_count = 0

        self.drawer.clear(self.background or self.bar.background)
        self.draw_connections()
        self.drawer.draw(offsetx=self.offset, width=self.length)

    def update(self):
        if self.update_count == 0:
            self.update_count += 1
            self.timeout_add(1, self.draw)

    def set_sizes(self):
        self.wifi_height = self.bar.height - (self.padding_y * 2)
        self.wifi_width = (self.wifi_height * math.sin(to_rads(self.wifi_arc / 2))) * 2
        self.wifi_width = math.ceil(self.wifi_width)

        self.icon_size = self.wifi_height

    def get_wifi_text(self, connection, size_only=False):
        text = "{} ({}%)"
        s = connection.strength
        text = text.format(connection.name, s)

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

        for connection in self.manager.connections:
            width += self.padding_x

            if connection is None:
                width += self.wifi_width

            elif connection.is_wired:
                width += self.icon_size

            else:
                width += self.wifi_width
                if connection.is_wifi and self.show_text:
                    width += (self.padding_x +
                              self.get_wifi_text(connection,
                                                 size_only=True))

        if not self.manager.connections:
            width += self.padding_x + self.wifi_width

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

        self.hide_timer = self.timeout_add(5, self.hide)

    def hide(self):
        self.show_text = False
        self.bar.draw()

    def prepare_images(self):
        temp = {}
        active = ETHERNET_ICON.format(colour=hex(self.active_colour))
        inactive = ETHERNET_ICON.format(colour=hex(self.inactive_colour))
        temp["lan-active"] = Img(active.encode(), name="lan-active")
        temp["lan-inactive"] = Img(inactive.encode(), name="lan-inactive")
        for key, img in temp.items():
            img.resize(height=self.icon_size)
            self.images[key] = img.pattern
