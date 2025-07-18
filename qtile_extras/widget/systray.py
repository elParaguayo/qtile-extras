# Copyright (c) 2022, elParaguayo. All rights reserved.
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
import xcffib
from libqtile import widget
from libqtile.backend.x11 import window
from libqtile.widget.systray import Icon as QIcon
from xcffib.xproto import ClientMessageData, ClientMessageEvent, EventMask, ExposeEvent, SetMode

XEMBED_PROTOCOL_VERSION = 0


class Icon(QIcon):
    def __init__(self, win, qtile, systray):
        super().__init__(win, qtile, systray)
        self._pixmap = None

    def handle_DestroyNotify(self, event):  # noqa: N802
        r = super().handle_DestroyNotify(event)
        self._free_pixmap()
        return r

    def _free_pixmap(self):
        if self._pixmap is not None:
            self.qtile.core.conn.conn.core.FreePixmap(self._pixmap)
            self._pixmap = None

    def set_pixmap(self, x, y, drawer):
        """
        Sets the icon's backpixmap to be the widget's background.
        When using pseudotransparency, this will mean the root wallpaper
        (and any background rendered by the widget) will also be applied
        to the icons.
        """

        # Create a new pixmap the size of the icon window
        if self._pixmap is None:
            self._pixmap = self.qtile.core.conn.conn.generate_id()

            self.qtile.core.conn.conn.core.CreatePixmap(
                drawer._depth,
                self._pixmap,
                self.window.wid,
                self.width,
                self.height,
            )

        # Copy the widget's pixmap to the new pixmap
        with self.qtile.core.masked():
            self.qtile.core.conn.conn.core.CopyArea(
                drawer.pixmap,
                self._pixmap,
                drawer._gc,
                x,
                y,  # Source x, y positions equal the icon's offset in the widget
                0,
                0,  # Pixmap is placed at 0, 0 in new pixmap
                self.width,
                self.height,
            )

            # Apply the pixmap to the window
            self.window.set_attribute(backpixmap=self._pixmap)

        # We need to send an Expose event to force the window to redraw
        event = ExposeEvent.synthetic(self.window.wid, 0, 0, self.width, self.height, 0)
        self.window.send_event(event, mask=EventMask.Exposure)
        self.qtile.core.conn.flush()


class Systray(widget.Systray):
    """
    A modified version of Qtile's Systray widget.

    The only difference is to improve behaviour of the icon background when using
    decorations.

    This widget does not and will not fix the issue with icons having a transparent
    background when displaying on a (semi-)transparent bar.
    """

    _qte_compatibility = True

    def handle_ClientMessage(self, event):  # noqa: N802
        atoms = self.conn.atoms

        opcode = event.type
        data = event.data.data32
        message = data[1]
        wid = data[2]

        parent = self.bar.window.window

        if opcode == atoms["_NET_SYSTEM_TRAY_OPCODE"] and message == 0:
            w = window.XWindow(self.conn, wid)
            icon = Icon(w, self.qtile, self)
            if icon not in self.tray_icons:
                self.tray_icons.append(icon)
                self.tray_icons.sort(key=lambda icon: icon.name)
                self.qtile.windows_map[wid] = icon

            self.conn.conn.core.ChangeSaveSet(SetMode.Insert, wid)
            self.conn.conn.core.ReparentWindow(wid, parent.wid, 0, 0)
            self.conn.conn.flush()

            info = icon.window.get_property("_XEMBED_INFO", unpack=int)

            if not info:
                self.bar.draw()
                return False

            if info[1]:
                self.bar.draw()

        return False

    def draw(self):
        offset = self.padding
        self.drawer.clear(self.background or self.bar.background)
        self.draw_at_default_position()
        for pos, icon in enumerate(self.tray_icons):
            if self.bar.horizontal:
                xoffset = offset
                yoffset = self.bar.height // 2 - self.icon_size // 2
                step = icon.width
            else:
                xoffset = self.bar.width // 2 - self.icon_size // 2
                yoffset = offset
                step = icon.height

            if self.decorations:
                icon.set_pixmap(xoffset, yoffset, self.drawer)
            else:
                icon.window.set_attribute(backpixmap=self.drawer.pixmap)

            icon.place(
                self.offsetx + xoffset,
                self.offsety + yoffset,
                icon.width,
                self.icon_size,
                0,
                None,
            )

            # icon.place(xoffset, yoffset, icon.width, self.icon_size, 0, None)
            if icon.hidden:
                icon.unhide()
                data = [
                    self.conn.atoms["_XEMBED_EMBEDDED_NOTIFY"],
                    xcffib.xproto.Time.CurrentTime,
                    0,
                    self.bar.window.wid,
                    XEMBED_PROTOCOL_VERSION,
                ]
                u = ClientMessageData.synthetic(data, "I" * 5)
                event = ClientMessageEvent.synthetic(
                    format=32, window=icon.wid, type=self.conn.atoms["_XEMBED"], data=u
                )
                self.window.send_event(event)

            offset += step + self.padding
