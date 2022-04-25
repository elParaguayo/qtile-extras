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
import math

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import pytest

from qtile_extras import widget
from test.helpers import BareConfig, Retry


class FakeAttribute:
    def __getattr__(self, value):
        attr = FakeAttribute()
        setattr(self, value, attr)
        return attr

    def __call__(self, *args, **kwargs):
        return None


class FakeContext(FakeAttribute):
    def __init__(self):
        self.angle = 0

    def rotate(self, angle):
        self.angle = angle


class FakeBar(FakeAttribute):
    size = 20


class FakeDrawer(FakeAttribute):
    def __init__(self):
        self.ctx = FakeContext()


class ClockConfig(BareConfig):
    screens = [
        libqtile.config.Screen(
            top=libqtile.bar.Bar(
                [
                    widget.AnalogueClock(second_size=1),
                    widget.AnalogueClock(name="square", face_shape="square"),
                    widget.AnalogueClock(name="circle", face_shape="circle"),
                    widget.AnalogueClock(name="bad_shape", face_shape="hexagon"),
                    widget.AnalogueClock(
                        name="face_file", face_shape="square", face_background="220022"
                    ),
                ],
                40,
            )
        )
    ]


clock_config = pytest.mark.parametrize("manager", [ClockConfig], indirect=True)


def test_analogueclock_hand_angles():
    clock = widget.AnalogueClock()
    clock.drawer = FakeDrawer()
    clock.bar = FakeBar()
    clock.hours = 3
    clock.minuntes = 30
    clock.seconds = 45

    # Angles start from positive x axis and increase in an anticlockwise direction

    # Hour hand is at 3 o'clock = 0
    clock.draw_hours()
    assert clock.drawer.ctx.angle == 0

    # Minute hand is at 30 mins = -pi/2
    clock.draw_minutes()
    assert clock.drawer.ctx.angle == -1 * math.pi / 2

    # Second hand is at 45 mins = po
    clock.draw_seconds()
    assert clock.drawer.ctx.angle == math.pi


@clock_config
def test_analogueclock_unknown_face(logger, manager):
    clock = manager.c.widget["bad_shape"]
    _, shape = clock.eval("self.face_shape")
    assert shape == "None"

    records = logger.get_records("setup")
    records = [r for r in records if r.msg.startswith("Unknown clock")]
    assert records

    log = records[0]
    assert log.levelname == "WARNING"
    assert log.msg == "Unknown clock face shape. Setting to None."


@clock_config
def test_analogueclock_loop(manager):
    @Retry(ignore_exceptions=(AssertionError,))
    def count_seconds(widget, start):
        _, secs = widget.eval("self.seconds")
        assert secs != start

    clock = manager.c.widget["analogueclock"]
    _, secs = clock.eval("self.seconds")
    count_seconds(clock, secs)
