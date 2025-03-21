# mypy: disable-error-code="name-defined,no-redef,valid-type"
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

from dbus_fast import NameFlag, RequestNameReply, Variant
from dbus_fast.aio import MessageBus
from dbus_fast.constants import PropertyAccess
from dbus_fast.errors import DBusError
from dbus_fast.service import ServiceInterface, dbus_property, method, signal
from libqtile.log_utils import logger

from qtile_extras.resources.snapcast.snapcontrol import GROUP_ONSTREAMCHANGED, STREAM_ONPROPERTIES


# org.mpris.MediaPlayer2 interface
# https://specifications.freedesktop.org/mpris-spec/latest/Media_Player.html
class SnapMpris(ServiceInterface):
    def __init__(self, widget):
        super().__init__("org.mpris.MediaPlayer2")
        self.widget = widget

    @method()
    def Raise(self):  # noqa: N802
        pass

    @method()
    def Quit(self):  # noqa: N802
        self.widget.stop()

    @dbus_property(access=PropertyAccess.READ)
    def CanQuit(self) -> b:  # noqa: N802, F821
        return True

    @dbus_property()
    def Fullscreen(self) -> b:  # noqa: N802, F821
        return False

    @Fullscreen.setter
    def Fullscreen(self, fullscreen: b):  # noqa: N802, F821, F841
        raise DBusError("PropertyError", "Can't set player fullscreen status.")

    @dbus_property(access=PropertyAccess.READ)
    def CanSetFullscreen(self) -> b:  # noqa: N802, F821
        return False

    @dbus_property(access=PropertyAccess.READ)
    def CanRaise(self) -> b:  # noqa: N802, F821
        return False

    @dbus_property(access=PropertyAccess.READ)
    def HasTrackList(self) -> b:  # noqa: N802, F821
        return False

    @dbus_property(access=PropertyAccess.READ)
    def Identity(self) -> s:  # noqa: N802, F821
        return "qtile-snapcast-widget"

    @dbus_property(access=PropertyAccess.READ)
    def DesktopEntry(self) -> s:  # noqa: N802, F821
        return ""

    @dbus_property(access=PropertyAccess.READ)
    def SupportedUriSchemes(self) -> "as":  # noqa: N802, F821, F722
        return []

    @dbus_property(access=PropertyAccess.READ)
    def SupportedMimeTypes(self) -> "as":  # noqa: N802, F821, F722
        return []


# org.mpris.MediaPlayer2.Player interface
# https://specifications.freedesktop.org/mpris-spec/latest/Player_Interface.html
class SnapMprisPlayer(ServiceInterface):
    def __init__(self, service_name, control, widget):
        super().__init__("org.mpris.MediaPlayer2.Player")
        self.control = control
        self.bus = None
        self.service_name = service_name
        self._error = None
        self.widget = widget
        self.stream_props = {}

        self._metadata = {}
        self._playbackstatus = "Playing"

        self._request_name_warned = False

    @property
    def metadata(self):
        return self._metadata

    @metadata.setter
    def metadata(self, data):
        if data != self._metadata:
            self._metadata = data
            self.emit_properties_changed({"Metadata": data})

    @property
    def playback_status(self):
        return self._playbackstatus

    @playback_status.setter
    def playback_status(self, status):
        status = status.capitalize()
        if status != self._playbackstatus:
            self._playbackstatus = status
            self.emit_properties_changed({"PlaybackStatus": status})

    def send_command(self, command):
        params = {"id": self.widget.stream, "command": command}
        self.control.send("Stream.Control", params=params)

    async def start(self):
        try:
            self.bus = await MessageBus().connect()
        except Exception as e:  # ugly but "connect" passes through all errors
            self._error = e
            return False

        self.bus.export("/org/mpris/MediaPlayer2", SnapMpris(self.widget))
        self.bus.export("/org/mpris/MediaPlayer2", self)

        reply = await self.bus.request_name(self.service_name, flags=NameFlag.DO_NOT_QUEUE)
        if reply is RequestNameReply.EXISTS:
            if not self._request_name_warned:
                logger.warning("Unable to request dbus service name.")
                self._request_name_warned = True
            self.bus.disconnect()
            self.bus = None
            return False

        self.control.subscribe(STREAM_ONPROPERTIES, self._on_properties)
        self.control.subscribe(GROUP_ONSTREAMCHANGED, self._on_stream_change)

        return True

    def stop(self):
        if self.bus is not None:
            self.bus.disconnect()
            self.bus = None
            self.control.unsubscribe(STREAM_ONPROPERTIES, self._on_properties)
            self.control.unsubscribe(GROUP_ONSTREAMCHANGED, self._on_stream_change)

    def _on_stream_change(self, params):
        stream = params["stream_id"]
        if stream == self.widget.stream and stream in self.stream_props:
            self.process_props(self.stream_props[stream])

    def _on_properties(self, params):
        props = params["properties"]
        stream = params["id"]
        self.stream_props[stream] = props
        if stream == self.widget.stream:
            self.process_props(props)

    def process_props(self, props):
        self.check_metadata(props)

        if "playbackStatus" in props:
            self.playback_status = props["playbackStatus"]

    def check_metadata(self, props):
        metadata = props.get("metadata", {})
        if not metadata:
            return

        meta = {}
        meta["xesam:title"] = Variant("s", metadata.get("title", "Unknown title"))
        meta["xesam:album"] = Variant("s", metadata.get("album", "Unknown album"))
        meta["xesam:artist"] = Variant("as", metadata.get("artist", ["Unknown artist"]))
        if art_url := metadata.get("artUrl"):
            meta["mpris:artUrl"] = Variant("s", art_url)

        self.metadata = meta

    @method()
    def Next(self):  # noqa: N802
        self.send_command("next")

    @method()
    def Previous(self):  # noqa: N802
        self.send_command("previous")

    @method()
    def Pause(self):  # noqa: N802
        self.send_command("pause")

    @method()
    def PlayPause(self):  # noqa: N802
        self.send_command("playPayse")

    @method()
    def Stop(self):  # noqa: N802
        self.send_command("stop")

    @method()
    def Play(self):  # noqa: N802
        self.send_command("play")

    @method()
    def Seek(self, Offset: x):  # noqa: N802, F821, N803, F841
        pass

    @method()
    def SetPosition(self, TrackId: o, Position: x):  # noqa: N802, F821, N803, F841
        pass

    @method()
    def OpenUri(self, Uri: s):  # noqa: N802, F821, N803, F841
        pass

    @signal()
    def Seeked(self) -> x:  # noqa: N802, F821
        return [0]

    @dbus_property(access=PropertyAccess.READ)
    def PlaybackStatus(self) -> s:  # noqa: N802, F821
        return self.playback_status

    @dbus_property()
    def LoopStatus(self) -> s:  # noqa: N802, F821
        return "None"

    @LoopStatus.setter
    def LoopStatus(self, Loop_Status: s):  # noqa: N802, F821, N803, F841
        raise DBusError("PropertyError", "Cannot set loop status for audio streams.")

    @dbus_property()
    def Rate(self) -> d:  # noqa: N802, F821
        return 1

    @Rate.setter
    def Rate(self, rate: d):  # noqa: N802, F821, F841
        return 1

    @dbus_property()
    def Shuffle(self) -> b:  # noqa: N802, F821
        return False

    @Shuffle.setter
    def Shuffle(self, shuffle: b):  # noqa: N802, F821, F841
        raise DBusError("PropertyError", "Cannot set shuffle status for audio streams.")

    @dbus_property(access=PropertyAccess.READ)
    def Metadata(self) -> "a{sv}":  # noqa: N802, F821, F722
        return self.metadata

    @dbus_property()
    def Volume(self) -> d:  # noqa: N802, F821
        return 1

    @Volume.setter
    def Volume(self, volume: d):  # noqa: N802, F821, F841
        return 1

    @dbus_property(access=PropertyAccess.READ)
    def Position(self) -> x:  # noqa: N802, F821
        return 0

    @dbus_property(access=PropertyAccess.READ)
    def MinimumRate(self) -> d:  # noqa: N802, F821
        return 1

    @dbus_property(access=PropertyAccess.READ)
    def MaximumRate(self) -> d:  # noqa: N802, F821
        return 1

    @dbus_property(access=PropertyAccess.READ)
    def CanGoNext(self) -> b:  # noqa: N802, F821
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanGoPrevious(self) -> b:  # noqa: N802, F821
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanPlay(self) -> b:  # noqa: N802, F821
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanPause(self) -> b:  # noqa: N802, F821
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanSeek(self) -> b:  # noqa: N802, F821
        return False

    @dbus_property(access=PropertyAccess.READ)
    def CanControl(self) -> b:  # noqa: N802, F821
        return True
