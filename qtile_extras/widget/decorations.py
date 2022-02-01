# Copyright (c) 2021, elParaguayo. All rights reserved.
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

import copy
import math
from typing import TYPE_CHECKING

from cairocffi import Context
from libqtile.backend.base import Drawer
from libqtile.log_utils import logger
from libqtile.widget import base

if TYPE_CHECKING:
    from typing import Any


class _Decoration(base.PaddingMixin):
    """
    Base decoration class. Should not be called by
    configs directly.
    """

    defaults = [("padding", 0, "Default padding")]  # type: list[tuple[str, Any, str]]

    def __init__(self, **config):
        base.PaddingMixin.__init__(self, **config)
        self.add_defaults(_Decoration.defaults)

    def _configure(self, parent: base._Widget) -> None:
        self.parent = parent

    def single_or_four(self, value, name: str):
        if type(value) in [float, int]:
            n = e = s = w = value
        elif type(value) in [tuple, list]:
            if len(value) == 1:
                n = e = s = w = value[0]
            elif len(value) == 4:
                n, e, s, w = value
            else:
                logger.info(f"{name} should be a single number or a list of 1 or 4 values")
                n = e = s = w = 0
        else:
            logger.info(f"{name} should be a single number or a list of 1 or 4 values")
            n = e = s = w = 0

        return [n, e, s, w]

    def clone(self) -> _Decoration:
        return copy.copy(self)

    @property
    def height(self) -> int:
        if self.parent.bar.horizontal:
            return self.parent.bar.height
        return self.parent.height

    @property
    def width(self) -> int:
        if self.parent.bar.horizontal:
            return self.parent.width
        return self.parent.bar.width

    @property
    def drawer(self) -> Drawer:
        return self.parent.drawer

    @property
    def ctx(self) -> Context:
        return self.parent.drawer.ctx


class RectDecoration(_Decoration):
    """
    Widget decoration that draws a rectangle behind the widget contents.

    Only one colour can be set but decorations can be layered to achieve
    multi-coloured effects.

    Rectangles can be drawn as just the the outline or filled. Curved corners
    can be obtained by setting the ``radius`` parameter.
    """

    defaults = [
        ("filled", False, "Whether to fill shape"),
        ("radius", 4, "Corner radius as int or list of ints [TL TR BR BL]. 0 is square"),
        ("colour", "#000000", "Colour for decoration"),
        ("line_width", 2, "Line width for decoration"),
    ]  # type: list[tuple[str, Any, str]]

    _screenshots = [
        ("rect_decoration.png", "Single decoration"),
        ("rect_decoration_stacked.png", "Two decorations stacked"),
    ]

    def __init__(self, **config):
        _Decoration.__init__(self, **config)
        self.add_defaults(RectDecoration.defaults)
        self.corners = self.single_or_four(self.radius, "Corner radius")

    def draw(self) -> None:
        box_height = self.height - 2 * self.padding_y
        box_width = self.width - 2 * self.padding_x

        self.drawer.set_source_rgb(self.colour)

        if not self.radius:

            self.ctx.rectangle(self.padding_x, self.padding_y, box_width, box_height)

        else:

            degrees = math.pi / 180.0

            self.ctx.new_sub_path()

            # Top left
            radius = self.corners[0]
            delta = radius + self.line_width / 2 - 1
            self.ctx.arc(
                self.padding_x + delta,
                self.padding_y + delta,
                radius,
                180 * degrees,
                270 * degrees,
            )

            # Top right
            radius = self.corners[1]
            delta = radius + self.line_width / 2 - 1
            self.ctx.arc(
                self.padding_x + box_width - delta,
                self.padding_y + delta,
                radius,
                -90 * degrees,
                0 * degrees,
            )

            # Bottom right
            radius = self.corners[2]
            delta = radius + self.line_width / 2 - 1
            self.ctx.arc(
                self.padding_x + box_width - delta,
                self.padding_y + box_height - delta,
                radius,
                0 * degrees,
                90 * degrees,
            )

            # Bottom left
            radius = self.corners[3]
            delta = radius + self.line_width / 2 - 1
            self.ctx.arc(
                self.padding_x + delta,
                self.padding_y + box_height - delta,
                radius,
                90 * degrees,
                180 * degrees,
            )

            self.ctx.close_path()

        if self.filled:
            self.ctx.fill()
        else:
            self.ctx.set_line_width(self.line_width)
            self.ctx.stroke()


class BorderDecoration(_Decoration):
    """
    Widget decoration that draws a straight line on the widget border.
    Padding can be used to adjust the position of the border further.

    Only one colour can be set but decorations can be layered to achieve
    multi-coloured effects.
    """

    defaults = [
        ("colour", "#000000", "Border colour"),
        ("border_width", 2, "Border width as int or list of ints [N E S W]."),
    ]  # type: list[tuple[str, Any, str]]

    _screenshots = [("border_decoration.png", "Stacked borders")]

    def __init__(self, **config):
        _Decoration.__init__(self, **config)
        self.add_defaults(BorderDecoration.defaults)
        self.borders = self.single_or_four(self.border_width, "Border width")

    def draw(self) -> None:
        top, right, bottom, left = self.borders

        self.drawer.set_source_rgb(self.colour)

        if top:
            offset = top / 2
            self._draw_border(
                self.padding_x,  # offset not applied to x coords as seems to create a gap
                offset + self.padding_y,
                self.width - self.padding_x,
                offset + self.padding_y,
                top,
            )

        if right:
            offset = right / 2
            self._draw_border(
                self.width - offset - self.padding_x,
                offset + self.padding_y,
                self.width - offset - self.padding_x,
                self.height - offset - self.padding_y,
                right,
            )

        if bottom:
            offset = bottom / 2
            self._draw_border(
                self.padding_x,  # offset not applied to x coords as seems to create a gap
                self.height - offset - self.padding_y,
                self.width - self.padding_y,
                self.height - offset - self.padding_y,
                bottom,
            )

        if left:
            offset = left / 2
            self._draw_border(
                offset + self.padding_x,
                offset + self.padding_y,
                offset + self.padding_x,
                self.height - offset - self.padding_y,
                left,
            )

    def _draw_border(self, x1: float, y1: float, x2: float, y2: float, line_width: float) -> None:
        self.ctx.move_to(x1, y1)
        self.ctx.line_to(x2, y2)
        self.ctx.set_line_width(line_width)
        self.ctx.stroke()


def inject_decorations(classdef):
    """
    Method to inject ability for widgets to display decorations.
    """

    def new_clear(self, colour):
        """Draw decorations after clearing background."""
        self._clear(colour)

        for decoration in self.decorations:
            decoration.draw()

    def configure_decorations(self):
        if hasattr(self, "decorations"):
            if not self.configured:
                # Give each widget a copy of the decoration objects
                temp_decs = []
                for i, dec in enumerate(self.decorations):
                    cloned_dec = dec.clone()
                    cloned_dec._configure(self)
                    temp_decs.append(cloned_dec)
                self.decorations = temp_decs

            self._clear = self.drawer.clear
            self.drawer.clear = self.new_clear

    def new_configure(self, qtile, bar):
        self.old_configure(qtile, bar)
        self.configure_decorations()

    if not hasattr(classdef, "_injected_decorations"):

        classdef.old_configure = classdef._configure
        classdef.new_clear = new_clear
        classdef.configure_decorations = configure_decorations
        classdef._configure = new_configure

        classdef.defaults.append(("decorations", [], "Decorations for widgets"))

        classdef._injected_decorations = True
