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

from qtile_extras.widget.snake import Snake
from test.helpers import Retry
from test.widget.docs_screenshots.conftest import widget_config


@pytest.fixture
def widget():
    yield partial(Snake, length=200, interval=0.001)


@widget_config(
    [{}, {"snake_colour": "f0f", "fruit_colour": ["0ff"], "size": 4}, {"autostart": False}]
)
def ss_snake(screenshot_manager):
    snake = screenshot_manager.c.widget["snake"]
    _, autostart = snake.eval("self.autostart")

    def snake_length():
        _, val = snake.eval("len(self.snake)")
        return int(val)

    @Retry(ignore_exceptions=(AssertionError,), tmax=30)
    def wait_for_snake():
        if autostart == "False":
            assert True
            return

        assert snake_length() > 25

    wait_for_snake()

    screenshot_manager.take_screenshot()
