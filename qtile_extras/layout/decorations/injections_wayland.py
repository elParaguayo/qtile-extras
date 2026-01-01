# Copyright (c) 2021 Matt Colligan
# Copyright (c) 2024-5 elParaguayo
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

from libqtile.backend.wayland._ffi import ffi, lib
from libqtile.backend.wayland.window import Window
from libqtile.log_utils import logger
from libqtile.utils import rgb

from qtile_extras.layout.decorations.borders import (
    ConditionalBorder,
    ConditionalBorderWidth,
    _BorderStyle,
)

if TYPE_CHECKING:
    from libqtile.backend.wayland.window import Core, Qtile, S
    from libqtile.utils import ColorsType


old_wayland_window_init = Window.__init__


def wayland_window_init(self, core: Core, qtile: Qtile, surface: S):
    logger.debug("qtile_extras: Running injected wayland window init.")
    old_wayland_window_init(self, core, qtile, surface)
    self._border_styles = {}


def wayland_place(
    self,
    x: int | None,
    y: int | None,
    width: int | None,
    height: int | None,
    b_width: int | None = None,
    bordercolor: ColorsType | None = None,
    above: bool = False,
    margin: int | list[int] | None = None,
    respect_hints: bool = False,
) -> None:
    # START BORDER WIDTH MODIFICATION
    if isinstance(b_width, ConditionalBorderWidth):
        old = getattr(self, "_old_bw", b_width.default)
        assert old is not None
        borderwidth = b_width.get_border_for_window(self)
        assert borderwidth is not None
        if borderwidth != old:
            width += old * 2
            width -= borderwidth * 2
            height += old * 2
            height -= borderwidth * 2
    else:
        borderwidth = b_width

    self._old_bw = borderwidth
    # END BORDER WIDTH MODIFICATION

    # Adjust the placement to account for layout margins, if there are any.
    # TODO: is respect_hints only for X11?
    assert ffi is not None
    if x is None:
        x = self.x
    if y is None:
        y = self.y
    if bordercolor is None:
        bordercolor = self.bordercolor
    if borderwidth is None:
        borderwidth = self._borderwidth
    if width is None:
        width = self.width
    if height is None:
        height = self.height
    if margin is not None:
        if isinstance(margin, int):
            margin = [margin] * 4
        x += margin[3]
        y += margin[0]
        width -= margin[1] + margin[3]
        height -= margin[0] + margin[2]

    # TODO: respect hints

    if self.group is not None and self.group.screen is not None:
        self.float_x = x - self.group.screen.x
        self.float_y = y - self.group.screen.y

    # START BORDER INJECTION
    border_layers = ffi.NULL
    num = 0

    if bordercolor is not None:
        if not isinstance(bordercolor, list):
            bordercolor = [bordercolor]

        bordercolor = [
            c.compare(self) if isinstance(c, ConditionalBorder) else c for c in bordercolor
        ]

        if len(bordercolor) > width:
            bordercolor = bordercolor[:width]

        num = len(bordercolor)
        widths = [borderwidth // num] * num
        for i in range(borderwidth % num):
            widths[i] += 1

        outer_w = width + borderwidth * 2
        outer_h = height + borderwidth * 2
        coord = 0

        border_layers = ffi.new(f"struct qw_border[{num}]")

        for i, color in enumerate(bordercolor):
            bw = widths[i]
            if isinstance(color, _BorderStyle):
                # Tidy up old data
                if color in self._border_styles:
                    old_surface = self._border_styles.pop(color)
                    if old_surface is not None:
                        old_surface.finish()

                surface, border = color._wayland_draw(
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
                self._border_styles[color] = surface
                border_layers[i] = border

            else:
                color_array = rgb(color)
                border_layers[i].type = lib.QW_BORDER_RECT
                border_layers[i].width = bw
                for side in range(4):
                    for j in range(4):
                        border_layers[i].rect.color[side][j] = color_array[j]
    # END BORDER INJECTION

    self.bordercolor = bordercolor
    self.borderwidth = borderwidth
    self._ptr.place(self._ptr, x, y, width, height, border_layers, num, int(above))
