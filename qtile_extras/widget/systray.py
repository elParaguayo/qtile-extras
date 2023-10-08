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

from qtile_extras.widget.decorations import RectDecoration

XEMBED_PROTOCOL_VERSION = 0


class Systray(widget.Systray):
    """
    A modified version of Qtile's Systray widget.

    The only difference is to improve behaviour of the icon background when using
    ``RectDecoration`` decorations.

    This widget does not and will not fix the issue with icons having a transparent
    background when displaying on a (semi-)transparent bar.
    """

    _qte_compatibility = True

    def draw(self):
        offset = self.padding
        self.drawer.clear(self.background or self.bar.background)
        self.drawer.draw(offsetx=self.offset, offsety=self.offsety, width=self.length)
        for pos, icon in enumerate(self.tray_icons):
            icon.window.set_attribute(backpixmap=self.drawer.pixmap)
            if self.bar.horizontal:
                xoffset = offset
                yoffset = self.bar.height // 2 - self.icon_size // 2
                step = icon.width
            else:
                xoffset = self.bar.width // 2 - self.icon_size // 2
                yoffset = offset
                step = icon.height

            if self.drawer.pseudotransparent or self.decorations:
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

            if icon.hidden:
                icon.unhide()
                data = [
                    self.conn.atoms["_XEMBED_EMBEDDED_NOTIFY"],
                    xcffib.xproto.Time.CurrentTime,
                    0,
                    self.bar.window.wid,
                    XEMBED_PROTOCOL_VERSION,
                ]
                u = xcffib.xproto.ClientMessageData.synthetic(data, "I" * 5)
                event = xcffib.xproto.ClientMessageEvent.synthetic(
                    format=32, window=icon.wid, type=self.conn.atoms["_XEMBED"], data=u
                )
                self.window.send_event(event)

            offset += step + self.padding
