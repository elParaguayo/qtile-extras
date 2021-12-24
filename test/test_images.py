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
from pathlib import Path

import libqtile.config
import pytest
from libqtile import bar
from libqtile.images import Img
from libqtile.widget.base import _Widget

from qtile_extras.images import ImgMask, Loader

ICON_PATH = Path(__file__).parent / ".." / "qtile_extras" / "resources" / "tvheadend-icons"


@pytest.mark.parametrize("kwargs,expected_cls", [({}, Img), ({"masked": True}, ImgMask)])
def test_loader(kwargs, expected_cls):
    images = Loader(ICON_PATH, **kwargs)("icon")

    for _, image in images.items():
        assert isinstance(image, expected_cls)


def test_draw(minimal_conf_noscreen, manager_nospawn):
    class MaskWidget(_Widget):
        def __init__(self):
            _Widget.__init__(self, bar.CALCULATED)

        def _configure(self, qtile, bar):
            _Widget._configure(self, qtile, bar)
            self.img = ImgMask.from_path(f"{ICON_PATH}/icon.svg")
            self.img.attach_drawer(self.drawer)
            self.img.resize(self.bar.height - 1)

        def calculate_length(self):
            if not self.configured:
                return 0

            return self.img.width

        def draw(self):
            self.drawer.clear(self.background or self.bar.background)
            self.img.draw()
            self.drawer.draw(offsetx=self.offset, offsety=self.offsety, width=self.length)

    config = minimal_conf_noscreen
    config.screens = [libqtile.config.Screen(top=bar.Bar([MaskWidget()], 10))]

    manager_nospawn.start(config)

    assert manager_nospawn.c.widget["maskwidget"]
    assert manager_nospawn.c.widget["maskwidget"].info()["width"] > 0
