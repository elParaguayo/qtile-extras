# Copyright (c) 2008, Aldo Cortesi. All rights reserved.
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
import libqtile.bar
from libqtile.utils import has_transparency


class Bar(libqtile.bar.Bar):
    """
    A modded version of the bar, which can display a border around it.
    """

    _experimental = True

    defaults = [
        ("border_color", "#000000", "Border colour as str or list of str [N E S W]"),
        ("border_width", 0, "Width of border as int or list of ints [N E S W]"),
    ]

    _screenshots = [("bar.png", "")]

    def __init__(self, widgets, size, **config):
        libqtile.bar.Bar.__init__(self, widgets, size, **config)
        self.add_defaults(Bar.defaults)

        if isinstance(self.margin, int):
            self.margin = [self.margin] * 4

        if isinstance(self.border_width, int):
            self.border_width = [self.border_width] * 4

    def _configure(self, qtile, screen):
        libqtile.bar.Gap._configure(self, qtile, screen)

        if sum(self.margin) or sum(self.border_width):

            if isinstance(self.border_color, str):
                self.border_color = [self.border_color] * 4

            # Increase the margin size for the border. The border will be drawn
            # in this space so the empty space will just be the margin.
            self.margin = [m + b for m, b in zip(self.margin, self.border_width)]

            if self.horizontal:
                self.x += self.margin[3] - self.border_width[3]
                self.width -= self.margin[1] + self.margin[3]
                self.length = self.width
                if self.size == self.initial_size:
                    self.size += self.margin[0] + self.margin[2]
                if self.screen.top is self:
                    self.y += self.margin[0] - self.border_width[0]
                else:
                    self.y -= self.margin[2] + self.border_width[2]

            else:
                self.y += self.margin[0] - self.border_width[0]
                self.height -= self.margin[0] + self.margin[2]
                self.length = self.height
                self.size += self.margin[1] + self.margin[3]
                if self.screen.left is self:
                    self.x += self.margin[3]
                else:
                    self.x -= self.margin[1]

        width = self.width + (self.border_width[1] + self.border_width[3])
        height = self.height + (self.border_width[0] + self.border_width[2])

        for w in self.widgets:
            # Executing _test_orientation_compatibility later, for example in
            # the _configure() method of each widget, would still pass
            # test/test_bar.py but a segfault would be raised when nosetests is
            # about to exit
            w._test_orientation_compatibility(self.horizontal)

        if self.window:
            # We get _configure()-ed with an existing window when screens are getting
            # reconfigured but this screen is present both before and after
            self.window.place(self.x, self.y, width, height, 0, None)
        else:
            # Whereas we won't have a window if we're startup up for the first time or
            # the window has been killed by us no longer using the bar's screen

            # X11 only:
            # To preserve correct display of SysTray widget, we need a 24-bit
            # window where the user requests an opaque bar.
            if self.qtile.core.name == "x11":
                depth = (
                    32
                    if has_transparency(self.background)
                    else self.qtile.core.conn.default_screen.root_depth
                )

                self.window = self.qtile.core.create_internal(
                    self.x, self.y, width, height, depth
                )

            else:
                self.window = self.qtile.core.create_internal(self.x, self.y, width, height)

            self.window.opacity = self.opacity
            self.window.unhide()

            self.drawer = self.window.create_drawer(width, height)
            self.drawer.clear(self.background)

            self.window.process_window_expose = self.draw
            self.window.process_button_click = self.process_button_click
            self.window.process_button_release = self.process_button_release
            self.window.process_pointer_enter = self.process_pointer_enter
            self.window.process_pointer_leave = self.process_pointer_leave
            self.window.process_pointer_motion = self.process_pointer_motion
            self.window.process_key_press = self.process_key_press

        self.crashed_widgets = []
        if self._configured:
            for i in self.widgets:
                self._configure_widget(i)
        else:
            for idx, i in enumerate(self.widgets):
                if i.configured:
                    i = i.create_mirror()
                    self.widgets[idx] = i
                success = self._configure_widget(i)
                if success:
                    qtile.register_widget(i)

        self._remove_crashed_widgets()
        self.draw()
        self._resize(self.length, self.widgets)
        self._configured = True

    def _actual_draw(self):
        self.queued_draws = 0
        self._resize(self.length, self.widgets)

        # We draw the border before the widgets
        if self.border_width:

            # The border is drawn "outside" of the bar (i.e. not in the space that the
            # widgets occupy) so we need to add the additional space
            width = self.width + self.border_width[1] + self.border_width[3]
            height = self.height + self.border_width[0] + self.border_width[2]

            # line_opts is a list of tuples where each tuple represents the borders
            # in the order N, E, S, W. The border tuple contains two pairs of
            # co-ordinates for the start and end of the border.
            line_opts = [
                ((0, self.border_width[0] * 0.5), (width, self.border_width[0] * 0.5)),
                (
                    (width - (self.border_width[1] * 0.5), self.border_width[0]),
                    (width - (self.border_width[1] * 0.5), height - self.border_width[2]),
                ),
                (
                    (0, height - self.border_width[2] + (self.border_width[2] * 0.5)),
                    (width, height - self.border_width[2] + (self.border_width[2] * 0.5)),
                ),
                (
                    (self.border_width[3] * 0.5, self.border_width[0]),
                    (self.border_width[3] * 0.5, height - self.border_width[2]),
                ),
            ]

            self.drawer.clear(self.background)

            for border_width, colour, opts in zip(
                self.border_width, self.border_color, line_opts
            ):

                if not border_width:
                    continue

                move_to, line_to = opts

                # Draw the border
                self.drawer.set_source_rgb(colour)
                self.drawer.ctx.set_line_width(border_width)
                self.drawer.ctx.move_to(*move_to)
                self.drawer.ctx.line_to(*line_to)
                self.drawer.ctx.stroke()

            self.drawer.draw(0, 0)

        for i in self.widgets:
            i.draw()
        end = i.offset + i.length  # pylint: disable=undefined-loop-variable
        # we verified that self.widgets is not empty in self.draw(), see above.
        if end < self.length:
            if self.horizontal:
                self.drawer.draw(offsetx=end, width=self.length - end)
            else:
                self.drawer.draw(offsety=end, height=self.length - end)


def inject_bar_border(classdef):
    @property
    def width(self):
        if self.bar.horizontal:
            return self.length
        return self.bar.width

    @property
    def height(self):
        if self.bar.horizontal:
            return self.bar.height
        return self.length

    def _offset_draw(self, offsetx=0, offsety=0, width=None, height=None):
        if self.bar.horizontal:
            self._realdraw(offsetx=offsetx, offsety=self.offsety, width=width, height=height)
        else:
            self._realdraw(offsetx=self.offsetx, offsety=offsety, width=width, height=height)

    def _configure(self, qtile, bar):
        self._old_bar_configure(qtile, bar)
        self._realdraw = self.drawer.draw
        self.drawer.draw = self._offset_draw

    if not hasattr(classdef, "_injected_offsets"):

        classdef._offset_draw = _offset_draw
        classdef._old_bar_configure = classdef._configure
        classdef._configure = _configure
        classdef._injected_offsets = True
        classdef.height = height
        classdef.width = width
