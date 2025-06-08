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

from qtile_extras.widget.pong import Pong as _Pong
from test.helpers import Retry


class Pong(_Pong):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.step_count = 0

    def ball_step(self):
        super().ball_step()
        self.step_count += 1


@pytest.fixture
def widget():
    yield partial(Pong, length=200, ball_speed=100, paddle_speed=100, paddle_react_distance=100)


def ss_pong(screenshot_manager):
    pong = screenshot_manager.c.widget["pong"]

    def step_count():
        _, val = pong.eval("self.step_count")
        return int(val)

    @Retry(ignore_exceptions=(AssertionError,), tmax=30)
    def wait_for_move():
        assert step_count() > 25

    wait_for_move()

    screenshot_manager.take_screenshot()
