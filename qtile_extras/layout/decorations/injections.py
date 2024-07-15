# Copyright (c) 2021 Matt Colligan
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

import xcffib
from libqtile import qtile
from libqtile.log_utils import logger
from xcffib.wrappers import GContextID, PixmapID

from qtile_extras.layout.decorations.borders import (
    ConditionalBorder,
    ConditionalBorderWidth,
    _BorderStyle,
)


def x11_paint_borders(self, depth, colors, borderwidth, width, height):
    """
    This method is used only by the managing Window class.
    """
    logger.debug("qtile_extras: Running injected x11 paint borders.")
    self.set_property("_NET_FRAME_EXTENTS", [borderwidth] * 4)

    if not colors or not borderwidth:
        return

    if isinstance(colors, str):
        self.set_attribute(borderpixel=self.conn.color_pixel(colors))
        return
    elif isinstance(colors, _BorderStyle):
        colors = [colors]

    if len(colors) > borderwidth:
        colors = colors[:borderwidth]

    win = qtile.windows_map.get(self.wid)

    colors = [c.compare(win) if isinstance(c, ConditionalBorder) else c for c in colors]

    core = self.conn.conn.core
    outer_w = width + borderwidth * 2
    outer_h = height + borderwidth * 2

    with PixmapID(self.conn.conn) as pixmap:
        with GContextID(self.conn.conn) as gc:
            core.CreatePixmap(depth, pixmap, self.wid, outer_w, outer_h)
            core.CreateGC(gc, pixmap, 0, None)
            borders = len(colors)
            borderwidths = [borderwidth // borders] * borders
            for i in range(borderwidth % borders):
                borderwidths[i] += 1
            coord = 0
            for i in range(borders):
                if isinstance(colors[i], _BorderStyle):
                    colors[i]._x11_draw(
                        self,
                        depth,
                        pixmap,
                        gc,
                        outer_w,
                        outer_h,
                        borderwidth,
                        coord,
                        coord,
                        outer_w - coord * 2,
                        outer_h - coord * 2,
                    )
                else:
                    core.ChangeGC(
                        gc, xcffib.xproto.GC.Foreground, [self.conn.color_pixel(colors[i])]
                    )
                    rect = xcffib.xproto.RECTANGLE.synthetic(
                        coord, coord, outer_w - coord * 2, outer_h - coord * 2
                    )
                    core.PolyFillRectangle(pixmap, gc, 1, [rect])
                coord += borderwidths[i]
            self._set_borderpixmap(depth, pixmap, gc, borderwidth, width, height)


def new_place(
    self,
    x,
    y,
    width,
    height,
    borderwidth,
    bordercolor,
    above=False,
    margin=None,
    respect_hints=False,
):
    logger.debug("qtile_extras: Running injected window place method.")
    if isinstance(borderwidth, ConditionalBorderWidth):
        old = getattr(self, "_old_bw", borderwidth.default)
        newborder = borderwidth.get_border_for_window(self)
        if newborder != old:
            width += old * 2
            width -= newborder * 2
            height += old * 2
            height -= newborder * 2
    else:
        newborder = borderwidth

    self._old_bw = newborder

    self._place(
        x,
        y,
        width,
        height,
        newborder,
        bordercolor,
        above=above,
        margin=margin,
        respect_hints=respect_hints,
    )
