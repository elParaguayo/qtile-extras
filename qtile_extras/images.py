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

import os
from io import BytesIO
from typing import TYPE_CHECKING
from urllib.error import URLError
from urllib.request import urlopen

import cairocffi
from libqtile.backend.base import Drawer
from libqtile.images import Img as QtileImg
from libqtile.images import Loader as QtileLoader
from libqtile.images import LoadingError
from libqtile.log_utils import logger
from libqtile.utils import scan_files

if TYPE_CHECKING:
    from libqtile.utils import ColorsType


class Img(QtileImg):
    @classmethod
    def from_url(cls, url):
        try:
            raw = urlopen(url)
        except URLError:
            logger.error("Could not open image file: %s", url)
            return

        return cls(BytesIO(raw.read()).read(), path=url)


class ImgMask(QtileImg):
    """
    Image object that uses the image source as a mask to paint the background.

    Colour can be set at the moment of drawing, rather than preparing images in
    advance.
    """

    def __init__(self, *args, drawer: Drawer | None = None, **kwargs):
        self.drawer = drawer
        QtileImg.__init__(self, *args, **kwargs)

    def attach_drawer(self, drawer: Drawer):
        self.drawer = drawer

    def draw(self, x=0, y=0, colour: "ColorsType" = "FFFFFF"):
        if self.drawer is None:
            logger.error("Cannot draw masked image. Did you forget to attach the drawer?")
            return

        self.drawer.ctx.save()
        self.drawer.set_source_rgb(colour)
        self.drawer.ctx.set_operator(cairocffi.OPERATOR_SOURCE)
        self.drawer.ctx.translate(x, y)
        self.drawer.ctx.mask(self.pattern)
        self.drawer.ctx.fill()
        self.drawer.ctx.restore()


class Loader(QtileLoader):
    """
    Same as libqtile.images.Loader but takes an optional parameter,
    ``masked``, to determine whether to use ``ImgMask`` class.
    """

    def __init__(self, *directories, masked=True, **kwargs):
        self.img_class = ImgMask if masked else Img
        QtileLoader.__init__(self, *directories, **kwargs)

    def __call__(self, *names):
        d = {}
        seen = set()
        set_names = set()
        for n in names:
            root, ext = os.path.splitext(n)
            if ext:
                set_names.add(n)
            else:
                set_names.add(n + ".*")

        for directory in self.directories:
            d_matches = scan_files(directory, *(set_names - seen))
            for name, paths in d_matches.items():
                if paths:
                    d[name if name in names else name[:-2]] = self.img_class.from_path(paths[0])
                    seen.add(name)

        if seen != set_names:
            msg = "Wasn't able to find images corresponding to the names: {}"
            raise LoadingError(msg.format(set_names - seen))

        return d
