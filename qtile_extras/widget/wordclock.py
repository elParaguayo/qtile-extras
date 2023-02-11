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
import importlib
import os
from datetime import datetime, time

import cairocffi
from libqtile import hook
from libqtile.utils import rgb
from libqtile.widget import base

from qtile_extras.popup.toolkit import PopupGridLayout, PopupText
from qtile_extras.resources.wordclock import LANGUAGES


def round_down(num, divisor):
    return num - (num % divisor)


class WordClock(base._Widget):
    """
    A widget to draw a word clock to the screen.

    This is not a traditional widget in that you will not see anything
    displayed in your bar. The widget works in the background and updates
    the screen wallpaper when required. However, having this as a widget
    provides an easy way for users to install and configure the clock.

    The clocks are currently designed to update on 5 minute intervals
    "five past" -> "ten past" etc. This may be changed in the future.

    Custom layouts can be added by referring to the instructions in
    ``qtile_extras/resources/wordclock/english.py``.
    """

    # Dynamically update docstring for supported languages
    __doc__ += """
    .. admonition:: Supported languages

        Available languages: {}
    """.format(
        ", ".join([f"``{lang.capitalize()}``" for lang in LANGUAGES])
    )

    orientations = base.ORIENTATION_BOTH
    defaults = [
        (
            "language",
            "english",
            "Display language. " "Choose from {}.".format(", ".join(f"'{x}'" for x in LANGUAGES)),
        ),
        ("background", "000000", "Background colour."),
        ("inactive", "202020", "Colour for inactive characters"),
        ("active", "00AAAA", "Colour for active characters"),
        ("update_interval", 1, "Interval to check time"),
        ("cache", "~/.cache/qtile-extras", "Location to store wallpaper"),
        ("fontsize", 70, "Font size for letters"),
        ("font", "sans", "Font for text"),
    ]

    _screenshots = [("wordclock.png", "")]

    def __init__(self, **config):
        base._Widget.__init__(self, 0, **config)
        self.add_defaults(WordClock.defaults)
        self.oldtime = None
        self.needs_draw = False
        self.clockfile = None

        # TO DO: Work out why the fontsize set by defaults is ignored
        # unless we try to access it before `setup`
        self.fontsize += 0

        self.cache = os.path.expanduser(self.cache)
        if not os.path.isdir(self.cache):
            os.makedirs(self.cache)

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        hook.subscribe.screens_reconfigured(self.paint_screen)
        self.setup()
        self.clockfile = os.path.join(self.cache, "wordclock.png")

    def update(self, *args):
        """
        Checks the time and calculates which letters should be highlighted.
        """
        nw = datetime.now()

        # Clock works on 5 minute intervals so round time to nearest 5 mins.
        hour = nw.hour
        minute = round_down(nw.minute, 5)

        # Is our language one where we need to increment the hour after 30 mins
        # e.g. 9:40 is "Twenty to ten"
        if self.config.HOUR_INCREMENT and (minute > self.config.HOUR_INCREMENT_TIME):
            hour = (hour + 1) % 24

        # Use a time object so we can use string formatting for the time.
        tm = time(hour, minute)

        # If it's the same as the last update then we don't need to do anything
        if tm != self.oldtime:
            # Morning or afternoon?
            ampm = "am" if nw.hour < 12 else "pm"

            # Load the map
            layout = self.config.MAP

            # Build list of the letters we need
            highlights = list()
            highlights.extend(layout.get("all", []))
            highlights.extend(layout[f"h{tm:%I}"])
            highlights.extend(layout[f"m{tm:%M}"])
            highlights.extend(layout.get(ampm, []))

            # Build a map of all letters saying whether they're on or off
            states = [x in highlights for x in range(len(self.config.LAYOUT))]

            for control, state in zip(self.grid.controls, states):
                control._highlight = state

            self.oldtime = tm

            self.needs_draw = True
            self.draw()

        self.timeout_add(self.update_interval, self.update)

    def load_layout(self):
        """
        Simple method to import the layout. If the module can't be found
        then it defaults to loading the English layout.
        """
        if self.language not in LANGUAGES:
            self.language = "english"

        config = importlib.import_module(f"qtile_extras.resources.wordclock.{self.language}")

        return config

    def setup(self):
        """
        Sets up the grid layour holding the word clock.
        """
        # Get the layout
        self.config = self.load_layout()

        letters = []

        # Loop over the letters
        for row in range(self.config.ROWS):
            for col in range(self.config.COLS):
                idx = (row * self.config.COLS) + col

                # Create a letter object
                cell = PopupText(
                    text=self.config.LAYOUT[idx],
                    row=row,
                    col=col,
                    foreground=self.inactive,
                    h_align="center",
                    v_align="middle",
                    fontsize=self.fontsize,
                    font=self.font,
                    highlight_method="text",
                    highlight=self.active,
                )

                letters.append(cell)

        # Create a grid layout that's the right size
        self.grid = PopupGridLayout(
            self.qtile,
            rows=self.config.ROWS,
            cols=self.config.COLS,
            width=self.bar.screen.width,
            height=self.bar.screen.height,
            controls=letters,
        )

        self.grid._configure()

        # We need to extract the RecordingSurface before it is cleared
        # by the popup `draw` method
        self._draw = self.grid.popup.draw
        self.grid.popup.draw = self.hook_draw

    def hook_draw(self):
        """
        Extracts the popup's surface and writes it to a file before being
        cleared by the popup's drawer.draw() call.
        """
        surface = cairocffi.ImageSurface(
            cairocffi.FORMAT_ARGB32, self.bar.screen.width, self.bar.screen.height
        )
        ctx = cairocffi.Context(surface)
        ctx.set_source_rgba(*rgb(self.background))
        ctx.paint()

        ctx.set_source_surface(self.grid.popup.drawer.surface, 0, 0)
        ctx.paint()
        surface.write_to_png(self.clockfile)

        # Now call the popup's draw to make sure the surface is cleared.
        self._draw()

    def draw(self):
        if not self.needs_draw:
            if self.oldtime is None:
                self.update()
            return

        self.grid.draw()
        self.paint_screen()
        self.needs_draw = False

    def paint_screen(self):
        if not self.clockfile:
            return

        self.bar.screen.paint(self.clockfile)
