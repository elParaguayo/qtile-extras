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

from libqtile.configurable import Configurable
from libqtile.log_utils import logger
from libqtile.popup import Popup

from qtile_extras.popup.menu import PopupMenu

if TYPE_CHECKING:
    from typing import Any, Callable


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

            elif (
                isinstance(self.tooltip_padding, list)
                and len(self.tooltip_padding) == 2
                and all(isinstance(m, int) for m in self.tooltip_padding)
            ):
                self._tooltip_padding = self.tooltip_padding

            else:
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


class MenuMixin(Configurable, _BaseMixin):
    """
    Provides the relevant settings to help configure a context menu to
    be displayed by the widget.

    The use of the mixin ensures that all menus use the same property names which
    allows users to theme menus more easily e.g. by setting values in
    ``widget_defaults``.
    """

    _build_menu = PopupMenu.generate  # type: Callable

    defaults = [
        ("menu_font", "sans", "Font for menu text"),
        ("menu_fontsize", 12, "Font size for menu text"),
        ("menu_foreground", "ffffff", "Font colour for menu text"),
        ("menu_foreground_disabled", "aaaaaa", "Font colour for disabled menu items"),
        (
            "menu_foreground_highlighted",
            None,
            "Font colour for highlighted item (None to use menu_foreground value)",
        ),
        ("menu_background", "333333", "Background colour for menu"),
        ("menu_border", "111111", "Menu border colour"),
        ("menu_border_width", 0, "Width of menu border"),
        ("menu_icon_size", 12, "Size of icons in menu (where available)"),
        ("menu_offset_x", 0, "Fine tune x position of menu"),
        ("menu_offset_y", 0, "Fine tune y position of menu"),
        ("separator_colour", "555555", "Colour of menu separator"),
        (
            "highlight_colour",
            "0060A0",
            "Colour of highlight for menu items (None for no highlight)",
        ),
        ("highlight_radius", 0, "Radius for menu highlight"),
        (
            "menu_row_height",
            None,
            (
                "Height of menu row (NB text entries are 2 rows tall, separators are 1 row tall.) "
                '"None" will attempt to calculate height based on font size.'
            ),
        ),
        ("menu_width", 200, "Context menu width"),
        ("show_menu_icons", True, "Show icons in context menu"),
        ("hide_after", 0.5, "Time in seconds before hiding menu atfer mouse leave"),
        ("opacity", 1, "Menu opactity"),
    ]  # type: list[tuple[str, Any, str]]

    def __init__(self, **config):
        self.add_defaults(MenuMixin.defaults)
        self.menu_config = {
            "font": self.menu_font,
            "fontsize": self.menu_fontsize,
            "foreground": self.menu_foreground,
            "foreground_disabled": self.menu_foreground_disabled,
            "foreground_highlighted": self.menu_foreground_highlighted,
            "background": self.menu_background,
            "border": self.menu_border,
            "border_width": self.menu_border_width,
            "icon_size": self.menu_icon_size,
            "colour_above": self.separator_colour,
            "highlight": self.highlight_colour,
            "highlight_radius": self.highlight_radius,
            "row_height": self.menu_row_height,
            "menu_width": self.menu_width,
            "show_menu_icons": self.show_menu_icons,
            "hide_after": self.hide_after,
            "opacity": self.opacity,
        }

        self.menu: PopupMenu | None = None

    def set_menu_position(self, x: int, y: int) -> tuple[int, int]:
        """
        Set the x and y coordinates of the menu.

        The method receivs and x and y value which is calculated during
        ``self.display_menu``. The x and y coordinates place the menu at
        the start of the widget and adjacent to the bar. The values have also
        already been adjusted to ensure that the menu will fit on the screen.

        This method can be overriden if menus need to adjust the placement of the menu
        e.g. if the widget has multiple items with separate menus.

        NB: if a user has defined ``menu_offset_x`` or ``menu_offset_y`` these will
        be applied after this method and so should not be included here.
        """
        return x, y

    def display_menu(self, menu_items):
        """
        Method to display the menu.

        By default, the menu will be placed by the widget using the widget's offset along the bar
        and the bar's size. If the position needs to be adjusted then the x and y coordinates should
        be set by overriding the ``set_menu_position`` method.
        """
        if not menu_items:
            return

        if self.menu and not self.menu._killed:
            self.menu.kill()

        self.menu = self._build_menu(self.qtile, menu_items, **self.menu_config)

        screen = self.bar.screen

        if screen.top == self.bar:
            x = min(self.offsetx, self.bar.width - self.menu.width - 2 * self.menu_border_width)
            y = self.bar.height

        elif screen.bottom == self.bar:
            x = min(self.offsetx, self.bar.width - self.menu.width - 2 * self.menu_border_width)
            y = screen.height - self.bar.height - self.menu.height - 2 * self.menu_border_width

        elif screen.left == self.bar:
            x = self.bar.width
            y = min(self.offsety, screen.height - self.menu.height - 2 * self.menu_border_width)

        else:
            x = screen.width - self.bar.width - self.menu.width - 2 * self.menu_border_width
            y = min(self.offsety, screen.height - self.menu.height - 2 * self.menu_border_width)

        x, y = self.set_menu_position(x, y)

        # Adjust the position for any user-defined settings
        x += self.menu_offset_x
        y += self.menu_offset_y

        self.menu.show(x, y)


class DbusMenuMixin(MenuMixin):
    """
    Builds a menu from ``qtile_extras.resources.dbusmenu.DBusMenuItem``
    objects.

    Should be used where a widget is accessing menu data over DBus.

    When calling ``qtile_extras.resources.dbusmenu.DBusMenu.get_menu``,
    the callback should be set to the widget's ``display_menu`` method.
    """
    _build_menu = PopupMenu.from_dbus_menu  # type: Callable
