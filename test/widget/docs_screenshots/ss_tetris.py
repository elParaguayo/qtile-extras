# Copyright (c) 2025 elParaguayo
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
from functools import partial

import pytest

from qtile_extras.widget.tetris import Tetris as _Tetris
from test.helpers import Retry
from test.widget.docs_screenshots.conftest import widget_config


class Tetris(_Tetris):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._place_count = 0

    def place(self, *args):
        super().place(*args)
        self._place_count += 1


@pytest.fixture
def widget():
    yield partial(Tetris, length=200, speed=1000)


@widget_config([{}, {"blockify": True}, {"cell_size": 3}])
def ss_tetris(screenshot_manager):
    tetris = screenshot_manager.c.widget["tetris"]
    _, autostart = tetris.eval("self.autostart")

    def blocks_placed():
        _, val = tetris.eval("self._place_count")
        return int(val)

    @Retry(ignore_exceptions=(AssertionError,), tmax=30)
    def wait_for_blocks(count):
        if autostart == "False":
            assert True
            return

        assert blocks_placed() >= count

    wait_for_blocks(10)

    screenshot_manager.take_screenshot()
