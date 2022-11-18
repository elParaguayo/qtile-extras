# Copyright (c) 2021 elParaguayo
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

import math
import os
from typing import TYPE_CHECKING

import cairocffi
from libqtile import bar, configurable, hook, pangocffi
from libqtile.backend.x11.xkeysyms import keysyms
from libqtile.command import interface
from libqtile.lazy import LazyCall
from libqtile.log_utils import logger
from libqtile.popup import Popup
from libqtile.utils import QtileError

from qtile_extras.images import Img

if TYPE_CHECKING:
    from typing import Any

    from libqtile.core.manager import Qtile


class _PopupLayout(configurable.Configurable):
    """
    This is the base class for a 2D popup layout that displays additional
    information/controls for widgets on the user's bar.

    As a bare minimum, the tooltip requires width and height and a list of
    "controls" that should be displayed within the tooltip.

    Note: It is currently envisaged that Popups will have a fixed size unlike
    widgets which are able to have variable sizes.
    """

    defaults = [
        ("width", 200, "Width of tooltip"),
        ("height", 200, "Height of tooltip"),
        ("controls", [], "Controls to display"),
        ("margin", 5, "Margin around edge of tooltip"),
        ("background", "000000", "Popup background colour"),
        ("border", "111111", "Border colour for popup"),
        ("border_width", 0, "Popup border width"),
        ("opacity", 1, "Popup window opacity. 'None' inherits bar opacity"),
        ("close_on_click", True, "Hide the popup when control is clicked"),
        (
            "keymap",
            {
                "left": ["Left", "h"],
                "right": ["Right", "l"],
                "up": ["Up", "j"],
                "down": ["Down", "k"],
                "select": ["Return", "space"],
                "step": ["Tab"],
                "close": ["Escape"],
            },
            "Keyboard controls. NB Navigation logic is very rudimentary. The popup will try "
            "to select the nearest control in the direction pressed but some controls may be "
            "inaccessible. In that scenario, use the mouse or `Tab` to cycle through controls.",
        ),
        ("keyboard_navigation", True, "Whether popup controls can be navigated by keys"),
        ("initial_focus", 0, "Index of control to be focused at startup."),
        ("hide_interval", 0.5, "Timeout after mouse leaves popup before popup is lilled"),
        ("hide_on_mouse_leave", False, "Hide the popup if the mouse pointer leaves the popup"),
        (
            "hide_on_timeout",
            0,
            "Timeout before popup closes (0 = disabled). Useful for notifications",
        ),
    ]  # type: list[tuple[str, Any, str]]

    def __init__(self, qtile: Qtile | None = None, **config):
        configurable.Configurable.__init__(self, **config)
        self.add_defaults(_PopupLayout.defaults)
        self.configured = False
        self.finalized = False
        self.qtile = qtile

        # Define drawable area
        self._width = self.width - 2 * self.margin
        self._height = self.height - 2 * self.margin

        # Keep track of which control the mouse is over
        self.cursor_in = None

        self._hooked = False

        # Identify focused control (via mouse of keypress)
        self.focusable_controls = [c for c in self.controls if c.can_focus]
        if self.initial_focus is None or not self.focusable_controls:
            self._focused = None
        else:
            try:
                self._focused = self.focusable_controls[self.initial_focus]
            except IndexError:
                self._focused = self.focusable_controls[0]

        if not self.focusable_controls:
            self.keyboard_navigation = False

        # Identify keysyms for keybaord navigation
        self.keys = {k: [keysyms[key.lower()] for key in v] for k, v in self.keymap.items()}

        # Build dict of updateable controls
        self._set_updateable_controls()

        self._autohide_timer = None
        self._hide_timer = None
        self._killed = False

    def _configure(self, qtile: Qtile | None = None):
        """
        This method creates an instances of a Popup window which serves as the
        base for the tooltip.

        We also attach handlers for mouse events so that these can be passed to
        the relevant controls.
        """
        if self.qtile is None:
            if qtile is None:
                raise QtileError("Cannot configure layout without Qtile instance.")
            else:
                self.qtile = qtile

        self.popup = Popup(
            self.qtile,
            width=self.width,
            height=self.height,
            background=self.background,
            opacity=self.opacity,
            border=self.border,
            border_width=self.border_width,
        )
        self.popup.win.info = self.info

        self.popup.win.process_button_click = self.process_button_click
        self.popup.win.process_button_release = self.process_button_release
        self.popup.win.process_pointer_enter = self.process_pointer_enter
        self.popup.win.process_pointer_leave = self.process_pointer_leave
        self.popup.win.process_pointer_motion = self.process_pointer_motion
        self.popup.win.process_key_press = self.process_key_press

        self.place_controls()

        if self._focused:
            self._focused.focus()

        self.configured = True

    def _set_updateable_controls(self):
        controls = {}
        for c in self.controls:
            if c.name is None:
                continue

            if c.name in controls:
                logger.warning(
                    f"There is an existing control named {c.name}. "
                    f"If you wish to update controls then they must have unique names."
                )
                continue

            controls[c.name] = c

        self._updateable_controls = controls

    def place_controls(self):
        for c in self.controls:
            self._place_control(c)
            c._configure(self.qtile, self)

    def _place_control(self, control):
        """
        This method should define the offsets and positions for the control.

        Layous therefore need to override this method with the specific rules
        for that layout.
        """
        pass

    def draw(self):
        """
        Assuming popup is a fixed size, we can just draw widgets without
        re-positioning them.
        """
        if not self.configured or self.finalized:
            return

        self.popup.clear()
        for c in self.controls:
            c.draw()
        self.popup.draw()

    def show(
        self,
        x: int | float = 0,
        y: int | float = 0,
        centered: bool = False,
        warp_pointer: bool = False,
        relative_to: int = 1,
        relative_to_bar: bool = False,
        qtile: Qtile | None = None,
        hide_on_timeout: int | float | None = None,
    ):
        """
        Display the popup. Can be centered on screen.

        x and y coordinates are relative to the current screen. By default, the coordinates
        are relative to the top left corner but this can be adjusted by setting the
        `relative_to` parameter. The parameter is an integer from 1 to 9 representing the
        screen broken into a 3x3 grid:

        .. ::

             1      2      3

             4      5      6

             7      8      9

        The number also represents the point on the popup corresponding to the relative
        coordinates i.e. for ``relative_to=7`` an x, y value of 0, 0 would place the
        bottom left corner of the popup in the bottom left corner of the screen. The
        x, y values can be integers representing the number of pixels to move, or a float
        representing the percentage of the screen's dimensions to move. In all cases, a
        positive x value will shift the popup to the right and a positive y value will shift
        the popup down.

        Setting ``relative_to_bar=True`` will automatically adjust the offset by the width of
        the bar or gap (including any margin) nearest the point on the above grid
        i.e. if ``relative_to=1`` then the y coordinate would be adjusted for any bar on the
        top of the screen and the x would be adjusted for any bar on the left. NB If you set
        ``relative_to-bar=True`` and you use a float value for x and/or y, the float value is
        still calculated by reference to the whole screen's dimensions (i.e. including the space
        occupied by the bar).

        An automatic hide timer can be set via ``hide_on_timeout``. This will replace any value
        that was set when configuring the layout.
        """
        if not self.configured:
            self._configure(qtile)

        # mypy doesn't realise we can only get here if the layout is configured which
        # requires self.qtile to be set...
        assert self.qtile

        scr = self.qtile.current_screen

        if centered:
            x = int((scr.width - self.popup.width) / 2) + scr.x
            y = int((scr.height - self.popup.height) / 2) + scr.y
        else:
            # If x and y are floats then we calculate the percentage of screen dimensions
            if isinstance(x, float):
                x = int(scr.width * x)

            if isinstance(y, float):
                y = int(scr.height * y)

            if relative_to == 1:
                x += scr.x
                y += scr.y

            elif relative_to == 2:
                x += scr.x + (scr.width - self.popup.width) // 2
                y += scr.y

            elif relative_to == 3:
                x += scr.x + scr.width - self.popup.width
                y += scr.y

            elif relative_to == 4:
                x += scr.x
                y += scr.y + (scr.height - self.popup.height) // 2

            elif relative_to == 5:
                x += scr.x + (scr.width - self.popup.width) // 2
                y += scr.y + (scr.height - self.popup.height) // 2

            elif relative_to == 6:
                x += scr.x + scr.width - self.popup.width
                y += scr.y + (scr.height - self.popup.height) // 2

            elif relative_to == 7:
                x += scr.x
                y += scr.y + scr.height - self.popup.height

            elif relative_to == 8:
                x += scr.x + (scr.width - self.popup.width) // 2
                y += scr.y + scr.height - self.popup.height

            elif relative_to == 9:
                x += scr.x + scr.width - self.popup.width
                y += scr.y + scr.height - self.popup.height

            else:
                logger.warning(f"Unexpected value for 'relative_to': {relative_to}.")
                x += scr.x
                y += scr.y

            if relative_to_bar:
                if relative_to in [1, 2, 3] and scr.top:
                    y += scr.top.size

                if relative_to in [3, 6, 9] and scr.right:
                    x -= scr.right.size

                if relative_to in [7, 8, 9] and scr.bottom:
                    y -= scr.bottom.size

                if relative_to in [1, 4, 7] and scr.left:
                    x += scr.left.size

        self.popup.x = x
        self.popup.y = y
        self.popup.place()
        self.draw()
        self.popup.unhide()

        if warp_pointer:
            self.qtile.core.warp_pointer(
                int(self.popup.x + self.popup.width // 2),
                int(self.popup.y + self.popup.height // 2),
            )

        if self.keyboard_navigation:
            self.set_hooks()
            self.popup.win.focus(False)

        if hide_on_timeout is not None:
            self.hide_on_timeout = hide_on_timeout

        if self.hide_on_timeout:
            self._set_autohide()

    def set_hooks(self):
        hook.subscribe.client_focus(self.focus_change)
        hook.subscribe.focus_change(self.focus_change)
        self._hooked = True

    def unset_hooks(self):
        if self._hooked:
            hook.unsubscribe.client_focus(self.focus_change)
            hook.unsubscribe.focus_change(self.focus_change)
            self._hooked = False

    def focus_change(self, window=None):
        if window is None or not window == self.popup.win:
            self.kill()

    def _set_autohide(self):
        if self._autohide_timer is not None:
            self._autohide_timer.cancel()

        self._autohide_timer = self.qtile.call_later(self.hide_on_timeout, self.kill)

    def hide(self):
        """Hide the popup."""
        self.popup.hide()

    def kill(self):
        if self.keyboard_navigation:
            self.unset_hooks()
        self.popup.kill()
        self.finalize()
        self.finalized = True
        self._killed = True

    def finalize(self):
        for control in self.controls:
            control.finalize()

    # The below methods are lifted from `bar`
    def get_control_in_position(self, x, y):
        for c in self.controls:
            if c.mouse_in_control(x, y):
                return c
        return None

    def process_button_click(self, x, y, button):  # noqa: N802
        control = self.get_control_in_position(x, y)
        if control:
            control.button_press(x - control.offsetx, y - control.offsety, button)
        if self.close_on_click:
            self.kill()

    def process_button_release(self, x, y, button):  # noqa: N802
        control = self.get_control_in_position(x, y)
        if control:
            control.button_release(x - control.offsetx, y - control.offsety, button)

    def process_pointer_enter(self, x, y):  # noqa: N802
        control = self.get_control_in_position(x, y)
        if control:
            control.mouse_enter(
                x - control.offsetx,
                y - control.offsety,
            )
        self.cursor_in = control
        if self._hide_timer is not None:
            self._hide_timer.cancel()
            self._hide_timer = None

    def process_pointer_leave(self, x, y):  # noqa: N802
        if self.cursor_in:
            self.cursor_in.mouse_leave(
                x - self.cursor_in.offsetx,
                y - self.cursor_in.offsety,
            )
            self.cursor_in = None
        if self.hide_on_mouse_leave:
            self._hide_timer = self.qtile.call_later(self.hide_interval, self.kill)

    def process_pointer_motion(self, x, y):  # noqa: N802
        control = self.get_control_in_position(x, y)
        if self.cursor_in and control is not self.cursor_in:
            self.cursor_in.mouse_leave(
                x - self.cursor_in.offsetx,
                y - self.cursor_in.offsety,
            )
        if control:
            control.mouse_enter(
                x - control.offsetx,
                y - control.offsety,
            )

        self.cursor_in = control

    def process_key_press(self, keycode):
        if keycode in self.keys["close"]:
            self.kill()
            return

        if not self.keyboard_navigation:
            return

        self.unfocus()

        if self._focused is None and self.initial_focus is None:
            self._focused = self.focusable_controls[0]

        # Variable to track next control for navigation
        control = None

        # Default behaviour is to move to the next control in the list
        # Direction can be reversed by setting this to -1
        step = 1
        if keycode in self.keys["left"]:
            control = self.find_nearest_control("left")
            step = -1
        elif keycode in self.keys["up"]:
            control = self.find_nearest_control("up")
            step = 0
        elif keycode in self.keys["right"]:
            control = self.find_nearest_control("right")
        elif keycode in self.keys["down"]:
            control = self.find_nearest_control("down")
            step = 0
        elif keycode in self.keys["select"]:
            if self._focused:
                self._focused.button_press(0, 0, 1)
                if self.close_on_click:
                    self.kill()
            return
        elif keycode in self.keys["step"]:
            pass
        else:
            return

        if not control and self.focusable_controls:
            try:
                idx = self.focusable_controls.index(self._focused)
            except IndexError:
                idx = 0
            idx = (idx + step) % len(self.focusable_controls)
            control = self.focusable_controls[idx]

        if control:
            control.focus()

            self.draw()

    def fake_key_press(self, keycode):
        self.process_key_press(self.qtile.core.keysym_from_name(keycode))

    def find_nearest_control(self, direction):
        controls = []
        if direction == "left":
            controls = [c for c in self.controls if self._focused.is_left(c) and c.can_focus]
        elif direction == "right":
            controls = [c for c in self.controls if self._focused.is_right(c) and c.can_focus]
        elif direction == "up":
            controls = [c for c in self.controls if self._focused.is_above(c) and c.can_focus]
        elif direction == "down":
            controls = [c for c in self.controls if self._focused.is_below(c) and c.can_focus]

        if controls:
            controls.sort(key=lambda x: self._focused.distance_to(x))
            return controls[0]

    def unfocus(self):
        for c in self.controls:
            c.unfocus()

    def update_controls(self, **updates):
        """
        Update the value of controls in the popup, values are set by using keyword arguments
        e.g. to update the control named ``textbox1`` you need to call
        ``popup.update_controls(textbox1="New text")``. Multiple controls can be updated in the
        same call by adding more ``name=value`` pairs.

        If the control is a PopupImage instance, passing a string will set the primary image
        filename while passing a tuple of two strings will set the primary and highlight image
        filenames. You should use a value of ``None`` if you wish a value to be unchanged.

        The popup will be redrawn automatically after updating the relevant controls.
        """
        for name, value in updates.items():
            if name not in self._updateable_controls:
                logger.warning("Unknown control: %s. Skipping.", name)
                continue

            control = self._updateable_controls[name]

            if isinstance(control, PopupText):
                control.text = value

            elif isinstance(control, PopupImage):
                if isinstance(value, str):
                    control.filename = value

                elif isinstance(value, tuple) and len(value) == 2:
                    filename, highlight = value

                    if filename is not None:
                        control.filename = filename

                    if highlight is not None:
                        control.highlight_filename = highlight

                    control.load_images()

            elif isinstance(control, PopupSlider):
                control.value = value

        self.draw()

        if self.hide_on_timeout:
            self._set_autohide()

    def info(self):
        return {
            "name": self.__class__.__name__.lower(),
            "x": self.popup.x,
            "y": self.popup.y,
            "width": self.popup.width,
            "height": self.popup.height,
            "controls": [control.info() for control in self.controls],
        }


class PopupGridLayout(_PopupLayout):
    """
    The grid layout should be familiar to users who have used Tkinter.

    In addition to the `width` and `height` attributes, the grid layout also
    requires `rows` and `cols` to define the grid. Grid cells are evenly sized.a

    Controls can then be placed in the grid via the `row`, `col`, `row_span` and
    `col_span` parameters.

    For example:

    ::

        PopupGridLayout(rows=6, cols=6, controls=[
            PopupImage(filename="A",row=0, col=2, row_span=2, col_span=2),
            PopupImage(filename="B",row=2, col=2, row_span=2, col_span=2),
            PopupImage(filename="C",row=3, col=1),
            PopupImage(filename="D",row=3, col=4),
            PopupText(row=4,col_span=6),
        ])

    would result in a tooltip looking like:

    ::

        -------------------------
        |   |   |       |   |   |
        ---------   A   ---------
        |   |   |       |   |   |
        -------------------------
        |   |   |       |   |   |
        ---------   B   ---------
        |   | C |       | D |   |
        -------------------------
        |         TEXT          |
        -------------------------
        |   |   |   |   |   |   |
        -------------------------

    row and col are both zero-indexed.
    """

    defaults = [("rows", 2, "Number of rows in grid"), ("cols", 2, "Number of columns in grid")]

    def __init__(self, qtile, **config):
        _PopupLayout.__init__(self, qtile, **config)
        self.add_defaults(PopupGridLayout.defaults)
        self._width = self.rows * round((self.width - 2 * self.margin) / self.rows)
        self._height = self.cols * round((self.height - 2 * self.margin) / self.cols)
        self.width = self._width + 2 * self.margin
        self.height = self._height + 2 * self.margin
        self.col_width = self._width / self.cols
        self.row_height = self._height / self.rows

    def _place_control(self, control):
        if not control.placed:
            control.offsetx = int(control.col * self.col_width) + self.margin
            control.offsety = int(control.row * self.row_height) + self.margin
            control.width = int(control.col_span * self.col_width)
            control.height = int(control.row_span * self.row_height)
            control.placed = True


class PopupRelativeLayout(_PopupLayout):
    """
    The relative layout positions controls based on a percentage of the parent
    tooltip's dimensions.

    The positions are defined with the following parameters:

    ::

        `pos_x`, `pos_y`: top left corner
        `width`, `height`: size of control

    All four of these parameters should be a value between 0 and 1. Values
    outside of this range will generate a warning in the log but will not raise
    an exception.

    For example:

    ::

       PopupRelativeLayout(rows=6, cols=6, controls=[
           PopupImage(filename="A",pos_x=0.1, pos_y=0.2, width=0.5, height=0.5)
       ])

    Would result in a tooltip with dimensions of 200x200 (the default), with an
    image placed at (20, 40) with dimensions of (100, 100).

    Note: images are not stretched but are, instead, centered within the rect.
    """

    def _place_control(self, control):
        def is_relative(val):
            """
            Relative layout positions controls based on percentage of
            parent's size so check value is in range.
            """
            return 0 <= val <= 1

        if not control.placed:
            if not all(
                [
                    is_relative(x)
                    for x in [control.pos_x, control.pos_y, control.width, control.height]
                ]
            ):
                logger.warning(
                    "Control {} using non relative dimensions "
                    "in Relative layout".format(control)
                )

            control.offsetx = int(self._width * control.pos_x) + self.margin
            control.offsety = int(self._height * control.pos_y) + self.margin
            control.width = int(self._width * control.width)
            control.height = int(self._height * control.height)
            control.placed = True


class PopupAbsoluteLayout(_PopupLayout):
    """
    The absolute layout is the simplest layout of all. Controls are placed based
    on the following parameters:

    ::

        `pos_x`, `pos_y`: top left corner
        `width`, `height`: size of control

    No further adjustments are made to the controls.

    Note: the layout currently ignores the ``margin`` attribute i.e. a control
    placed at (0,0) will display there even if a margin is defined.
    """

    def _place_control(self, control):
        if not control.placed:
            control.offsetx = control.pos_x
            control.offsety = control.pos_y
            control.placed = True


class _PopupWidget(configurable.Configurable):
    """
    Base class for controls to be included in tooltip windows.

    This draws heavily on the `base._Widget` class but includes additional
    defaults to allow for positioning within a 2D space.
    """

    defaults = [
        ("width", 50, "width of control"),
        ("height", 50, "height of control"),
        ("pos_x", 0, "x position of control"),
        ("pos_y", 0, "y position of control"),
        ("row", 0, "Row position (for grid layout)"),
        ("col", 0, "Column position (for grid layout)"),
        ("row_span", 1, "Number of rows covered by control"),
        ("col_span", 1, "Number of columns covered by control"),
        ("background", None, "Background colour for control"),
        ("highlight", "#006666", "Highlight colour"),
        (
            "highlight_method",
            "block",
            "How to highlight focused control. Options are 'border' and 'block'.",
        ),
        ("highlight_border", 2, "Border width for focused controls"),
        ("highlight_radius", 5, "Corner radius for highlight"),
        (
            "can_focus",
            "auto",
            "Whether or not control can be focussed. Focussed control will be "
            "highlighted if `highlight` attribute is set. Possible value are: "
            "True, False or 'auto' (which sets to True if a 'Button1' mouse_callback is set).",
        ),
        (
            "mouse_callbacks",
            {},
            "Dict of mouse button press callback functions. Accepts lazy objects.",
        ),
        (
            "name",
            None,
            "A unique name for the control. Is only necessary if you wish to update the control's value via ``popup.update_controls()``.",
        ),
    ]  # type: list[tuple[str, Any, str]]

    offsetx = None
    offsety = None

    def __init__(self, **config):
        configurable.Configurable.__init__(self, **config)
        self.add_defaults(_PopupWidget.defaults)
        if self.can_focus == "auto":
            self.can_focus = bool(self.mouse_callbacks.get("Button1", False))
        self._highlight = False
        self.placed = False
        self.focused = False
        self.configured = False

    def _configure(self, qtile, container):
        self.qtile = qtile
        self.container = container
        self.drawer = container.popup.drawer
        self.configured = True

    def add_callbacks(self, defaults):
        """
        Add default callbacks with a lower priority than user-specified
        callbacks.
        """
        defaults.update(self.mouse_callbacks)
        self.mouse_callbacks = defaults

    def paint(self):
        raise NotImplementedError

    def rectangle(self):
        degrees = math.pi / 180.0
        radius = self.highlight_radius
        delta = radius + self.highlight_border / 2 - 1
        ctx = self.drawer.ctx

        ctx.new_sub_path()

        # Top left
        ctx.arc(
            delta,
            delta,
            radius,
            180 * degrees,
            270 * degrees,
        )

        # Top right
        ctx.arc(
            self.width - delta,
            delta,
            radius,
            -90 * degrees,
            0 * degrees,
        )

        # Bottom right
        ctx.arc(
            self.width - delta,
            self.height - delta,
            radius,
            0 * degrees,
            90 * degrees,
        )

        # Bottom left
        ctx.arc(
            delta,
            self.height - delta,
            radius,
            90 * degrees,
            180 * degrees,
        )

        ctx.close_path()

    def draw(self):
        self.drawer.ctx.save()
        self.drawer.ctx.translate(self.offsetx, self.offsety)
        self.paint()
        self.paint_border()
        self.drawer.ctx.restore()

    def paint_border(self):
        if not (self._highlight and self.highlight_method == "border"):
            return
        self.drawer.set_source_rgb(self.highlight)
        self.drawer.ctx.save()
        self.rectangle()
        self.drawer.ctx.stroke()
        self.drawer.ctx.restore()

    def clear(self, colour):
        if not colour:
            return
        self.drawer.set_source_rgb(colour)
        self.drawer.ctx.save()
        # TODO: OPERATOR_SOURCE replaces background with the new drawing
        # Consider whether OVERLAY is more appropriate (particularly with
        # transparency)
        self.drawer.ctx.set_operator(cairocffi.OPERATOR_SOURCE)
        self.rectangle()
        self.drawer.ctx.fill()
        self.drawer.ctx.restore()

    @property
    def win(self):
        return self.container.popup.win

    @property
    def _background(self):
        """
        This property changes based on whether the `_highlight` variable has been
        set.
        """
        if (
            self._highlight
            and self.highlight
            and self.highlight_method not in ["border", "text", "image"]
        ):
            return self.highlight
        else:
            return self.background

    def mouse_in_control(self, x, y):
        """Checks whether the point (x, y) is inside the control."""
        return all(
            [
                x >= self.offsetx,
                x < self.width + self.offsetx,
                y >= self.offsety,
                y < self.height + self.offsety,
            ]
        )

    def button_press(self, x, y, button):
        name = "Button{0}".format(button)
        if name in self.mouse_callbacks:
            cmd = self.mouse_callbacks[name]
            if isinstance(cmd, LazyCall):
                status, val = self.qtile.server.call(
                    (cmd.selectors, cmd.name, cmd.args, cmd.kwargs)
                )
                if status in (interface.ERROR, interface.EXCEPTION):
                    logger.error("KB command error %s: %s" % (cmd.name, val))
            else:
                cmd()

    def button_release(self, x, y, button):
        pass

    def mouse_enter(self, x, y):
        if self.can_focus and self.highlight and not self._highlight:
            self.focus()
            self.container.draw()

    def mouse_leave(self, x, y):
        if self.can_focus and self._highlight:
            self.unfocus()
            self.container.draw()

    def info(self):
        return {
            "name": self.name or self.__class__.__name__.lower(),
            "x": self.offsetx,
            "y": self.offsety,
            "width": self.width,
            "height": self.height,
        }

    def focus(self):
        self.container.unfocus()
        self._highlight = True
        self.container._focused = self

    def unfocus(self):
        self._highlight = False

    def is_left(self, target):
        """Returns True if `target` midpoint is to left of current control."""
        if not isinstance(target, _PopupWidget):
            return False

        return (target.offsetx + target.width / 2) <= self.offsetx

    def is_right(self, target):
        """Returns True if `target` midpoint is to right of current control."""
        if not isinstance(target, _PopupWidget):
            return False

        return (target.offsetx + target.width / 2) > (self.offsetx + self.width)

    def is_above(self, target):
        """Returns True if `target` midpoint is above current control."""
        if not isinstance(target, _PopupWidget):
            return False

        return (target.offsety + target.height / 2) <= self.offsety

    def is_below(self, target):
        """Returns True if `target` midpoint is below current control."""
        if not isinstance(target, _PopupWidget):
            return False

        return (target.offsety + target.height / 2) >= self.offsety + self.height

    def distance_to(self, target):
        """Return distance between midpoints."""
        if not isinstance(target, _PopupWidget):
            return 100000

        dx = (target.offsetx + target.width / 2) - (self.offsetx + self.width / 2)
        dy = (target.offsety + target.height / 2) - (self.offsety + self.height / 2)

        return math.sqrt(dx**2 + dy**2)

    def finalize(self):
        pass


class PopupText(_PopupWidget):
    """Simple control to display text."""

    defaults = [
        ("font", "sans", "Font name"),
        ("fontsize", 12, "Font size"),
        ("foreground", "#ffffff", "Font colour"),
        (
            "foreground_highlighted",
            None,
            "Font colour when highlighted via `block` (None to use foreground value)",
        ),
        ("highlight_method", "block", "Available options: 'border', 'block' or 'text'."),
        ("h_align", "left", "Text alignment: left, center or right."),
        ("v_align", "middle", "Vertical alignment: top, middle or bottom."),
        ("wrap", False, "Wrap text in layout"),
    ]

    def __init__(self, text="", **config):
        _PopupWidget.__init__(self, **config)
        self.add_defaults(PopupText.defaults)
        self._text = text

    def _configure(self, qtile, container):
        _PopupWidget._configure(self, qtile, container)
        self.layout = self.drawer.textlayout(
            self._text,
            self.foreground,
            self.font,
            self.fontsize,
            None,
            markup=False,
            wrap=self.wrap,
        )
        self.layout.layout.set_alignment(pangocffi.ALIGNMENTS[self.h_align])
        self.layout.width = self.width

    def _set_layout_colour(self):
        if self.highlight_method == "text" and self._highlight:
            self.layout.colour = self.highlight
        elif (
            self.highlight_method == "block"
            and self.foreground_highlighted is not None
            and self._highlight
        ):
            self.layout.colour = self.foreground_highlighted
        else:
            self.layout.colour = self.foreground

    def paint(self):
        self._set_layout_colour()

        if self.v_align == "top":
            y = 0
        elif self.v_align == "bottom":
            y = self.height - self.layout.height
        else:
            y = (self.height - self.layout.height) // 2

        self.clear(self._background)
        self.layout.draw(0, y)

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, val):
        self._text = val
        self.layout.text = self._text
        self.draw()

    def info(self):
        info = _PopupWidget.info(self)
        info["text"] = self.text
        return info


class PopupSlider(_PopupWidget):
    """
    Control to display slider/progress bar.

    Bar can be displayed horizontally (draws left-to-right) or vertically
    (bottom-to-top).

    In addition, a border can be drawn around the bar using the
    ``bar_border_colour/size/margin`` parameters.
    """

    defaults = [
        ("min_value", 0, "Minimum value"),
        ("max_value", 1.0, "Maximum value"),
        ("horizontal", True, "Orientation. False = vertical"),
        ("colour_below", "#ffffff", "Colour for bar below value"),
        ("colour_above", "#888888", "Colour for bar above value"),
        ("bar_size", 2, "Thickness of bar"),
        ("marker_size", 10, "Size of marker"),
        ("marker_colour", "#bbbbbb", "Colour of marker"),
        ("end_margin", 5, "Gap between edge of control and ends of the bar/border"),
        ("bar_border_colour", "ffffff", "Colour of border drawn around bar"),
        ("bar_border_size", 0, "Thickness of border around bar"),
        ("bar_border_margin", 0, "Size of gap between border and bar"),
    ]  # type: list[tuple[str, Any, str]]

    def __init__(self, value=None, **config):
        _PopupWidget.__init__(self, **config)
        self.add_defaults(PopupSlider.defaults)
        self._value = self._check_value(value)

    def _check_value(self, val):
        if val is None or type(val) not in (int, float):
            return self.min_value
        return min(max(val, self.min_value), self.max_value)

    def _configure(self, qtile, container):
        _PopupWidget._configure(self, qtile, container)
        self.full_bar_depth = (self.bar_border_size + self.bar_border_margin) * 2 + self.bar_size
        self.full_bar_length = self.length - self.end_margin * 2
        self.bar_length = (
            self.full_bar_length - (self.bar_border_size + self.bar_border_margin) * 2
        )

    def paint(self):
        self.clear(self._background)

        ctx = self.drawer.ctx
        ctx.save()

        if not self.horizontal:
            ctx.rotate(-90 * math.pi / 180.0)
            ctx.translate(-self.length, 0)

        if self.bar_border_size:
            ctx.save()
            ctx.translate(self.end_margin, (self.depth - self.full_bar_depth) // 2)
            ctx.set_line_width(self.bar_border_size)
            self.drawer.set_source_rgb(self.bar_border_colour)
            ctx.rectangle(0, 0, self.full_bar_length, self.full_bar_depth)
            ctx.stroke()
            ctx.restore()

        ctx.translate(
            self.end_margin + self.bar_border_size + self.bar_border_margin, self.depth // 2
        )
        ctx.set_line_width(self.bar_size)

        if self.percentage > 0:
            ctx.new_sub_path()
            self.drawer.set_source_rgb(self.colour_below)
            ctx.move_to(0, 0)
            ctx.line_to(self.bar_length * self.percentage, 0)
            ctx.stroke()

        if self.percentage < 1:
            ctx.new_sub_path()
            self.drawer.set_source_rgb(self.colour_above)
            ctx.move_to(self.bar_length * self.percentage, 0)
            ctx.line_to(self.bar_length, 0)
            ctx.stroke()

        if self.marker_size:
            self.drawer.set_source_rgb(self.marker_colour)
            ctx.arc(self.bar_length * self.percentage, 0, self.marker_size / 2, 0, math.pi * 2)
            ctx.fill()

        ctx.restore()

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        self._value = self._check_value(val)
        self.draw()

    @property
    def percentage(self):
        return (self.value - self.min_value) / (self.max_value - self.min_value)

    @property
    def length(self):
        if self.horizontal:
            return self.width
        else:
            return self.height

    @property
    def depth(self):
        if self.horizontal:
            return self.height
        else:
            return self.width

    def info(self):
        info = _PopupWidget.info(self)
        info["value"] = self.value
        return info


class PopupImage(_PopupWidget):
    """
    Control to display an image.

    Image will be scaled (locked aspect ratio) to fit within the control rect.
    The image will also be centered vertically and horizontally.
    """

    defaults = [
        ("filename", None, "path to image file."),
        (
            "highlight_filename",
            None,
            "path to image to be displayed when highlight method is 'image'",
        ),
        (
            "highlight_method",
            "block",
            "How to highlight focused control. Options are 'image', 'border', 'block' and 'mask'. "
            "'mask' is experimental and will replace the image with the 'highlight' colour "
            "masked by the image. Works best with solid icons on a transparent background.",
        ),
    ]

    def __init__(self, **config):
        _PopupWidget.__init__(self, **config)
        self.add_defaults(PopupImage.defaults)

    def _configure(self, qtile, container):
        _PopupWidget._configure(self, qtile, container)
        self.img = None

        if self.highlight_method == "image" and self.highlight_filename is None:
            logger.warning("No highlight image provided.")
            self.highlight_method == "block"

        self.highlight_img = None
        self.load_images()

    def load_images(self):
        self.img = self._load_image(self.filename)

        if self.highlight_filename is not None:
            self.highlight_img = self._load_image(self.highlight_filename)

    def _load_image(self, filename):
        if filename.startswith("http"):
            img = Img.from_url(filename)

        else:
            filename = os.path.expanduser(filename)
            if not os.path.exists(filename):
                logger.warning("Image does not exist: %s", filename)
                return

            img = Img.from_path(filename)

        if (img.width / img.height) >= (self.width / self.height):
            img.scale(width_factor=(self.width / img.width), lock_aspect_ratio=True)
        else:
            img.scale(height_factor=(self.height / img.height), lock_aspect_ratio=True)

        return img

    def paint(self):
        self.clear(self._background)
        if self.highlight_method == "mask" and self._highlight:
            return
        self.drawer.ctx.save()
        self.drawer.ctx.translate(
            int((self.width - self.img.width) / 2), int((self.height - self.img.height) / 2)
        )
        if self._highlight and self.highlight_method == "image":
            pattern = self.highlight_img.pattern
        else:
            pattern = self.img.pattern
        self.drawer.ctx.set_source(pattern)
        self.drawer.ctx.paint()
        self.drawer.ctx.restore()

    def info(self):
        info = _PopupWidget.info(self)
        info["image"] = self.filename
        return info

    def clear(self, colour):
        if not (colour and self.highlight_method == "mask" and self._highlight):
            _PopupWidget.clear(self, colour)
            return

        self.drawer.set_source_rgb(colour)
        self.drawer.ctx.save()
        self.drawer.ctx.set_operator(cairocffi.OPERATOR_SOURCE)
        self.drawer.ctx.mask_surface(self.img.surface, 0, 0)
        self.drawer.ctx.fill()
        self.drawer.ctx.restore()


class ControlBar:
    """
    Widget's rely on various attributes of their parent `Bar`. However,
    in a popup window there is no `Bar` so we need to create an object
    which provides the correct attributes but pulls these properties from
    the popup window instead.
    """

    def __init__(self, control: _PopupLayout):
        self.control = control
        self.horizontal = control.horizontal
        self.left = control.vertical_left

    @property
    def width(self):
        return self.control.width

    @property
    def height(self):
        return self.control.height

    @property
    def window(self):
        return self.control.container.popup.win

    @property
    def background(self):
        return self.control._background or self.control.container.popup.background

    @property
    def size(self):
        if self.horizontal:
            return self.height
        return self.width

    @property
    def border_width(self):
        return (0, 0, 0, 0)

    @property
    def screen(self):
        class Obj:
            def __init__(self, parent):
                self.parent = parent

            @property
            def top(self):
                if self.parent.horizontal:
                    return self.parent

            @property
            def bottom(self):
                return False

            @property
            def left(self):
                if not self.parent.horizontal and self.parent.left:
                    return self.parent

            @property
            def right(self):
                if not self.parent.horizontal and not self.parent.left:
                    return self.parent

        return Obj(self)

    def draw(self):
        self.control.draw()


class PopupWidget(_PopupWidget):
    """
    Control to display a Qtile widget in a Popup window.

    Mouse clicks are passed on to the widgets.

    Currently, widgets will be sized based on the dimensions of the control.
    This will override any width/stretching settings in thw widget.
    """

    defaults = [
        ("widget", None, "Widget instance."),
        ("horizontal", True, "Widget is horizontal. False = vertical."),
        (
            "vertical_left",
            True,
            "If using vertical orientation, mimic bar on left hand side of screen "
            "(causes text to read from bottom to top).",
        ),
    ]

    def __init__(self, **config):
        _PopupWidget.__init__(self, **config)
        self.add_defaults(PopupWidget.defaults)
        self.add_callbacks({"Button1": self.widget.draw})

    def _configure(self, qtile, container):
        _PopupWidget._configure(self, qtile, container)
        if self.widget is None:
            logger.warning("PopupWidget control created with no widget.")
            return

        # Force the widget's length to be the same as the control
        self.widget.length_type = bar.STATIC
        self.widget.length = self.width if self.horizontal else self.height

        # Configure the widget
        self.widget._configure(qtile, ControlBar(self))
        self.widget.configured = True

        # Set the correct offsets for positioning the widget in the popup window
        self.widget.offsetx = self.offsetx
        self.widget.offsety = self.offsety

    def paint(self):
        # Not sure why but the widget draw function needs to be called outside of the
        # popup's draw call... Will/may investigate later...
        self.qtile.call_soon(self.widget.draw)

    def button_press(self, x, y, button):
        _PopupWidget.button_press(self, x, y, button)
        self.widget.button_press(x, y, button)

    def info(self):
        info = _PopupWidget.info(self)
        info["widget"] = self.widget.info() if self.widget else dict()
        return info

    def finalize(self):
        self.widget.finalize()
