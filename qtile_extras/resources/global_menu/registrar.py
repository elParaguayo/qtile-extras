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
from __future__ import annotations

import asyncio
import pickle
from pathlib import Path
from typing import TYPE_CHECKING

from dbus_next import Message
from dbus_next.aio import MessageBus
from dbus_next.constants import MessageType, PropertyAccess
from dbus_next.service import ServiceInterface, dbus_property, method, signal
from libqtile.core.lifecycle import lifecycle
from libqtile.log_utils import logger
from libqtile.utils import create_task

if TYPE_CHECKING:
    from typing import Callable

GLOBAL_MENU_INTERFACE = "com.canonical.AppMenu.Registrar"
GLOBAL_MENU_PATH = "/com/canonical/AppMenu/Registrar"
MENU_INTERFACE = "com.canonical.dbusmenu"
NO_MENU = "/NO_DBUSMENU"

REGISTRAR_CACHE = Path("/tmp/qtile-extras/global-menu-cache")

lock = asyncio.Lock()


class GlobalMenuRegistrar(ServiceInterface):  # noqa: E303
    """
    DBus service that creates a Global Menu service interface
    on the bus and listens for applications wanting to register.
    """

    def __init__(self):
        super().__init__(GLOBAL_MENU_INTERFACE)
        self.windows = {}
        self.pids = {}
        self.started = False
        self.callbacks = []
        self.previously_registered = set()
        self._finalized = False

    async def start(self):
        # We take a lock here as, otherwise, there's a potential race
        # condition and we only want to start the registrar once.
        async with lock:
            if not self.started:
                self.bus = await MessageBus().connect()
                self.bus.export(GLOBAL_MENU_PATH, self)
                await self.bus.request_name(GLOBAL_MENU_INTERFACE)

                # We're going to use a message handler to register windows
                self.bus.add_message_handler(self._message_handler)

                # Load previously saved state
                self.load_state()

                self.started = True

    async def get_service_pid(self, wid, sender, path):
        msg = await self.bus.call(
            Message(
                message_type=MessageType.METHOD_CALL,
                destination="org.freedesktop.DBus",
                interface="org.freedesktop.DBus",
                path="/org/freedesktop/DBus",
                member="GetConnectionUnixProcessID",
                signature="s",
                body=[sender],
            )
        )

        if msg.message_type == MessageType.METHOD_RETURN:
            pid = msg.body[0]
            self.pids[pid] = (sender, path)

    def _message_handler(self, message):
        """Low-level message handler to retrieve sender and body of messages."""
        # Filter out messages that aren't calls to RegisterWindow
        if not (message.member == "RegisterWindow"):
            return False

        # Extract the key bits of info
        sender = message.sender
        wid = message.body[0]
        path = message.body[1]

        # If we've already registered this window but with a different interface
        # then we need to let attached clients know so they can re-request menus
        # as necessary
        for callback in self.callbacks:
            callback(wid)

        self.windows[wid] = [sender, path]

        # Wayland windows don't really have an ID so we can try to match service to the PID
        create_task(self.get_service_pid(wid, sender, path))

        self.previously_registered.add(wid)
        self.WindowRegistered(wid)

        return False

    @method()
    def RegisterWindow(self, windowId: "u", menuObjectPath: "o"):  # type: ignore  # noqa: F821, N802, N803
        # This is silly, the spec says that apps should only provide
        # windowId and menuObjectPath but we need to be able to return
        # the host service too but this isn't explicityly provided
        # and dbus-next's high-level service doesn't expose this part of
        # the message. So... we expose the method here but don't do anything
        # with it. We actually deal with the call in a low-level message
        # handler, self._message_handler.
        pass

    @method()
    def UnregisterWindow(self, windowId: "u"):  # type: ignore  # noqa: F821, N802, N803
        if windowId in self.windows:
            del self.windows[windowId]
            self.WindowUnregistered(windowId)

    @method()
    def GetMenuForWindow(self, windowId: "u") -> "so":  # type: ignore  # noqa: F821, N802, N803
        return self.get_menu(windowId)

    @dbus_property(access=PropertyAccess.READ)
    def RegisteredWindows(self) -> "au":  # type: ignore  # noqa: F821, N802
        return list(self.windows.keys())

    @signal()
    def WindowRegistered(self, windowId: int) -> "uso":  # type: ignore  # noqa: F821, N802, N803
        return [windowId, *self.get_menu(windowId)]

    @signal()
    def WindowUnregistered(self, windowId: int) -> "u":  # type: ignore  # noqa: F821, N802, N803
        return windowId

    def get_menu(self, window_id):
        if window_id in self.windows:
            return self.windows[window_id]

    def get_menu_by_pid(self, pid):
        if pid in self.pids:
            return self.pids[pid]

    def add_callback(self, callback: Callable):
        self.callbacks.append(callback)

        # Let subscribed clients know about any windows that may already be registered
        for wid in self.windows:
            callback(wid)

    def remove_callback(self, callback: Callable):
        try:
            self.callbacks.remove(callback)
        except ValueError:
            pass

    def window_closed(self, wid):
        if wid in self.windows:
            del self.windows[wid]
        if wid in self.previously_registered:
            self.previously_registered.remove(wid)

    def load_state(self):
        try:
            with open(REGISTRAR_CACHE, "rb") as f:
                self.windows.update(pickle.load(f))
        except FileNotFoundError:
            return

        REGISTRAR_CACHE.unlink()

    def dump_state(self):
        try:
            REGISTRAR_CACHE.parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            logger.warning("Unable to cache current state. Menus may not work after restart.")

        with open(REGISTRAR_CACHE, "wb") as f:
            pickle.dump(self.windows, f)

    def finalize(self):
        # Don't finalize if it's already finalized or there are still subscribed callbacks
        if self._finalized or self.callbacks:
            return
        self._finalized = True

        # If we're not terminating then we want to preserve details of registered windows
        if lifecycle.behavior != lifecycle.behavior.TERMINATE:
            if self.windows:
                self.dump_state()

        # If not, let's shut things down and unregister windows
        else:
            for wid in self.windows.copy():
                del self.windows[wid]
                self.WindowUnregistered(wid)

            if REGISTRAR_CACHE.is_file():
                REGISTRAR_CACHE.unlink()


registrar = GlobalMenuRegistrar()
