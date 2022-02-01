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
from typing import TYPE_CHECKING

from libqtile.log_utils import logger
from libqtile.popup import Popup

if TYPE_CHECKING:
    from typing import Any


class _BaseMixin:
    """Base class to help docs only show mixins."""

    pass


class TooltipMixin(_BaseMixin):
    """
    Mixin that provides a tooltip for widgets.

    To use it, subclass and add this to ``__init__``:

    .. code:: python

        TooltipMixin.__init__(self, **kwargs)
        self.add_defaults(TooltipMixin.defaults)

    Widgets should set ``self.tooltip_text`` to change display text.
    """

    defaults = [
        ("tooltip_delay", 1, "Time in seconds before tooltip displayed"),
        ("tooltip_background", "#000000", "Background colour for tooltip"),
        ("tooltip_color", "#ffffff", "Font colur for tooltop"),
        ("tooltip_font", "sans", "Font colour for tooltop"),
        ("tooltip_fontsize", 12, "Font size for tooltop"),
        ("tooltip_padding", 4, "int for all sides or list for [top/bottom, left/right]"),
    ]  # type: list[tuple[str, Any, str]]

    _screenshots = [("tooltip_mixin.gif", "")]

    def __init__(self):
        self._tooltip = None
        self._tooltip_timer = None
        self.tooltip_text = ""
        self.mouse_enter = self._start_tooltip
        self.mouse_leave = self._stop_tooltip
        self._tooltip_padding = None

    def _show_tooltip(self, x, y):

        if self._tooltip_padding is None:
            if isinstance(self.tooltip_padding, int):
                self._tooltip_padding = [self.tooltip_padding] * 2

            elif not (isinstance(self.tooltip_padding, list) and len(self.tooltip_padding) >= 2):
                logger.warning("Invalid tooltip padding. Defaulting to [4, 4]")
                self._tooltip_padding = [4, 4]

        self._tooltip = Popup(
            self.qtile,
            font=self.tooltip_font,
            font_size=self.tooltip_fontsize,
            foreground=self.tooltip_color,
            background=self.tooltip_background,
            vertical_padding=self._tooltip_padding[0],
            horizontal_padding=self._tooltip_padding[1],
            wrap=False,
        )

        # Size the popup
        self._tooltip.text = self.tooltip_text

        height = self._tooltip.layout.height + (2 * self._tooltip.vertical_padding)
        width = self._tooltip.layout.width + (2 * self._tooltip.horizontal_padding)

        self._tooltip.height = height
        self._tooltip.width = width

        # Position the tooltip depending on bar position and orientation
        screen = self.bar.screen

        if screen.top == self.bar:
            x = min(self.offsetx, self.bar.width - width)
            y = self.bar.height

        elif screen.bottom == self.bar:
            x = min(self.offsetx, self.bar.width - width)
            y = screen.height - self.bar.height - height

        elif screen.left == self.bar:
            x = self.bar.width
            y = min(self.offsety, screen.height - height)

        else:
            x = screen.width - self.bar.width - width
            y = min(self.offsety, screen.height - height)

        self._tooltip.x = x
        self._tooltip.y = y

        self._tooltip.clear()
        self._tooltip.place()
        self._tooltip.draw_text()
        self._tooltip.unhide()
        self._tooltip.draw()

    def _start_tooltip(self, x, y):
        if not self.configured or not self.tooltip_text:
            return

        if not self._tooltip_timer and not self._tooltip:
            self._tooltip_timer = self.timeout_add(self.tooltip_delay, self._show_tooltip, (x, y))

    def _stop_tooltip(self, x, y):
        if self._tooltip_timer and not self._tooltip:
            self._tooltip_timer.cancel()
            self._tooltip_timer = None
            return

        else:
            self._tooltip.hide()
            self._tooltip.kill()
            self._tooltip = None
            self._tooltip_timer = None
