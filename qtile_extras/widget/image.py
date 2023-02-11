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
import os

from libqtile import bar
from libqtile.log_utils import logger
from libqtile.widget import Image as QtileImage

from qtile_extras.images import Img, ImgMask


class Image(QtileImage):
    """
    A modified version of Qtile's ``Image`` widget.

    The two key differences are:
    1) The widget accepts a url and will download the image from the internet.
    2) The image can be used as a mask and filled with a user-defined colour.
    """

    defaults = [
        ("filename", None, "Image filename. Can contain '~'. Can also be a url."),
        ("mask", False, "Use the image as a mask and fill with ``colour``."),
        ("colour", "ffffff", "Colour to paint maksed image"),
        ("adjust_x", 0, "Fine x-axis adjustment of icon position"),
        ("adjust_y", 0, "Fine y-axis adjustment of icon position"),
        (
            "padding",
            0,
            "Padding to left and right of image on horizontal bar, or above and below widget on vertical bar.",
        ),
    ]

    def __init__(self, length=bar.CALCULATED, **config):
        QtileImage.__init__(self, length, **config)
        self.add_defaults(Image.defaults)

    def _update_image(self):
        img_class = ImgMask if self.mask else Img

        self.img = None

        if not self.filename:
            logger.warning("Image filename not set!")
            return

        self.filename = os.path.expanduser(self.filename)

        if self.filename.startswith("http"):
            img = img_class.from_url(self.filename)

        else:
            if not os.path.exists(self.filename):
                logger.warning("Image does not exist: %s", self.filename)
                return

            img = img_class.from_path(self.filename)

        if self.mask:
            img.attach_drawer(self.drawer)

        self.img = img
        img.theta = self.rotate
        if not self.scale:
            return
        if self.bar.horizontal:
            new_height = self.bar.height - (self.margin_y * 2)
            img.resize(height=new_height)
        else:
            new_width = self.bar.width - (self.margin_x * 2)
            img.resize(width=new_width)

    def draw(self):
        if self.img is None:
            return

        pad_x = self.padding if self.bar.horizontal else 0
        pad_y = self.padding if not self.bar.horizontal else 0

        self.drawer.clear(self.background or self.bar.background)
        self.drawer.ctx.save()
        self.drawer.ctx.translate(
            self.margin_x + pad_x + self.adjust_x, self.margin_y + pad_y + self.adjust_y
        )
        if self.mask:
            self.img.draw(colour=self.colour)
        else:
            self.drawer.ctx.set_source(self.img.pattern)
            self.drawer.ctx.paint()
        self.drawer.ctx.restore()

        if self.bar.horizontal:
            self.drawer.draw(offsetx=self.offset, offsety=self.offsety, width=self.width)
        else:
            self.drawer.draw(offsety=self.offset, offsetx=self.offsetx, height=self.width)

    def calculate_length(self):
        if self.img is None:
            return 0

        if self.bar.horizontal:
            return self.img.width + (self.margin_x * 2) + (self.padding * 2)
        else:
            return self.img.height + (self.margin_y * 2) + (self.padding * 2)
