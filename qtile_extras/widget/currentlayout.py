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

    This version sets the colour of the icon via the ``foreground``
    parameter. This behaviour can be disabled by using setting ``use_mask``
    to ``False``.
    """

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        ("use_mask", True, "Uses the icon file as a mask. Set to False to show original icon.")
    ]

    _screenshots = [
        ("currentlayouticon.png", "You can use a single colour or a list of colours.")
    ]

    def __init__(self, **config):
        LayoutIcon.__init__(self, **config)
        self.add_defaults(CurrentLayoutIcon.defaults)

    def _setup_images(self):
        """
        Loads layout icons.
        """
        if not self.use_mask:
            LayoutIcon._setup_images(self)
            return

        for layout_name in self._get_layout_names():
            icon_file_path = self.find_icon_file_path(layout_name)
            if icon_file_path is None:
                logger.warning('No icon found for layout "%s"', layout_name)
                icon_file_path = self.find_icon_file_path("unknown")

            try:
                img = ImgMask.from_path(icon_file_path)
                img.attach_drawer(self.drawer)
            except (cairocffi.Error, IOError) as e:
                # Icon file is guaranteed to exist at this point.
                # If this exception happens, it means the icon file contains
                # an invalid image or is not readable.
                self.icons_loaded = False
                logger.exception(
                    'Failed to load icon from file "%s", error was: %s', icon_file_path, e.message
                )
                return

            size = self.bar.height - 1
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
