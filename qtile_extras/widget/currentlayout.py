# Copyright (c) 2022 elParaguayo
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
import cairocffi
from libqtile.log_utils import logger
from libqtile.widget import CurrentLayout as _CurrentLayout
from libqtile.widget import base

from qtile_extras.images import ImgMask


class CurrentLayout(_CurrentLayout):
    """
    A modified version of Qtile's ``CurrentLayout``.

    The default version behaves the same as the main qtile version of the widget.
    However, if you set ``use_mask`` to ``True`` then you can set the colour of
    the icon via the ``foreground`` parameter.
    """

    defaults = [
        (
            "use_mask",
            False,
            "Uses the icon file as a mask. Icon colour will be set via the ``foreground`` parameter.",
        )
    ]

    def __init__(self, **config):
        _CurrentLayout.__init__(self, **config)
        self.add_defaults(CurrentLayout.defaults)

        # The original widget calculates a new scale value. We don't want to use that with the ImgMask.
        if self.use_mask:
            self.scale = config.get("scale", 1)

    def _setup_images(self):
        """
        Loads layout icons.
        """
        if not self.use_mask:
            _CurrentLayout._setup_images(self)
            return

        for names in self._get_layout_names():
            layout_name = names[0]
            # Python doesn't have an ordered set but we can use a dictionary instead
            # First key is the layout's name (which may have been set by the user),
            # the second is the class name. If these are the same (i.e. the user hasn't
            # set a name) then there is only one key in the dictionary.
            layouts = dict.fromkeys(names)
            for layout in layouts.keys():
                icon_file_path = self.find_icon_file_path(layout)
                if icon_file_path:
                    break
            else:
                logger.warning('No icon found for layout "%s".', layout_name)
                icon_file_path = self.find_icon_file_path("unknown")

            try:
                img = ImgMask.from_path(icon_file_path)
                img.attach_drawer(self.drawer)
                # Check if we can create a surface here
                img.surface
            except (OSError, cairocffi.Error, cairocffi.pixbuf.ImageLoadingError):
                # Icon file is guaranteed to exist at this point.
                # If this exception happens, it means the icon file contains
                # an invalid image or is not readable.
                self.icons_loaded = False
                logger.warning('Failed to load icon from file "%s".', icon_file_path)
                raise

            # Resize the image to the bar and adjust for any scaling.
            size = int((self.bar.height - 1) * self.scale)
            img.resize(size)

            if img.width > self.img_length:
                self.img_length = int(img.width)

            self.surfaces[layout_name] = img

        self.icons_loaded = True

    def draw_icon(self):
        if not self.icons_loaded:
            return
        try:
            surface = self.surfaces[self.current_layout]
        except KeyError:
            logger.error("No icon for layout %s", self.current_layout)
            return

        self.drawer.clear(self.background or self.bar.background)
        self.drawer.ctx.save()
        self.rotate_drawer()

        translatex, translatey = self.width, self.height

        if self.mode == "both":
            y = (self.bar.size - self.layout.height) / 2 + 1
            if self.bar.horizontal:
                if self.icon_first:
                    # padding - icon - padding - text - padding
                    x = self.padding + self.img_length + self.padding
                    translatex -= base._TextBox.calculate_length(self) - self.padding
                else:
                    # padding - text - padding - icon - padding
                    x = self.padding
                    translatex += base._TextBox.calculate_length(self) - self.padding
            elif self.rotate:
                if self.icon_first:
                    # padding - icon - padding - text - padding
                    x = self.padding + self.img_length + self.padding
                    translatey -= base._TextBox.calculate_length(self) - self.padding
                else:
                    # padding - text - padding - icon - padding
                    x = self.padding
                    translatey += base._TextBox.calculate_length(self) - self.padding
            else:
                x = 0
                if self.icon_first:
                    # padding - icon - padding - text - padding
                    y = self.padding + self.img_length + self.padding
                    translatey -= base._TextBox.calculate_length(self) - self.padding
                else:
                    # padding - text - padding - icon - padding
                    y = self.padding
                    translatey += base._TextBox.calculate_length(self) - self.padding

            self.layout.draw(x, y)

        if not self.bar.horizontal and self.rotate:
            translatex, translatey = translatey, translatex

        self.drawer.ctx.translate(
            (translatex - surface.width) / 2,
            (translatey - surface.height) / 2,
        )
        if self.use_mask:
            surface.draw(colour=self.foreground)
        else:
            self.drawer.ctx.set_source(surface.pattern)
            self.drawer.ctx.paint()
        self.drawer.ctx.restore()
        self.draw_at_default_position()


class CurrentLayoutIcon(CurrentLayout):
    """
    Helper class to avoid breakages in users' config.

    In qtile, the ``CurrentLayoutIcon`` widget was removed and combined with ``CurrentLayout``.

    This class just passes the necessary arguments to ``CurrentLayout`` to result in the widget
    displaying an icon.
    """

    def __init__(self, *args, **config):
        CurrentLayout.__init__(self, *args, mode="icon", **config)
