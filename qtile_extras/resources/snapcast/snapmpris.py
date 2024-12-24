# Copyright (c) 2024 elParaguayo
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

from dbus_fast import Variant
from dbus_fast.aio import MessageBus
from dbus_fast.constants import PropertyAccess
from dbus_fast.errors import DBusError
from dbus_fast.service import ServiceInterface, dbus_property, method, signal


class SnapMpris(ServiceInterface):
    def __init__(self, widget):
        super().__init__("org.mpris.MediaPlayer2")
        self.widget = widget

    @method()
    def Raise(self):
        pass

    @method()
    def Quit(self):
        self.widget.stop()

    @dbus_property(access=PropertyAccess.READ)
    def CanQuit(self) -> b:
        return True

    @dbus_property()
    def Fullscreen(self) -> b:
        return False

    @Fullscreen.setter
    def Fullscreen(self, fullscreen: b):
        raise DBusError("PropertyError", "Can't set player fullscreen status.")

    @dbus_property(access=PropertyAccess.READ)
    def CanSetFullscreen(self) -> b:
        return False

    @dbus_property(access=PropertyAccess.READ)
    def CanRaise(self) -> b:
        return False

    @dbus_property(access=PropertyAccess.READ)
    def HasTrackList(self) -> b:
        return False

    @dbus_property(access=PropertyAccess.READ)
    def Identity(self) -> s:
        return "qtile-snapcast-widget"

    @dbus_property(access=PropertyAccess.READ)
    def DesktopEntry(self) -> s:
        return ""

    @dbus_property(access=PropertyAccess.READ)
    def SupportedUriSchemes(self) -> "as":
        return []

    @dbus_property(access=PropertyAccess.READ)
    def SupportedMimeTypes(self) -> "as":
        return []


class SnapMprisPlayer(ServiceInterface):
    def __init__(self, service_name, control, widget):
        super().__init__("org.mpris.MediaPlayer2.Player")
        self.control = control
        self.bus = None
        self.service_name = service_name
        self._error = None
        self.widget = widget

    async def start(self):
        try:
            self.bus = await MessageBus().connect()
        except Exception as e:  # ugly but "connect" passes through all errors
            self._error = e
            return False

        self.control.subscribe(self.on_message)
        self.bus.export("/org/mpris/MediaPlayer2", SnapMpris(self.widget))
        self.bus.export("/org/mpris/MediaPlayer2", self)
        await self.bus.request_name(self.service_name)
        self.control.send("Plugin.Stream.Player.GetProperties", callback=self._get_props)
        return True

    def _get_props(self, result):
        print(result)

    def on_message(self, message):
        if "method" in message:
            self._on_notification(message)

    def _on_notification(self, message):
        params = message["params"]

        match message["method"]:
            case "Client.OnConnect":
                pass

            case "Client.OnDisconnect":
                pass

            case "Client.OnVolumeChanged":
                pass

            case "Client.OnLatencyChanged":
                pass

            case "Client.OnNameChanged":
                pass

            case "Group.OnMute":
                pass

            case "Group.OnStreamChanged":
                pass

            case "Group.OnNameChanged":
                pass

            case "Stream.OnProperties":
                self._on_properties(params)

            case "Stream.OnUpdate":
                pass

            case "Server.OnUpdate":
                pass

            case _:
                pass

    def _on_properties(self, params):
        metadata = params["properties"].get("metadata", {})
        if not metadata:
            return

        meta = {}
        meta["xesam:title"] = Variant("s", metadata.get("title", "Unknown title"))
        meta["xesam:album"] = Variant("s", metadata.get("album", "Unknown album"))
        meta["xesam:artist"] = Variant("as", [metadata.get("artist", "Unknown artist")])
        if artUrl := metadata.get(""):
            meta["mpris:artUrl"] = Variant("s", artUrl)

        self.emit_properties_changed({"Metadata": meta})

    @method()
    def Next(self):
        pass

    @method()
    def Previous(self):
        pass

    @method()
    def Pause(self):
        pass

    @method()
    def PlayPause(self):
        pass

    @method()
    def Stop(self):
        pass

    @method()
    def Play(self):
        pass

    @method()
    def Seek(self, Offset: x):
        pass

    @method()
    def SetPosition(self, TrackId: o, Position: x):
        pass

    @method()
    def OpenUri(self, Uri: s):
        pass

    @signal()
    def Seeked(self) -> x:
        return [0]

    @dbus_property(access=PropertyAccess.READ)
    def PlaybackStatus(self) -> s:
        return "Playing"

    @dbus_property()
    def LoopStatus(self) -> s:
        return "None"

    @LoopStatus.setter
    def LoopStatus(self, Loop_Status: s):
        raise DBusError("PropertyError", "Cannot set loop status for audio streams.")

    @dbus_property()
    def Rate(self) -> d:
        return 1

    @Rate.setter
    def Rate(self, rate: d):
        return 1

    @dbus_property()
    def Shuffle(self) -> b:
        return False

    @Shuffle.setter
    def Shuffle(self, shuffle: b):
        raise DBusError("PropertyError", "Cannot set shuffle status for audio streams.")

    @dbus_property(access=PropertyAccess.READ)
    def Metadata(self) -> "a{sv}":
        return {}

    @dbus_property()
    def Volume(self) -> d:
        return 1

    @Volume.setter
    def Volume(self, volume: d):
        return 1

    @dbus_property(access=PropertyAccess.READ)
    def Position(self) -> x:
        return 0

    @dbus_property(access=PropertyAccess.READ)
    def MinimumRate(self) -> d:
        return 1

    @dbus_property(access=PropertyAccess.READ)
    def MaximumRate(self) -> d:
        return 1

    @dbus_property(access=PropertyAccess.READ)
    def CanGoNext(self) -> b:
        return False

    @dbus_property(access=PropertyAccess.READ)
    def CanGoPrevious(self) -> b:
        return False

    @dbus_property(access=PropertyAccess.READ)
    def CanPlay(self) -> b:
        return False

    @dbus_property(access=PropertyAccess.READ)
    def CanPause(self) -> b:
        return False

    @dbus_property(access=PropertyAccess.READ)
    def CanSeek(self) -> b:
        return False

    @dbus_property(access=PropertyAccess.READ)
    def CanControl(self) -> b:
        return False
