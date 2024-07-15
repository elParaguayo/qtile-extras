# Copyright (c) 2024 elParaguayo
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
from libqtile import hook
from libqtile.log_utils import logger

from qtile_extras.layout.decorations.borders import (  # noqa: F401
    ConditionalBorder,
    ConditionalBorderWidth,
    CustomBorder,
    GradientBorder,
    GradientFrame,
    RoundedCorners,
    ScreenGradientBorder,
    SolidEdge,
)


# We need to inject code into qtile to allow the windows to render the new
# decorations. To simplify this, we can use a hook so it's invisible to
# users.
@hook.subscribe.startup_once
def inject_border_methods():
    from libqtile import qtile

    logger.debug("qtile_extras: Running inject_border_methods.")

    if qtile.core.name == "wayland":
        from libqtile.backend.wayland.window import Window

        from qtile_extras.layout.decorations.injections_wayland import (
            wayland_paint_borders,
            wayland_window_init,
        )

        logger.debug("qtile_extras: Injecting wayland border methods.")
        Window.__init__ = wayland_window_init
        Window.paint_borders = wayland_paint_borders

    else:
        from libqtile.backend.x11.window import XWindow

        from qtile_extras.layout.decorations.injections import x11_paint_borders

        logger.debug("qtile_extras: Injecting x11 border methods.")
        XWindow.paint_borders = x11_paint_borders


@hook.subscribe.startup_once
def inject_border_width_methods():
    from libqtile import qtile

    from qtile_extras.layout.decorations.injections import new_place

    logger.debug("qtile_extras: Running inject_border_width methods.")

    if qtile.core.name == "wayland":
        from libqtile.backend.wayland.xdgwindow import XdgWindow
        from libqtile.backend.wayland.xwindow import XWindow

        logger.debug("qtile_extras: Injecting wayland border width methods.")
        for base in (XdgWindow, XWindow):
            base._place = base.place
            base.place = new_place

    else:
        from libqtile.backend.x11.window import _Window

        logger.debug("qtile_extras: Injecting x11 border methods.")
        _Window._place = _Window.place
        _Window.place = new_place
