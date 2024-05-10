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

from typing import TYPE_CHECKING

import xcffib
from libqtile.backend.wayland.window import SceneRect, Window, _rgb
from xcffib.wrappers import GContextID, PixmapID

from qtile_extras.layout.decorations.borders import _BorderStyle

if TYPE_CHECKING:
    from libqtile.backend.wayland.window import Core, Qtile, S
    from libqtile.utils import ColorsType


old_wayland_window_init = Window.__init__


def wayland_window_init(self, core: Core, qtile: Qtile, surface: S):
    old_wayland_window_init(self, core, qtile, surface)
    self._border_styles = {}


def wayland_paint_borders(self, colors: ColorsType | None, width: int) -> None:
    if not colors:
        colors = []
        width = 0

    if not isinstance(colors, list):
        colors = [colors]

    if self.tree:
        self.tree.node.set_position(width, width)
    self.bordercolor = colors
    self.borderwidth = width

    if width == 0:
        for rects in self._borders:
            for rect in rects:
                rect.node.destroy()
        self._borders.clear()
        return

    if len(colors) > width:
        colors = colors[:width]

    num = len(colors)
    old_borders = self._borders
    new_borders = []
    widths = [width // num] * num
    for i in range(width % num):
        widths[i] += 1

    outer_w = self.width + width * 2
    outer_h = self.height + width * 2
    coord = 0

    for i, color in enumerate(colors):
        bw = widths[i]
        if isinstance(color, _BorderStyle):
            # Tidy up old data
            if color in self._border_styles:
                _old_buffer, old_surface = self._border_styles.pop(color)
                if old_surface is not None:
                    old_surface.finish()

            scenes, image_buffer, surface = color._wayland_draw(
                self,
                outer_w,
                outer_h,
                bw,
                coord,
                coord,
                outer_w - coord * 2,
                outer_h - coord * 2,
            )

            # Keep reference to border objects
            self._border_styles[color] = (image_buffer, surface)
            new_borders.append(scenes)
        else:
            color_ = _rgb(color)

            # [x, y, width, height] for N, E, S, W
            geometries = (
                (coord, coord, outer_w - coord * 2, bw),
                (outer_w - bw - coord, bw + coord, bw, outer_h - bw * 2 - coord * 2),
                (coord, outer_h - bw - coord, outer_w - coord * 2, bw),
                (coord, bw + coord, bw, outer_h - bw * 2 - coord * 2),
            )

            if old_borders:
                rects = old_borders.pop(0)
                for (x, y, w, h), rect in zip(geometries, rects):
                    rect.set_color(color_)
                    rect.set_size(w, h)
                    rect.node.set_position(x, y)

            else:
                rects = []
                for x, y, w, h in geometries:
                    rect = SceneRect(self.container, w, h, color_)
                    rect.node.set_position(x, y)
                    rects.append(rect)

            new_borders.append(rects)
        coord += bw

    for rects in old_borders:
        for rect in rects:
            rect.node.destroy()

    # Ensure the window contents and any nested surfaces are drawn above the
    # borders.
    if self.tree:
        self.tree.node.raise_to_top()

    self._borders = new_borders


def x11_paint_borders(self, depth, colors, borderwidth, width, height):
    """
    This method is used only by the managing Window class.
    """
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
