# Copyright (c) 2023 elParaguayo
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
import contextlib
import shutil

from dbus_next.aio import MessageBus
from dbus_next.constants import BusType
from dbus_next.errors import DBusError, InterfaceNotFoundError
from dbus_next.service import ServiceInterface, method
from libqtile.command.base import expose_command
from libqtile.log_utils import logger
from libqtile.utils import create_task
from libqtile.widget import base

from qtile_extras.widget.mixins import ConnectionCheckMixin, GraphicalWifiMixin, MenuMixin

IWD_SERVICE = "net.connman.iwd"
IWD_DEVICE = IWD_SERVICE + ".Device"
IWD_STATION = IWD_SERVICE + ".Station"
IWD_STATION_DIAGNOSTIC = IWD_SERVICE + ".StationDiagnostic"
IWD_NETWORK = IWD_SERVICE + ".Network"
IWD_MANAGER = IWD_SERVICE + ".AgentManager"
OBJECT_MANAGER_INTERFACE = "org.freedesktop.DBus.ObjectManager"
PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"


def retry(message, retries=10, interval=0.5, exceptions=list(), check_interface=""):
    retries = max(retries, 1)
    exceptions = tuple([DBusError, BlockingIOError] + exceptions)

    def _wrapper(func):
        async def f(self, *args, **kwargs):
            count = 0
            while True:
                try:
                    return await func(self, *args, **kwargs)
                except exceptions as e:
                    if count < retries:
                        await asyncio.sleep(interval)
                        count += 1
                    else:
                        if check_interface:
                            proxy = await self._widget.get_proxy(self.path)
                            try:
                                proxy.get_interface(check_interface)
                            except InterfaceNotFoundError:
                                return False

                        logger.exception("%s (%s).", message, e)  # noqa: G200
                        return False

        return f

    return _wrapper


class Cancelled(DBusError):
    def __init__(self, msg):
        DBusError.__init__(self, "net.connman.iwd.Error.Canceled", msg)


class ConnectionAgent(ServiceInterface):  # noqa: E303
    ID = 0

    def __init__(self, *args, path="", widget=None, password_cmd=list()):
        self.path = path
        self.widget = widget
        self.password_cmd = password_cmd
        self.proc = None
        ServiceInterface.__init__(self, *args)

    async def _get_password(self):
        self.proc = await asyncio.create_subprocess_exec(
            *self.password_cmd,
            stdout=asyncio.subprocess.PIPE,
        )
        stdout, _ = await self.proc.communicate()

        returncode = self.proc.returncode
        self.proc = None

        if returncode:
            raise Cancelled("Password entry cancelled.")

        return stdout.decode().strip()

    @method()
    async def Release(self) -> None:  # noqa: N802
        await self.widget.manager.call_unregister_agent(self.path)

    @method()
    async def RequestPassphrase(self, path: "o") -> "s":  # type:ignore  # noqa: N802, F821
        return await self._get_password()

    @method()
    async def RequestPrivateKeyPassphrase(  # noqa: N802
        self, path: "o"  # type:ignore  # noqa: F821
    ) -> "s":  # type:ignore  # noqa: F821
        return await self._get_password()

    @method()
    def Cancel(self, reason: "s") -> None:  # type:ignore  # noqa: N802, F821
        logger.warning("Agent cancelled: %s.", reason)
        if self.proc is not None:
            self.proc.terminate()
            self.proc = None


class Device:
    """Represents a wireless device."""

    def __init__(self, widget, path, bus, callback=None):
        self._widget = widget
        self.path = path
        self.bus = bus
        self.name = "<unknown wirelesss device>"
        self.powered = False
        self.scanning = False
        self.state = ""
        self.connected_network = ""
        self.callback = callback
        self.rssi = 0
        self.quality = 0

    def __del__(self):
        if hasattr(self, "properties"):
            with contextlib.suppress(RuntimeError):
                self.properties.off_properties_changed(self._update_properties)

    @retry("Unable to connect to wireless device.")
    async def setup(self):
        device_introspection = await self.bus.introspect(IWD_SERVICE, self.path)
        proxy = self.bus.get_proxy_object(IWD_SERVICE, self.path, device_introspection)
        self.device = proxy.get_interface(IWD_DEVICE)
        self.station = proxy.get_interface(IWD_STATION)
        self.diagnostics = proxy.get_interface(IWD_STATION_DIAGNOSTIC)
        self.properties = proxy.get_interface(PROPERTIES_INTERFACE)
        self.properties.on_properties_changed(self._update_properties)
        return await self.get_properties()

    def _update_properties(self, interface, changed_properties, _invalidated_properties):
        needs_callback = False
        if "Scanning" in changed_properties:
            self.scanning = changed_properties["Scanning"].value
            needs_callback = True

        if "ConnectedNetwork" in changed_properties:
            self.connected_network = changed_properties["ConnectedNetwork"].value
            needs_callback = True

        if "State" in changed_properties:
            self.state = changed_properties["State"].value
            needs_callback = True

        if needs_callback and self.callback:
            self.callback()

    @retry("Unable to get wireless device properties")
    async def get_properties(self):
        self.name, self.powered, self.state = await asyncio.gather(
            self.device.get_name(), self.device.get_powered(), self.station.get_state()
        )
        try:
            self.connected_network = await self.station.get_connected_network()
        except DBusError:
            self.connected_network = ""
        return True

    @retry(
        "Unable to get signal strength",
        retries=5,
        interval=0.1,
        check_interface=IWD_STATION_DIAGNOSTIC,
    )
    async def get_signal_strength(self):
        diagnostics = await self.diagnostics.call_get_diagnostics()
        self.rssi = diagnostics["RSSI"].value
        self.quality = min(max(2 * (self.rssi + 100), 0), 100)

    @retry("Unable to start scan", retries=5, interval=0.1)
    async def scan(self):
        await self.station.call_scan()


class Network:
    """Represents a wireless network."""

    def __init__(self, widget, path, bus, callback=None):
        self._widget = widget
        self.path = path
        self.bus = bus
        self.name = ""
        self.known = False
        self.callback = callback
        self.type = ""

    @retry("Unable to connect to get network details.")
    async def setup(self):
        device_introspection = await self.bus.introspect(IWD_SERVICE, self.path)
        proxy = self.bus.get_proxy_object(IWD_SERVICE, self.path, device_introspection)
        self.network = proxy.get_interface(IWD_NETWORK)
        self.properties = proxy.get_interface(PROPERTIES_INTERFACE)
        self.properties.on_properties_changed(self._update_properties)
        return await self.get_properties()

    @retry("Unable to get network properties")
    async def get_properties(self):
        self.name, self.connected, self.type = await asyncio.gather(
            self.network.get_name(), self.network.get_connected(), self.network.get_type()
        )
        try:
            self.known = bool(await self.network.get_known_network())
        except DBusError:
            self.known = False
        return True

    def _update_properties(self, interface, changed_properties, _invalidated_properties):
        needs_callback = False
        if "Connected" in changed_properties:
            self.connected = changed_properties["Connected"].value
            needs_callback = True

        if "KnownNetwork" in changed_properties:
            self.known = bool(changed_properties["KnownNetwork"].value)
            needs_callback = True

        if "Name" in changed_properties:
            self.name = changed_properties["Name"].value
            needs_callback = True

        if needs_callback and self.callback:
            self.callback()

    async def connect(self):
        await self.network.call_connect()


class IWD(base._TextBox, base.MarginMixin, MenuMixin, GraphicalWifiMixin, ConnectionCheckMixin):
    """
    This widget provides information about your wireless connection using iwd.

    The widget also allows you to scan for and connect to different networks.
    If the network is unknown (i.e. you haven't connected to it before), the widget
    will launch a window to enter the password (using zenity by default).

    NB you cannot join 802.1x networks unless they have already been configured.
    """

    _experimental = True

    defaults = [
        (
            "interface",
            None,
            "Name of wireless interface. You should only need to set this if you have more than "
            "one wireless adapter on your system.",
        ),
        ("update_interval", 2, "Polling interval in seconds."),
        ("password_entry_app", "zenity", "Application for password entry."),
        (
            "password_entry_args",
            ["--entry", "--text", "Enter password:", "--hide-text"],
            "Additional args to pass to password entry command.",
        ),
        ("format", "{ssid} ({quality}%)", "Text format. Available fields: ssid, rssi, quality"),
        ("show_text", True, "Displays text in bar."),
        ("show_image", False, "Shows a graphical representation of signal strength."),
        ("active_colour", "ffffff", "Colour for wifi strength."),
        ("inactive_colour", "666666", "Colour for wifi background."),
        ("scanning_colour", "3abb3a", "Colour to use for image when scanning is active."),
    ]

    def __init__(self, **config):
        base._TextBox.__init__(self, **config)
        self.add_defaults(MenuMixin.defaults)
        self.add_defaults(GraphicalWifiMixin.defaults)
        self.add_defaults(ConnectionCheckMixin.defaults)
        self.add_defaults(IWD.defaults)
        self.add_defaults(base.MarginMixin.defaults)
        MenuMixin.__init__(self, **config)
        GraphicalWifiMixin.__init__(self)
        ConnectionCheckMixin.__init__(self)
        self.bus = None
        self.device = None
        self.networks = {}
        self.devices = {}
        self._device_tasks = []
        self._network_tasks = []
        self.timer = None
        self._setting_up = False
        self.add_callbacks({"Button1": self.show_networks})
        self._can_connect = False
        self.percentage = 0
        self._refresh_timer = None

    def _configure(self, qtile, bar):
        base._TextBox._configure(self, qtile, bar)
        self.set_wifi_sizes()
        ConnectionCheckMixin._configure(self)

    def calculate_length(self):
        width = 0
        text_width = base._TextBox.calculate_length(self)
        image_width = self.wifi_width + 2 * self.actual_padding

        if self.show_text:
            width += text_width

        if self.show_image:
            width += image_width
            if self.show_text:
                width -= self.actual_padding

        return width

    async def _config_async(self):
        await self._connect()

    async def _connect(self):
        """Connect to bus and set up key listeners."""
        self.bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

        # Get the object manager
        device_introspection = await self.bus.introspect(IWD_SERVICE, "/")
        proxy = self.bus.get_proxy_object(IWD_SERVICE, "/", device_introspection)
        self.object_manager = proxy.get_interface(OBJECT_MANAGER_INTERFACE)

        # Subscribe to signals for new and removed interfaces
        self.object_manager.on_interfaces_added(self._interface_added)
        self.object_manager.on_interfaces_removed(self._interface_removed)

        await self._get_managed_objects()

        await self._register_agent()

        self.refresh()

    async def get_proxy(self, path):
        """Provides proxy object after introspecting the given path."""
        device_introspection = await self.bus.introspect(IWD_SERVICE, path)
        proxy = self.bus.get_proxy_object(IWD_SERVICE, path, device_introspection)
        return proxy

    async def _register_agent(self):
        if not self.password_entry_app:
            logger.warning("No password entry app provided. Agent will not be started.")
            return

        if shutil.which(self.password_entry_app) is None:
            logger.warning("Cannot find password entry app. Agent will not be started.")
            return

        args = self.password_entry_args

        if args and not isinstance(args, list):
            logger.warning("password_entry_args must be a list. Agent will not be started.")
            return

        password_cmd = [self.password_entry_app]

        if args:
            password_cmd.extend(args)

        ConnectionAgent.ID += 1
        path = f"/qtile_extras/iwd/agent{ConnectionAgent.ID}"
        agent = ConnectionAgent(
            "net.connman.iwd.Agent", path=path, widget=self, password_cmd=password_cmd
        )
        self.bus.export(path, agent)

        proxy = await self.get_proxy("/net/connman/iwd")
        self.manager = proxy.get_interface(IWD_MANAGER)
        await self.manager.call_register_agent(path)
        self._can_connect = True

    async def _get_managed_objects(self):
        """
        Retrieve list of managed objects.

        These are wireless adapters, known networks and currently visible networks.
        """
        self._setting_up = True

        objects = await self.object_manager.call_get_managed_objects()

        for path, interfaces in objects.items():
            task = self._interface_added(path, interfaces)
            if task is not None:
                if isinstance(task.obj, Device):
                    self._device_tasks.append(task)
                elif isinstance(task.obj, Network):
                    self._network_tasks.append(task)

        if not self.devices:
            logger.warning("No wireless devices found.")
        else:
            await self.find_device()

        if self.device:
            await self.filter_networks()

        self._setting_up = False

    def _interface_added(self, path, interfaces):
        """Handles the object based on the interface type."""
        task = None

        if IWD_DEVICE in interfaces and IWD_STATION in interfaces:
            device = Device(self, path, self.bus, self.refresh)
            self.devices[path] = device
            task = create_task(device.setup())
            task.add_done_callback(self.task_completed)
            task.obj = device

        elif IWD_NETWORK in interfaces:
            network = Network(self, path, self.bus, self.refresh)
            self.networks[path] = network
            task = create_task(network.setup())
            task.add_done_callback(self.task_completed)
            task.obj = network

        return task

    def _interface_removed(self, path, interfaces):
        # Object has been removed so remove from our list of available devices
        updated = False

        if IWD_STATION in interfaces:
            if self.device.path == path:
                self.device = None
                updated = True

        elif IWD_NETWORK in interfaces:
            with contextlib.suppress(KeyError):
                del self.networks[path]
                updated = True

        if updated and not self._setting_up:
            self.refresh()

    async def find_device(self):
        while not all(t.done() for t in self._device_tasks):
            await asyncio.sleep(0.01)

        # Filter out any devices we couldn't set up.
        for t in self._device_tasks:
            if not t.result():
                del self.devices[t.obj.path]

        self._device_tasks.clear()

        if not self.devices:
            logger.warning("Couldn't set up any wireless devices.")
            return

        # Look for named device
        if self.interface is not None:
            for device in self.devices.values():
                if device.name == self.interface:
                    self.device = device
                    break
            else:
                logger.warning("The interface '%s' was not found.", self.interface)

            return

        # Look for connected device
        for device in self.devices.values():
            if device.state == "connected":
                self.device = device
                return

        # Look for powered device
        for device in self.devices.values():
            if device.powered:
                self.device = device
                return

        logger.warning("No connected or powered devices found.")

    async def filter_networks(self):
        while not all(t.done() for t in self._network_tasks):
            await asyncio.sleep(0.01)

        for t in self._network_tasks:
            if not t.result() or self.device.path not in t.obj.path:
                del self.devices[t.obj.path]

        self._network_tasks.clear()

    def task_completed(self, task):
        if not self._setting_up:
            self.refresh()

    def get_stats(self):
        task = create_task(self.device.get_signal_strength())
        self._refresh_timer = None
        task.add_done_callback(self.refresh)

    def refresh(self, *args):
        old_width = self.layout.width

        if self.device is None:
            self.text = "Error"
            self.percentage = 0

        else:
            self.text = self.format.format(
                ssid=self.networks[self.device.connected_network].name,
                quality=self.device.quality,
                rssi=self.device.rssi,
            )
            self.percentage = self.device.quality / 100.0

        if old_width != self.layout.width:
            self.bar.draw()
        else:
            self.draw()

        # We only want to set a new timer if the previous timer has run
        # Refresh() can be called by callbacks from the dbus objects
        # so we clear the timer in get_stats which is only called by the timer
        if self._refresh_timer is None:
            self._refresh_timer = self.timeout_add(self.update_interval, self.get_stats)

    def draw(self):
        if not self.can_draw:
            return

        self.drawer.clear(self.background or self.bar.background)
        offset = self.wifi_padding_x
        if self.show_image:
            if self.device is not None and self.device.scanning:
                foreground = self.scanning_colour
            elif not self.is_connected:
                foreground = self.disconnected_colour
            else:
                foreground = self.active_colour
            self.draw_wifi(
                self.percentage, foreground=foreground, background=self.inactive_colour
            )
            offset += self.wifi_width + self.wifi_padding_x

        if self.show_text:
            self.layout.draw(offset, int(self.bar.height / 2.0 - self.layout.height / 2.0) + 1)

        self.drawer.draw(
            offsetx=self.offsetx, offsety=self.offsety, width=self.width, height=self.height
        )

    def _get_menu_items(self):
        menu_items = []
        pmi = self.create_menu_item
        pms = self.create_menu_separator

        if self.device.connected_network:
            # We can get a KeyError here if the deivce was suspended while connected
            # nut resumed when the network is no longer visible.
            try:
                name = self.networks[self.device.connected_network].name
            except KeyError:
                self.device.connected_network = ""
            else:
                menu_items.extend(
                    [
                        pmi("Connected to:"),
                        pmi(name),
                        pms(),
                    ]
                )

        networks = []

        for path, network in self.networks.items():
            if path == self.device.connected_network:
                continue

            def connect(n):
                task = create_task(n.connect())
                task.add_done_callback(self.connect_response)

            enabled = (self._can_connect and not network.type == "8021x") or network.known

            item = pmi(
                f"{network.name} ({network.type})",
                mouse_callbacks={"Button1": lambda n=network: connect(n)} if enabled else {},
                enabled=enabled,
            )
            networks.append(item)

        if networks:
            networks.insert(0, pmi("Visible networks:"))
            networks.append(pms())
            menu_items.extend(networks)

        if self.device.scanning:
            device_item = pmi("Scanning...", enabled=False)
        else:
            device_item = pmi(
                "Scan for networks",
                mouse_callbacks={"Button1": self.scan},
            )

        menu_items.append(device_item)

        return menu_items

    def connect_response(self, task):
        exc = task.exception()
        if exc is not None:
            if isinstance(exc, Cancelled):
                logger.info("Password entry cancelled.")
            else:
                logger.warning("Could not connect: %s", exc)

    @expose_command
    def show_networks(
        self,
        x=None,
        y=None,
        centered=False,
        warp_pointer=False,
        relative_to=1,
        relative_to_bar=False,
        hide_on_timeout=None,
    ):
        """Show menu with available networks."""
        self.display_menu(
            menu_items=self._get_menu_items(),
            x=x,
            y=y,
            centered=centered,
            warp_pointer=warp_pointer,
            relative_to=relative_to,
            relative_to_bar=relative_to_bar,
            hide_on_timeout=hide_on_timeout,
        )

    @expose_command
    def scan(self):
        if self.device:
            task = create_task(self.device.scan())
            task.add_done_callback(self._check_scan)

    def _check_scan(self, task):
        if task.exception():
            logger.warning("Unable to trigger scan of networks.")

    def finalize(self):
        self.bus.disconnect()
        base._TextBox.finalize(self)
