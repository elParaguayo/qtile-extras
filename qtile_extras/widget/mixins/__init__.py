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
import socket
from contextlib import contextmanager
from copy import deepcopy
from typing import TYPE_CHECKING

from libqtile.command.base import expose_command
from libqtile.configurable import Configurable, ExtraFallback
from libqtile.log_utils import logger
from libqtile.popup import Popup

from qtile_extras.popup.menu import PopupMenu, PopupMenuItem, PopupMenuSeparator
from qtile_extras.resources.dbusmenu import DBusMenuItem

if TYPE_CHECKING:
    from typing import Any, Callable  # noqa: F401


PI = math.pi


@contextmanager
def socket_context(*args, **kwargs):
    s = socket.socket(*args, **kwargs)
    try:
        yield s
    finally:
        s.close()


def to_rads(degrees):
    return degrees * PI / 180.0


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
            width=self.bar.screen.width // 2,
            height=self.bar.screen.height // 2,
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

        x += screen.x
        y += screen.y

        self._tooltip.x = x
        self._tooltip.y = y

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
        ("highlight_radius", 5, "Radius for menu highlight"),
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
        ("opacity", 1, "Menu opacity"),
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

        self.menu = None

    def display_menu(
        self,
        menu_items: list[PopupMenuItem | PopupMenuSeparator | DBusMenuItem] = list(),
        x: int | float | None = None,
        y: int | float | None = None,
        centered: bool = False,
        warp_pointer: bool = False,
        relative_to: int = 1,
        relative_to_bar: bool = False,
        hide_on_timeout: int | float | None = None,
    ):
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

        custom_x = x
        custom_y = y

        if screen.top is self.bar:
            x = min(self.offsetx, screen.width - self.menu.width - 2 * self.menu_border_width)
            y = self.bar.height + self.bar.margin[0]

        elif screen.bottom == self.bar:
            x = min(self.offsetx, screen.width - self.menu.width - 2 * self.menu_border_width)
            y = (
                screen.height
                - (self.bar.height + self.bar.margin[2])
                - self.menu.height
                - 2 * self.menu_border_width
            )

        elif screen.left == self.bar:
            x = self.bar.width + self.bar.margin[3]
            y = min(self.offsety, screen.height - self.menu.height - 2 * self.menu_border_width)

        else:
            x = (
                screen.width
                - (self.bar.width + self.bar.margin[1])
                - self.menu.width
                - 2 * self.menu_border_width
            )
            y = min(self.offsety, screen.height - self.menu.height - 2 * self.menu_border_width)

        # Adjust the position for any user-defined settings
        x += self.menu_offset_x
        y += self.menu_offset_y

        self.menu.show(
            x=custom_x if custom_x is not None else x,
            y=custom_y if custom_y is not None else y,
            centered=centered,
            warp_pointer=warp_pointer,
            relative_to=relative_to,
            relative_to_bar=relative_to_bar,
            hide_on_timeout=hide_on_timeout,
        )

    def create_menu_item(self, text, **config):
        """
        Create a PopupMenuItem with parameters specified here taking preference over default.
        """
        item_config = {**self.menu_config, **config}
        return PopupMenuItem(text, **item_config)

    def create_menu_separator(self, **config):
        """
        Create a PopupMenuSeparator with parameters specified here taking preference over default.
        """
        item_config = {**self.menu_config, **config}
        return PopupMenuSeparator(**item_config)


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


class GraphicalWifiMixin(_BaseMixin):
    """
    Provides the ability to draw a graphical representation of wifi signal strength.

    To use the mixin, your code needs to include the following:

    .. code:: python

        class MyGraphicalInternetWidget(GraphicalWifiMixin):
            def __init__(self):
                self.add_defaults(GraphicalWifiMixin.defaults)
                GraphicalWifiMixin.__init__(self)

            def _configure(self, qtile, bar):
                ... # other configuration lines here

                self.set_wifi_sizes()

            def draw(self):
                # To draw the icon you need the following parameters:
                # - percentage: a value between 0 and 1
                # - foreground: the colour of the indicator
                # - background: the colour of the indicator background
                self.draw_wifi(percentage=percentage, foreground=foreground, background=background)

    .. note::

        This mixin does not set the width of your widget but does provide a
        ``self.wifi_width`` attribute which can be used for this purpose.

    """

    defaults = [
        ("wifi_arc", 75, "Angle of arc in degrees."),
        ("wifi_rectangle_width", 5, "Width of rectangle in pixels."),
        ("wifi_shape", "arc", "'arc' or 'rectangle'"),
    ]

    def __init__(self):
        self.wifi_width = 0

    def set_wifi_sizes(self):
        self.wifi_padding_x = getattr(self, "padding_x", getattr(self, "padding", 0))
        self.wifi_padding_y = getattr(self, "padding_y", getattr(self, "padding", 0))
        self.wifi_height = self.bar.height - (self.wifi_padding_y * 2)
        width_ratio = math.sin(to_rads(self.wifi_arc / 2))
        if self.wifi_shape == "arc":
            self.wifi_width = (self.wifi_height * width_ratio) * 2
            self.wifi_width = math.ceil(self.wifi_width)
        else:
            self.wifi_width = self.wifi_rectangle_width

        self.icon_size = self.wifi_height

    def draw_wifi(self, percentage, foreground="ffffff", background="777777"):
        if self.wifi_shape == "arc":
            func = self._draw_wifi_arc
        else:
            func = self._draw_wifi_rectangle

        func(percentage, foreground, background)

    def _draw_wifi_arc(self, percentage, foreground, background):
        offset = self.wifi_padding_x

        half_arc = self.wifi_arc / 2
        x_offset = int(self.wifi_height * math.sin(to_rads(half_arc)))

        self.drawer.ctx.new_sub_path()

        self.drawer.ctx.move_to(
            self.wifi_padding_x + x_offset, self.wifi_padding_y + self.wifi_height
        )
        self.drawer.ctx.arc(
            offset + x_offset,
            self.wifi_padding_y + self.wifi_height,
            self.wifi_height,
            to_rads(270 - half_arc),
            to_rads(270 + half_arc),
        )
        self.drawer.set_source_rgb(background)
        self.drawer.ctx.fill()

        self.drawer.ctx.new_sub_path()
        self.drawer.ctx.move_to(offset + x_offset, self.wifi_padding_y + self.wifi_height)
        self.drawer.ctx.arc(
            offset + x_offset,
            self.wifi_padding_y + self.wifi_height,
            self.wifi_height * percentage,
            to_rads(270 - half_arc),
            to_rads(270 + half_arc),
        )
        self.drawer.set_source_rgb(foreground)
        self.drawer.ctx.fill()

    def _draw_wifi_rectangle(self, percentage, foreground, background):
        ctx = self.drawer.ctx
        ctx.save()
        ctx.translate(self.wifi_padding_x, self.wifi_padding_y)
        ctx.rectangle(0, 0, self.wifi_width, self.wifi_height)
        self.drawer.set_source_rgb(background)
        ctx.fill()

        ctx.rectangle(
            0, self.wifi_height * (1 - percentage), self.wifi_width, self.wifi_height * percentage
        )
        self.drawer.set_source_rgb(foreground)
        ctx.fill()

        ctx.restore()


class ConnectionCheckMixin(_BaseMixin):
    """
    Mixin to periodically check for internet connection and set the
    ``self.is_connected`` flag depending on status.

    Your code should include the following lines to use the mixin.

    .. code:: python

        class MyInternetWidget(ConnectionCheckMixin):
            def __init__(self):
                self.add_defaults(ConnectionCheckMixin.defaults)
                ConnectionCheckMixin.__init__(self)

            def _configure(self, qtile, bar):
                ConnectionCheckMixin._configure(self)

    """

    defaults = [
        (
            "check_connection_interval",
            0,
            "Interval to check if device connected to internet (0 to disable)",
        ),
        ("disconnected_colour", "aa0000", "Colour when device has no internet connection"),
        ("internet_check_host", "8.8.8.8", "IP adddress to check for internet connection"),
        ("internet_check_port", 53, "Port to check for internet connection"),
        (
            "internet_check_timeout",
            5,
            "Period before internet check times out and widget reports no internet connection.",
        ),
    ]

    def __init__(self):
        # If we're checking the internet connection then we assume we're disconnected
        # until we've verified the connection
        self.is_connected = not bool(self.check_connection_interval)

    def _configure(self, *args):
        if self.check_connection_interval:
            self.timeout_add(self.check_connection_interval, self._check_connection)

    def _check_connection(self):
        self.qtile.run_in_executor(self._check_internet).add_done_callback(self._check_connected)

    def _check_internet(self):
        with socket_context(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(self.internet_check_timeout)
            try:
                s.connect((self.internet_check_host, self.internet_check_port))
                return True
            except (TimeoutError, OSError):
                return False

    def _check_connected(self, result):
        self.is_connected = result.result()
        self.timeout_add(self.check_connection_interval, self._check_connection)
