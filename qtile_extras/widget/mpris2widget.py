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
import asyncio

from dbus_next.constants import MessageType
from libqtile import widget
from libqtile.command.base import expose_command
from libqtile.utils import _send_dbus_message

from qtile_extras.popup.templates.mpris2 import DEFAULT_IMAGE, DEFAULT_LAYOUT
from qtile_extras.widget.mixins import ExtendedPopupMixin


def hms(time):
    time = time // 1000000
    m, s = divmod(time, 60)
    h, m = divmod(m, 60)

    text = "{h:.0f}:{m:02.0f}:{s:02.0f}" if h else "{m:02.0f}:{s:02.0f}"

    return text.format(h=h, m=m, s=s)


def parse_artwork(path):
    """
    Spotify URLs need to be changed to get the correct address.

    Filepaths need the "file://" prefix removed.
    """
    if path.startswith("file://"):
        path = path[7:]

    elif "open.spotify.com" in path:
        path = path.replace("open.spotify.com", "i.scdn.co")

    return path


class Mpris2(widget.Mpris2, ExtendedPopupMixin):
    """
    Modified version of the base Mpris2 widget.

    This version adds a popup with player controls. Users can provide
    a custom template for the popup using the ``popup_layout`` parameter.

    The popup can be toggled with the ``toggle_player`` command.

    The following fields are available (controls should set their 'name' to this value):

    - 'title': Track title
    - 'artist': Track artist
    - 'album': Album name
    - 'player': Media player name
    - 'artwork': Path to artwork (to be used with a PopupImage control)
    - 'progress': Progress through thrack (to be used with a PopupSlider control)
    - 'position': Current playback position e.g. '03:40'
    - 'length': Track length e.g. '05:15'
    - 'time': String showing position and total length e.g. '03:40 / 05:15'

    To control playback, the template should have controls named:

    - 'play_pause'
    - 'stop'
    - 'previous'
    - 'next'

    When shown, the controls can be selected using the mouse or keyboard navigation. The
    popup can be hidden by pressing <escape> or by calling the ``toggle_player`` command.

    Two pre-defined layouts are currently provided and can be loadeded via:

    .. code::

        from qtile_extras import widget
        from qtile_extras.popup.templates.mpris2 import COMPACT_LAYOUT, DEFAULT_LAYOUT

        ...

        # NB DEFAULT_LAYOUT is included by default and does not need to be imported in
        # your config
        widget.Mpris2(popup_layout=COMPACT_LAYOUT)

    The layouts look like this:

    .. list-table::

        * - DEFAULT_LAYOUT
          - |default|
        * - COMPACT_LAYOUT
          - |compact|

    .. |default| image:: /_static/images/mpris_popup_default.png
    .. |compact| image:: /_static/images/mpris_popup_compact.png

    """

    defaults = [
        ("popup_layout", DEFAULT_LAYOUT, "Layout for player controls."),
        ("parse_artwork", parse_artwork, "Function to parse artwork path."),
        ("default_artwork", DEFAULT_IMAGE, "Image to display in popup when there's no art"),
        ("popup_show_args", {"relative_to": 2, "relative_to_bar": True}, "Where to place popup"),
    ]

    def __init__(self, **config):
        widget.Mpris2.__init__(self, **config)
        ExtendedPopupMixin.__init__(self, **config)
        self.add_defaults(ExtendedPopupMixin.defaults)
        self.add_defaults(Mpris2.defaults)
        self._popup_values = {}

    def bind_callbacks(self):
        self.extended_popup.bind_callbacks(
            play_pause={"Button1": self.play_pause},
            next={"Button1": self.next},
            previous={"Button1": self.previous},
            stop={"Button1": self.stop},
        )

    def _set_popup_text(self, task):
        if task.exception():
            return
        bus, msg = task.result()

        if bus:
            bus.disconnect()

        result = msg.body[0]

        metadata = getattr(result.get("Metadata"), "value", dict())
        position = getattr(result.get("Position"), "value", 0)
        title = getattr(metadata.get("xesam:title"), "value", "")
        artist = ", ".join(getattr(metadata.get("xesam:artist"), "value", list()))
        album = getattr(metadata.get("xesam:album"), "value", "")
        artwork = getattr(metadata.get("mpris:artUrl"), "value", "")

        if artwork:
            artwork = self.parse_artwork(artwork)
        else:
            artwork = self.default_artwork

        if "mpris:length" in metadata:
            length = metadata["mpris:length"].value
            progress = position / length
        else:
            length = 0
            progress = 0

        pos_text = hms(position)
        length_text = hms(length)
        time = f"{pos_text} / {length_text}"

        # Save all properties in a dict
        properties = dict(
            title=title,
            artist=artist,
            album=album,
            progress=progress,
            player=self.player,
            artwork=artwork,
            time=time,
            position=pos_text,
            length=length_text,
        )

        # Identify which values have changed since the last update and just update the popup for those
        changed = dict(set(properties.items()) - set(self._popup_values.items()))
        self.extended_popup.update_controls(**changed)

        self._popup_values = properties

        self.timeout_add(1, self._update_popup)

    def _update_popup(self):
        if not self._current_player or not self.has_popup:
            return

        if not getattr(self.extended_popup, "bound_callbacks", False):
            self.bind_callbacks()
            self._popup_values = {}
            self.extended_popup.bound_callbacks = True

        task = asyncio.create_task(
            _send_dbus_message(
                True,
                MessageType.METHOD_CALL,
                self._current_player,
                "org.freedesktop.DBus.Properties",
                "/org/mpris/MediaPlayer2",
                "GetAll",
                "s",
                ["org.mpris.MediaPlayer2.Player"],
            )
        )
        task.add_done_callback(self._set_popup_text)

    @expose_command()
    def show_popup(self):
        if not self._current_player:
            return

        ExtendedPopupMixin.show_popup(self)

    @expose_command()
    def toggle_player(self):
        if self.extended_popup and not self.extended_popup._killed:
            self.extended_popup.kill()
        else:
            self.show_popup()
