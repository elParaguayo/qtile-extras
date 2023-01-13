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
from copy import deepcopy
from typing import TYPE_CHECKING

from libqtile.command.base import expose_command
from libqtile.configurable import Configurable, ExtraFallback
from libqtile.log_utils import logger
from libqtile.popup import Popup

from qtile_extras.popup.menu import PopupMenu

if TYPE_CHECKING:
    from typing import Any, Callable  # noqa: F401


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

    def __init__(self, **kwargs):
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
            y = min(self.offsety + self.bar.window.y, screen.height - height)

        else:
            x = screen.width - self.bar.width - width
            y = min(self.offsety + self.bar.window.y, screen.height - height)

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
        ("icon_theme", None, "Icon theme for DBus menu items"),
    ]  # type: list[tuple[str, Any, str]]

    def __init__(self, **config):
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
            "icon_theme": self.icon_theme,
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


class ExtendedPopupMixin(_BaseMixin):
    """
    Mixin that provides the ability for a widget to display extended
    detail in popups via the Popup toolkit.

    It is not mandatory for widgets to use this if they want to use the
    toolkit. However, the mixin provides some standard variable and
    method names.

    .. list-table::

      * -  ``self.extended_popup``
        - the popup instance or None
      * - ``self._popup_hide_timer``
        - the current timer object for hiding the popup or None
      * - ``self.has_popup``
        - property that returns ``True`` is popup is defined and not killed
      * - ``self.update_popup()``
        - method to call to update popup contents. Should not be overriden
          as it calls ``self._update_popup`` (see below) but only if ``self.has_popup`` is ``True``
      * - ``self._update_popup()``
        - method that actually updates the contents. This will raise a
          ``NotImplementedError`` if called without being overriden.
      * - ``self._set_popup_timer()``
        - sets the timer to kill the popup.
      * - ``self._kill_popup()``
        - kills the popup
      * - ``self.show_popup()``
        - displays the popup. Is also exposed to command interface so can be used
          in ``lazy`` calls etc.

    """

    defaults = [
        ("popup_show_args", {"centered": True}, "Arguments to be passed to ``popup.show()``"),
        ("popup_layout", None, "The popup layout definition"),
        ("popup_hide_timeout", 0, "Number of seconds before popup is hidden (0 to disable)."),
    ]  # type: list[tuple[str, Any, str]]

    def __init__(self, **kwargs):
        self.extended_popup = None
        self._popup_hide_timer = None

    @property
    def has_popup(self):
        return self.extended_popup is not None and not getattr(
            self.extended_popup, "_killed", True
        )

    def update_popup(self):
        """
        This is the primary call to update the popup's contents and is the method that should be called
        by the widget. It is not anticipated that this method would be overriden.
        """
        if not self.has_popup:
            return

        self._update_popup()

    def _update_popup(self):
        """
        This method mus be overriden by individual widgets and should contain a call
        to `self.extended_popup.update_controls` in order to set the value of the controls
        being displayed by the popup.
        """
        raise NotImplementedError("Widgets need to override this method.")

    def _set_popup_timer(self):
        if not self.popup_hide_timeout:
            return

        if self._popup_hide_timer is not None:
            self._popup_hide_timer.cancel()

        self.timeout_add(self.popup_hide_timeout, self._kill_popup)

    def _kill_popup(self):
        if self.has_popup:
            self.extended_popup.kill()

        self._popup_hide_timer = None

    @expose_command()
    def show_popup(self):
        """Method to display the popup."""
        if not self.has_popup:
            self.extended_popup = deepcopy(self.popup_layout)
            self.extended_popup._configure(self.qtile)

        self.update_popup()

        self.extended_popup.show(**self.popup_show_args)
        self._set_popup_timer()

    def update_or_show_popup(self):
        if self.has_popup:
            self.update_popup()
        else:
            self.show_popup()


class ProgressBarMixin(_BaseMixin):
    """
    Mixin to allow widgets to display progress bars.

    Bar is drawn based on a ``bar_value`` between 0.0 and 1.0 inclusive.

    To use it, subclass and add this to ``__init__``:

    .. code:: python

        ProgressBarMixin.__init__(self, **kwargs)
        self.add_defaults(ProgressBarMixin.defaults)

    To draw the bar, you need to call ``self.bar_draw()``. The method take a
    number of optional parameters. Where these are not set in the method call
    then the instance version i.e. ``self.parameter_name`` will be used insted.

    ``bar.draw`` optional parameters:

    - ``x_offset`` (default 0): horizontal positioning of the bar
    - ``bar_colour``: colour of the bar
    - ``bar_background``: colour drawn behind the bar (i.e. to show extent of bar)
    - ``bar_text``: text to draw on bar,
    - ``bar_text_foreground``: text colour,
    - ``bar_value``: percentage of bar to fill

    .. note::

        The widget should ensure that its width is sufficient to display the bar
        (the ``bar_width`` property is relevant here).

    """

    defaults = [
        ("bar_width", 75, "Width of bar."),
        ("bar_height", None, "Height of bar (None = full bar height)."),
        ("bar_background", None, "Colour of bar background."),
        (
            "bar_colour",
            "00ffff",
            "Colour of bar (NB this setting may be overridden by other widget settings).",
        ),
        ("bar_text", "", "Text to show over bar"),
        ("bar_text_font", None, "Font to use for bar text"),
        ("bar_text_fontsize", None, "Fontsize for bar text"),
        ("bar_text_foreground", "ffffff", "Colour for bar text"),
    ]

    bar_text_font = ExtraFallback("bar_text_font", "font")
    bar_text_fontsize = ExtraFallback("bar_text_fontsize", "fontsize")
    bar_text_foreground = ExtraFallback("bar_text_foreground", "foreground")

    def __init__(self, **kwargs):
        self.bar_value = 0

    def draw_bar(
        self,
        x_offset=0,
        bar_colour=None,
        bar_background=None,
        bar_text=None,
        bar_text_foreground=None,
        bar_value=None,
    ):
        if self.bar_height is None:
            self.bar_height = self.bar.height

        percentage = bar_value or self.bar_value

        self.drawer.ctx.save()
        self.drawer.ctx.translate(x_offset, (self.bar.height - self.bar_height) // 2)

        if self.bar_background and percentage < 1:
            self.drawer.set_source_rgb(bar_background or self.bar_background)
            self.drawer.fillrect(0, 0, self.bar_width, self.bar_height, 1)

        # Draw progress bar
        self.drawer.set_source_rgb(bar_colour or self.bar_colour)
        self.drawer.fillrect(0, 0, self.bar_width * percentage, self.bar_height, 1)

        self.drawer.ctx.restore()

        if bar_text or self.bar_text:
            if self.bar_text_fontsize is None:
                self.bar_text_fontsize = self.bar.height - self.bar.height / 5

            self.drawer.ctx.save()
            # Create a text box
            layout = self.drawer.textlayout(
                bar_text or self.bar_text,
                bar_text_foreground or self.bar_text_foreground,
                self.bar_text_font,
                self.bar_text_fontsize,
                None,
                wrap=False,
            )

            # We want to centre this vertically
            y_offset = (self.bar.height - layout.height) / 2

            # Set the layout as wide as the widget so text is centred
            layout.width = self.bar_width

            self.drawer.ctx.translate(x_offset, y_offset)
            layout.draw(0, 0)

            self.drawer.ctx.restore()
