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
from functools import partial
from typing import TYPE_CHECKING

import cairocffi
from cairocffi import Context
from libqtile import bar
from libqtile.backend.base import Drawer
from libqtile.confreader import ConfigError
from libqtile.log_utils import logger
from libqtile.widget import Systray, base

if TYPE_CHECKING:
    from typing import Any  # noqa: F401


class _Decoration(base.PaddingMixin):
    """
    Base decoration class. Should not be called by
    configs directly.
    """

    defaults = [
        ("padding", 0, "Default padding"),
        ("extrawidth", 0, "Add additional width to the end of the decoration"),
        (
            "ignore_extrawidth",
            False,
            "Ignores additional width added by decoration. "
            "Useful when stacking decorations on top of a PowerLineDecoration.",
        ),
    ]  # type: list[tuple[str, Any, str]]

    def __init__(self, **config):
        base.PaddingMixin.__init__(self, **config)
        self.add_defaults(_Decoration.defaults)
        self._extrawidth = self.extrawidth

    def __eq__(self, other):
        return type(self) is type(other) and self._user_config == other._user_config

    def _configure(self, parent: base._Widget) -> None:
        self.parent = parent

    def single_or_four(self, value, name: str):
        if isinstance(value, (float, int)):
            n = e = s = w = value
        elif isinstance(value, (tuple, list)):
            if len(value) == 1:
                n = e = s = w = value[0]
            elif len(value) == 4:
                n, e, s, w = value
            else:
                logger.info("%s should be a single number or a list of 1 or 4 values", name)
                n = e = s = w = 0
        else:
            logger.info("%s should be a single number or a list of 1 or 4 values", name)
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
    def parent_length(self):
        if self.parent.length_type == bar.CALCULATED:
            return int(self.parent.calculate_length())
        return self.parent._length

    @property
    def width(self) -> int:
        if self.parent.bar.horizontal:
            if self.ignore_extrawidth:
                return self.parent_length
            else:
                return self.parent.width
        return self.parent.bar.width

    @property
    def drawer(self) -> Drawer:
        return self.parent.drawer

    @property
    def ctx(self) -> Context:
        return self.drawer.ctx

    def set_source_rgb(self, colour) -> None:
        self.drawer.set_source_rgb(colour, ctx=self.ctx)


class GroupMixin:
    """
    This mixin provides some useful methods for decorations to apply grouping.

    However, the decoration must still apply the relevant logic when drawing.
    """

    defaults = [
        (
            "group",
            False,
            "When set to True, the decoration will be applied as if the widgets were grouped. See documentation for more.",
        ),
    ]

    def _get_parent_group(self):
        """Finds the group of widgets containing the current widget."""

        def in_same_group(w1, w2):
            for dec in getattr(w1, "decorations", list()):
                if dec.group and dec not in getattr(w2, "decorations", list()):
                    return False

            return True

        widgets = self.parent.bar.widgets
        grouped = self._get_grouped_widgets()

        groups = []
        current = [grouped[0]]

        for w in grouped[1:]:
            # If the next grouped widget is not adjacent to the previous grouped widget...
            if widgets.index(w) != widgets.index(current[-1]) + 1 or not in_same_group(
                w, current[-1]
            ):
                # Append the current group to the list of groups and start a new group with widget
                groups.append(current)
                current = [w]
            # Otherwise, append the widget to the current group.
            else:
                current.append(w)

        groups.append(current)

        # Find the group containing the parent widget
        parent_group = [g for g in groups if self.parent in g]

        return parent_group[0]

    def _get_grouped_widgets(self):
        def is_grouped(widget):
            for dec in getattr(widget, "decorations", list()):
                if dec.group:
                    return True

            return False

        widgets = self.parent.bar.widgets
        grouped = [w for w in widgets if is_grouped(w)]

        return grouped

    @property
    def parent_index(self):
        return self.parent.bar.widgets.index(self.parent)

    @property
    def is_first(self):
        if not self.group:
            return True
        grouped = self._get_parent_group()
        visible = [w for w in grouped if w.length > 0]
        return visible and self.parent is visible[0]

    @property
    def is_last(self):
        if not self.group:
            return True
        grouped = self._get_parent_group()
        visible = [w for w in grouped if w.length > 0]
        return visible and self.parent is visible[-1]


class RectDecoration(_Decoration, GroupMixin):
    """
    Widget decoration that draws a rectangle behind the widget contents.

    Rectangles can be drawn as just the the outline or filled and the outline
    can be a different colour to fill. In addition, decorations can be layered
    to achieve more multi-coloured effects.

    Curved corners can be obtained by setting the ``radius`` parameter.

    To have the effect of multiple widgets using the same decoration (e.g.
    the curved ends appearing on the first and last widgets) use the
    ``group=True`` option.

    The advantage of using the ``group`` option is that the group is dynamic
    meaning that it is drawn according to the widgets that are currently visible
    in the group. The group will adjust if a window becomes visible or hidden.

    .. code:: python

        decoration_group = {
            "decorations": [
                RectDecoration(colour="#004040", radius=10, filled=True, padding_y=4, group=True)
            ],
            "padding": 10,
        }

        screens = [
            Screen(
                top=Bar(
                    [
                        extrawidgets.CurrentLayout(**decoration_group),
                        widget.Spacer(),
                        extrawidgets.StatusNotifier(**decoration_group),
                        extrawidgets.Mpris2(**decoration_group),
                        extrawidgets.Clock(format="%H:%M:%S", **decoration_group),
                        extrawidgets.ScriptExit(
                            default_text="[X]",
                            countdown_format="[{}]",
                            countdown_start=2,
                            **decoration_group
                        ),
                    ]
                ),
                28
            )
        ]

    There are two groups in this config: Group 1 is the CurrentLayout widget. Group 2 is the StatusNotifier, Mpris2,
    Clock and ScriptExit widgets. The groups are separated by the Spacer widget.

    When there is no active icon in the StatusNotifier, the bar looks like this:

    .. image:: /_static/images/rect_decoration_group1.png

    When there is an icon, the group is expanded to include the widget:

    .. image:: /_static/images/rect_decoration_group2.png

    Note the group is not broken despite the Mpris2 widget having no contents.

    Groups are determined by looking for:
      - widgets using the identical configuration for the decoration
      - widgets in a consecutive groups

    Groups can therefore be broken by changing the configuration of the group
    (e.g. by adding an additional parameter such as ``group_id=1``) or having
    an undecorated separator between groups.

    Setting ``clip=True`` will result in the widget's contents being restricted to the area covered
    by the decoration. This may be desirable for widgets like ``ALSAWidget`` and
    ``BrightnessControl`` which draw their levels in the bar. NB clipping be be constrained to the
    area inside the outline line width.

    .. image:: /_static/images/rect_decoration_clip.png

    |

    """

    defaults = [
        ("filled", False, "Whether to fill shape"),
        ("radius", 4, "Corner radius as int or list of ints [TL TR BR BL]. 0 is square"),
        ("colour", "#000000", "Colour for decoration"),
        ("line_width", 0, "Line width for decoration"),
        ("line_colour", "#ffffff", "Colour of border"),
        (
            "use_widget_background",
            False,
            "Paint the decoration using the colour from the widget's `background` property. "
            "The widget's background will then be the bar's background colour.",
        ),
        ("clip", False, "Clip contents of widget to decoration area."),
    ]  # type: list[tuple[str, Any, str]]

    _screenshots = [
        ("rect_decoration.png", "Single decoration"),
        ("rect_decoration_stacked.png", "Two decorations stacked"),
    ]

    def __init__(self, **config):
        _Decoration.__init__(self, **config)
        self.add_defaults(GroupMixin.defaults)
        self.add_defaults(RectDecoration.defaults)
        self.corners = self.single_or_four(self.radius, "Corner radius")

    def _draw_path(self, clip=False):
        ctx = self.ctx
        ctx.new_path()

        # If we're clipping then we want the path to be inside
        # the border
        diff = self.line_width / 2 if clip else 0

        box_height = self.height - 2 * self.padding_y
        box_width = self.width - 2 * self.padding_x
        first = False
        last = False

        if not self.radius and not self.group:
            ctx.rectangle(self.padding_x, self.padding_y, box_width, box_height)

        else:
            if self.group and self.parent in self.parent.bar.widgets:
                corners = [0, 0, 0, 0]

                if self.is_first:
                    first = True
                    corners[0] = self.corners[0]
                    corners[3] = self.corners[3]
                if self.is_last:
                    last = True
                    corners[1] = self.corners[1]
                    corners[2] = self.corners[2]

            else:
                corners = self.corners
                first = True
                last = True

            degrees = math.pi / 180.0

            # Top left
            radius = corners[0]
            delta = radius + self.line_width / 2
            y = self.padding_y + delta + diff
            if first:
                x = self.padding_x + delta
            else:
                radius = max(radius - diff, 0)
                x = -self.line_width + diff
            ctx.arc(
                x,
                y,
                radius,
                180 * degrees,
                270 * degrees,
            )

            # Top right
            radius = corners[1]
            delta = radius + self.line_width / 2
            y = self.padding_y + delta + diff
            if last:
                x = self.padding_x + box_width - delta
            else:
                radius = max(radius - diff, 0)
                x = self.width + self.line_width - diff
            ctx.arc(
                x,
                y,
                radius,
                -90 * degrees,
                0 * degrees,
            )

            # Bottom right
            radius = corners[2]
            delta = radius + self.line_width / 2
            y = self.padding_y + box_height - delta - diff
            if last:
                x = self.padding_x + box_width - delta
            else:
                radius = max(radius - diff, 0)
                x = self.width + self.line_width - diff
            ctx.arc(
                x,
                y,
                radius,
                0 * degrees,
                90 * degrees,
            )

            # Bottom left
            radius = corners[3]
            delta = radius + self.line_width / 2
            y = self.padding_y + box_height - delta - diff
            if first:
                x = self.padding_x + delta
            else:
                radius = max(radius - diff, 0)
                x = -self.line_width + diff
            ctx.arc(
                x,
                y,
                radius,
                90 * degrees,
                180 * degrees,
            )

            ctx.close_path()

    def draw(self) -> None:
        # The widget may have resized itsef so we should reset any existing clip area
        self.drawer.ctx.reset_clip()

        self._draw_path()

        if self.filled:
            self.fill_colour = (
                self.parent.background if self.use_widget_background else self.colour
            )
            self.set_source_rgb(self.fill_colour)
            self.ctx.fill_preserve()

        if self.line_width:
            self.ctx.set_line_width(self.line_width)
            self.set_source_rgb(self.line_colour)
            self.ctx.stroke()

        # Clip the widget's drawer so that the contents is limited to the
        # area defined by the decoration
        if self.clip:
            self._draw_path(clip=True)
            self.ctx.clip()
        # If we're not clipping then we need to clear any existing paths
        # (fill_preserve, above, retains the path) to ensure no undesired effects
        # for contents being rendered by widgets, e.g. using masks.
        else:
            self.ctx.new_path()


class BorderDecoration(_Decoration, GroupMixin):
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
        self.add_defaults(GroupMixin.defaults)
        self.add_defaults(BorderDecoration.defaults)
        self.borders = self.single_or_four(self.border_width, "Border width")

    def draw(self) -> None:
        top, right, bottom, left = self.borders

        self.set_source_rgb(self.colour)

        if top:
            offset = top / 2
            self._draw_border(
                self.padding_x
                if self.is_first
                else 0,  # offset not applied to x coords as seems to create a gap
                offset + self.padding_y,
                self.width - (self.padding_x if self.is_last else 0),
                offset + self.padding_y,
                top,
            )

        if right and (not self.group or (self.group and self.is_last)):
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
                self.padding_x
                if self.is_first
                else 0,  # offset not applied to x coords as seems to create a gap
                self.height - offset - self.padding_y,
                self.width - (self.padding_x if self.is_last else 0),
                self.height - offset - self.padding_y,
                bottom,
            )

        if left and (not self.group or (self.group and self.is_first)):
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


class PowerLineDecoration(_Decoration):
    """
    Widget decoration that can be used to recreate the PowerLine style.

    The advantages of the decoration are:
      - No fonts needed
      - The same decoration definition can be used for all widgets (the decoration
        works out which background and foreground colours to use)
      - Different styles can be used by changing a few parameters of the decoration

    The decoration works by adding the shape **after** the current widget. The decoration
    will also be hidden if a widget has zero width (i.e. is hidden).

    The shape is drawn in area whose size is defined by the ``size`` parameter. This area is
    drawn after the widget but can be shifted back by using the ``shift`` parameter. Shifting
    too far will result in widget contents being drawn over the shape.

    By default, the decoration will set colours based on the backgrounds of the adjoining widgets.
    The left-hand portion of the decoration is determined by the decorated widget, the right-hand portion
    comes from the next visible widget in the bar (or the bar background if the decorated widget is the
    last widget in the bar). Both colours can be overriden by using the `override_colour` and
    `override_next_colour` parameters.

    The default behavious is to draw an arrow pointing right. To change the shape you can
    use pre-defined paths: "arrow_left", "arrow_right", "forward_slash", "back_slash", "rounded_left",
    "rounded_right" and "zig_zag". Alternatively, you can create a custom shape by defining a path. The format
    is a list of (x, y) tuples. x and y values should be between 0 and 1 to represent the relative position
    in the additional space created by the decoration. (0, 0) is the top left corner (on a horizontal widget)
    and (1, 1) is the bottom right corner. The first point in the list is the starting point and then a line will
    be drawn to each subsequent point. The path is then closed by returning to the first point.
    Finally, the shape is filled with the background of the current widget.

    .. note::

        The decoration currently only works on horizontal bars. The ``padding_y`` parameter can be
        used to adjust the vertical size of the decoration. However, note that this won't change
        the size of the widget's own background. If you want to do that, you can use the following:

        .. code:: python

            powerline = {
                "decorations": [
                    RectDecoration(use_widget_background=True, padding_y=5, filled=True, radius=0),
                    PowerLineDecoration(path="arrow_right", padding_y=5)
                ]
            }

        The RectDecoration has the same padding and will use the widget's ``background`` parameter as
        its own colour.

    Example code:

    .. code:: python

        from qtile_extras import widget
        from qtile_extras.widget.decorations import PowerLineDecoration

        powerline = {
            "decorations": [
                PowerLineDecoration()
            ]
        }

        screens = [
            Screen(
                top=Bar(
                    [
                        widget.CurrentLayoutIcon(background="000000", **powerline),
                        widget.WindowName(background="222222", **powerline),
                        widget.Clock(background="444444", **powerline),
                        widget.QuickExit(background="666666")
                    ],
                    30
                )
            )
        ]

    The above code generates the following bar:

    .. image:: /_static/images/powerline_example.png

    |

    """

    defaults = [
        ("size", 15, "Width of shape"),
        ("path", "arrow_left", "Shape of decoration. See docstring for more info."),
        ("shift", 0, "Number of pixels to shift the decoration back by."),
        ("override_colour", None, "Force background colour."),
        (
            "override_next_colour",
            None,
            "Force background colour for the next part of the decoration.",
        ),
    ]

    _screenshots = [
        ("powerline_example2.png", "path='arrow_right'"),
        ("powerline_example3.png", "path='rounded_left'"),
        ("powerline_example4.png", "path='rounded_right'"),
        ("powerline_example5.png", "path='forward_slash'"),
        ("powerline_example6.png", "path='back_slash'"),
        ("powerline_example7.png", "path='zig_zag'"),
        (
            "powerline_example8.png",
            "path=[(0, 0), (0.5, 0), (0.5, 0.25), (1, 0.25), (1, 0.75), (0.5, 0.75), (0.5, 1), (0, 1)]",
        ),
    ]

    # Pre-defined paths
    paths = {
        "arrow_left": [(0, 0), (1, 0.5), (0, 1)],
        "arrow_right": [(0, 0), (1, 0), (0, 0.5), (1, 1), (0, 1)],
        "forward_slash": [(0, 0), (1, 0), (0, 1)],
        "back_slash": [(0, 0), (1, 1), (0, 1)],
        "zig_zag": [(0, 0), (1, 0.2), (0, 0.4), (1, 0.6), (0, 0.8), (1, 1), (0, 1)],
    }

    def __init__(self, **config):
        _Decoration.__init__(self, **config)
        self.add_defaults(PowerLineDecoration.defaults)
        self.shift = max(min(self.shift, self.size), 0)
        self._extrawidth += self.size - self.shift

        # This decoration doesn't use the GroupMixin but we need to set the property
        # as False as it's used in a couple of checks when other decorations are grouped
        self.group = False

    def _configure(self, parent):
        _Decoration._configure(self, parent)

        # Add custom shapes
        self.paths["rounded_left"] = self.draw_rounded
        self.paths["rounded_right"] = partial(self.draw_rounded, rotate=True)

        if isinstance(self.path, str):
            shape_path = self.paths.get(self.path, False)
            if callable(shape_path):
                self.draw_func = shape_path
            elif isinstance(shape_path, list):
                self.draw_func = partial(self.draw_path, path=shape_path)
            else:
                raise ConfigError(f"Unknown `path` ({self.path}) for PowerLineDecoration.")
        elif isinstance(self.path, list):
            self.draw_func = partial(self.draw_path, path=self.path)
        else:
            raise ConfigError(f"Unexpected value for PowerLineDecoration `path`: {self.path}.")

        self.parent_background = (
            self.override_colour or self.parent.background or self.parent.bar.background
        )
        self.next_background = self.override_next_colour or self.set_next_colour()

    def set_next_colour(self):
        try:
            index = self.parent.bar.widgets.index(self.parent)
            widgets = self.parent.bar.widgets
            next_widget = next(
                w
                for w in widgets
                if hasattr(w, "length") and w.length and widgets.index(w) > index
            )
            return next_widget.background or self.parent.bar.background
        except (ValueError, IndexError, StopIteration):
            return self.parent.bar.background

    def paint_background(self, background, foreground):
        """
        Bear with me, this one's a bit complicated...
        """
        self.ctx.save()
        self.ctx.set_operator(cairocffi.OPERATOR_SOURCE)

        # If we have vertical padding then we need to paint the bar's background to the space
        if self.padding_y:
            self.ctx.rectangle(
                0,
                0,
                self.parent.length,
                self.parent.bar.height,
            )
            self.set_source_rgb(self.parent.bar.background)
            self.ctx.fill()

            # We then need to clear the part that will be covered by the decoration
            self.drawer.clear_rect(
                0, self.padding_y, self.parent.length, self.parent.bar.height - 2 * self.padding_y
            )

        # We fill the "normal" part of the widget with the background colour...
        self.ctx.rectangle(
            0,
            self.padding_y,
            self.parent_length - self.shift,
            self.parent.bar.height - 2 * self.padding_y,
        )
        self.set_source_rgb(background)
        self.ctx.fill()

        # ...and fill the extra bit (i.e. between the widgets) with the foreground colour.
        self.ctx.rectangle(
            self.parent_length - self.shift,
            self.padding_y,
            self.size,
            self.parent.bar.height - 2 * self.padding_y,
        )
        self.set_source_rgb(foreground)
        self.ctx.fill()

        self.ctx.restore()

    def draw_rounded(self, rotate=False):
        # While not totally necessary to set these as instance variables,
        # it's helpful for testing!
        self.fg = self.parent_background if not rotate else self.next_background
        self.bg = self.next_background if not rotate else self.parent_background

        self.paint_background(self.parent_background, self.bg)

        self.ctx.save()
        self.ctx.set_operator(cairocffi.OPERATOR_SOURCE)

        start = (
            self.parent_length - self.shift + self.extrawidth
            if not rotate
            else self.parent.length
        )

        # Translate the surface so that the origin is in the middle of the arc
        self.ctx.translate(start, self.parent.bar.height // 2)

        # Rotate 180 degrees if drawing curve in the other direction
        if rotate:
            self.ctx.rotate(math.pi)

        # We use scaling in order to be able to draw ellipses
        x_scale = self.parent.length - (self.parent_length - self.shift) - self.extrawidth
        y_scale = (self.parent.bar.height / 2) - self.padding_y
        self.ctx.scale(x_scale, y_scale)

        self.set_source_rgb(self.fg)

        # Radius is 1 as we've scaled the surface
        self.ctx.arc(0, 0, 1, -math.pi / 2, math.pi / 2)
        self.ctx.close_path()
        self.ctx.fill()
        self.ctx.restore()

    def draw_path(self, path=list()):
        if not path:
            return

        # We're going to pop points from the list so we need to
        # operate on a copy
        path = path.copy()

        # While not totally necessary to set these as instance variables,
        # it's helpful for testing!
        self.fg = self.parent_background
        self.bg = self.next_background

        self.paint_background(self.fg, self.bg)

        width = self.size
        height = self.parent.bar.height - 2 * (self.padding_y)

        self.ctx.save()
        self.ctx.set_operator(cairocffi.OPERATOR_SOURCE)

        # Move to the start of the decoration (i.e. the addition area before the next widget)
        self.ctx.translate(self.parent_length - self.shift + self.extrawidth, self.padding_y)

        # The points are defined between 0 and 1 so they get scaled by width and height.
        x, y = path.pop(0)
        self.ctx.move_to(x * width, y * height)

        for x, y in path:
            self.ctx.line_to(x * width, y * height)

        self.ctx.close_path()
        self.set_source_rgb(self.fg)
        self.ctx.fill()

        self.ctx.restore()

    def draw(self) -> None:
        if self.width == 0:
            return

        self.next_background = self.override_next_colour or self.set_next_colour()

        self.ctx.save()
        self.draw_func()
        self.ctx.restore()


def inject_decorations(classdef):
    """
    Method to inject ability for widgets to display decorations.
    """

    def new_clear(self, colour):
        """Draw decorations after clearing background."""
        if self.use_bar_background:
            colour = self.bar.background

        # Clear the widget background with the appropriate colour
        self._pre_clear(colour)

        # Draw the decorations
        for decoration in self.decorations:
            decoration.draw()

    def configure_decorations(self):
        if not hasattr(self, "use_bar_background"):
            self.use_bar_background = False
        if hasattr(self, "decorations"):
            if not self.configured:
                # Give each widget a copy of the decoration objects
                temp_decs = []
                for i, dec in enumerate(self.decorations):
                    cloned_dec = dec.clone()
                    temp_decs.append(cloned_dec)
                    if isinstance(cloned_dec, RectDecoration) and not self.use_bar_background:
                        self.use_bar_background = cloned_dec.use_widget_background
                self.decorations = temp_decs

            for dec in self.decorations:
                dec._configure(self)

            self._pre_clear = self.drawer.clear
            self.drawer.clear = self.new_clear

    def new_configure(self, qtile, bar):
        # We can get into an infinite recursion loop if the widget
        # inherits a class which also has had decoration code injected
        # To fix this, we remove the injected _configure function for
        # any subclasses.
        base_classes = {}
        for c in self.__class__.__mro__[1:]:
            if getattr(c, "old_configure", False):
                base_classes[c] = c._configure
                c._configure = c.old_configure

        self.old_configure(qtile, bar)

        # Replace the injected code for subclasses
        for c, func in base_classes.items():
            c._configure = func

        self.configure_decorations()

    def length_get(self):
        if self.length_type == bar.CALCULATED:
            length = int(self.calculate_length())
        else:
            length = self._length

        if length:
            # Get the largest extra space required by a decoration
            # Max needs an iterator so we need some fallbacks:
            # If the widget doesn't have the decorations attribute then we use an empty list
            # max will error with an empty list so the `default` value is returned in this scenario
            extra = max((x._extrawidth for x in getattr(self, "decorations", list())), default=0)
            return length + extra

        return 0

    def length_set(self, value):
        # Stretch widgets have their length set by the bar.
        # We need to deduct any additional width provided by the decorations as this
        # will be added back when the length of the widget is retrieved.
        if value and hasattr(self, "decorations") and self.length_type == bar.STRETCH:
            extra = max(x._extrawidth for x in self.decorations) if self.decorations else 0
            self._length = value - extra
        else:
            self._length = value

    def create_mirror(self):
        if isinstance(self, Systray):
            return super().create_mirror()

        from qtile_extras.widget import QTEMirror

        return QTEMirror(self, background=self.background)

    if not hasattr(classdef, "_injected_decorations"):
        classdef.old_configure = classdef._configure
        classdef.new_clear = new_clear
        classdef.configure_decorations = configure_decorations
        classdef._configure = new_configure
        classdef.create_mirror = create_mirror
        classdef.length = property(length_get, length_set)

        classdef.defaults.append(("decorations", [], "Decorations for widgets"))

        classdef._injected_decorations = True
