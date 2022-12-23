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
from libqtile.widget import CurrentLayoutIcon as LayoutIcon
from libqtile.widget import base

from qtile_extras.images import ImgMask


class CurrentLayoutIcon(LayoutIcon):
    """
    A modified version of Qtile's ``CurrentLayoutIcon``.

    The default version behaves the same as the main qtile version of the widget.
    However, if you set ``use_mask`` to ``True`` then you can set the colour of
    the icon via the ``foreground`` parameter.
    """

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        (
            "use_mask",
            False,
            "Uses the icon file as a mask. Icon colour will be set via the ``foreground`` parameter.",
        )
    ]

    _screenshots = [
        ("currentlayouticon.png", "You can use a single colour or a list of colours.")
    ]

    def __init__(self, **config):
        LayoutIcon.__init__(self, **config)
        self.add_defaults(CurrentLayoutIcon.defaults)

        # The original widget calculates a new scale value. We don't want to use that with the ImgMask.
        if self.use_mask:
            self.scale = config.get("scale", 1)

    def _setup_images(self):
        """
        Loads layout icons.
        """
        if not self.use_mask:
            LayoutIcon._setup_images(self)
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
            except (cairocffi.Error, cairocffi.pixbuf.ImageLoadingError, IOError):
                # Icon file is guaranteed to exist at this point.
                # If this exception happens, it means the icon file contains
                # an invalid image or is not readable.
                self.icons_loaded = False
                logger.warning('Failed to load icon from file "%s".', icon_file_path)
                raise

            # Resize the image to the bar and adjust for any scaling.
            size = int((self.bar.height - 1) * self.scale)
            img.resize(size)

            if img.width > self.length:
                self.length = int(img.width) + self.actual_padding * 2

            self.surfaces[layout_name] = img

        self.icons_loaded = True

    def draw(self):
        if not self.icons_loaded or not self.use_mask or self.current_layout not in self.surfaces:
            LayoutIcon.draw(self)
            return

        img = self.surfaces[self.current_layout]

        self.drawer.clear(self.background or self.bar.background)
        offsety = (self.bar.height - img.height) // 2
        img.draw(colour=self.foreground, x=self.actual_padding, y=offsety)
        self.drawer.draw(offsetx=self.offset, offsety=self.offsety, width=self.length)
