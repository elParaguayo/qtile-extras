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
import math

import pytest
from libqtile.bar import Bar
from libqtile.config import Screen

from qtile_extras.widget.pong import Ball, Paddle, Pong, Velocity, _PongObject
from test.helpers import BareConfig


@pytest.fixture
def pmanager(manager_nospawn, request):
    config = {"paddle_speed": 0.001, "ball_speed": 0.001, "length": 100, "autostart": False}

    class PatchedPong(Pong):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **{**config, **kwargs})
            self.name = "pong"
            self.place_count = 0

        def timeout_add(self, *args, **kwargs):
            return None

    class PongConfig(BareConfig):
        screens = [
            Screen(top=Bar([PatchedPong()], 50)),
        ]

    manager_nospawn.start(PongConfig)

    yield manager_nospawn


# -------- Velocity Tests --------


def test_velocity_normalise():
    v = Velocity(3, 4)
    v.normalise()
    magnitude = math.sqrt(v.x**2 + v.y**2)
    assert pytest.approx(magnitude, 0.0001) == 1.0


def test_velocity_randomise():
    v = Velocity()
    v.randomise()
    magnitude = math.sqrt(v.x**2 + v.y**2)
    assert pytest.approx(magnitude, 0.0001) == 1.0


# -------- _PongObject Tests --------


def test_pong_object_step():
    obj = _PongObject(x=1, y=1, width=2, height=3)
    obj.velocity = Velocity(1, 2)
    obj.step()
    assert obj.x == 2
    assert obj.y == 3


# -------- Ball Tests --------


def test_ball_random_start_angle():
    b = Ball()
    angle = math.atan2(abs(b.velocity.y), abs(b.velocity.x))
    max_angle = math.asin(b.max_angle)
    assert angle <= max_angle


def test_ball_bounce_vertical_top():
    b = Ball(y=0)
    b.velocity.y = -1
    b.bounce(paddles=[], space=type("Space", (), {"height": 100}))
    assert b.velocity.y == 1


def test_ball_bounce_vertical_bottom():
    b = Ball(y=98, size=3)
    b.velocity.y = 1
    b.bounce(paddles=[], space=type("Space", (), {"height": 100}))
    assert b.velocity.y == -1


def test_ball_bounce_on_paddle():
    b = Ball(x=10, y=10, size=2)
    b.velocity.x = -1
    b.velocity.y = 0

    paddle = Paddle(x=9, y=8, width=2, height=5, left=True)
    b.bounce([paddle], space=type("Space", (), {"height": 100}))

    assert b.velocity.x == 1  # Ball should bounce


def test_ball_score_detection():
    b = Ball(x=-1, y=0, size=2)
    space = type("Space", (), {"width": 100})
    assert b.is_score(space)

    b.x = 101
    assert b.is_score(space)

    b.x = 50
    assert not b.is_score(space)


# -------- Paddle Tests --------


def test_paddle_ignore_far_ball():
    paddle = Paddle(x=0, y=0, height=10, width=2, react_distance=10)
    ball = Ball(x=100, y=100)
    paddle.move(ball)
    assert paddle.velocity.y == 0


def test_paddle_move_up():
    paddle = Paddle(x=0, y=10, height=10, width=2, react_distance=100)
    ball = Ball(x=5, y=5)
    paddle.move(ball)
    assert paddle.velocity.y == -1


def test_paddle_move_down():
    paddle = Paddle(x=0, y=0, height=10, width=2, react_distance=100)
    ball = Ball(x=5, y=15)
    paddle.move(ball)
    assert paddle.velocity.y == 1


def test_paddle_no_move_ball_aligned():
    paddle = Paddle(x=0, y=5, height=10, width=2, react_distance=100)
    ball = Ball(x=5, y=8)
    paddle.move(ball)
    assert paddle.velocity.y == 1  # close enough, small adjustment


# -------- Game Simulation Tests --------


def test_pong_game(pmanager):
    pong = pmanager.c.widget["pong"]

    def step():
        pong.eval("self.ball_step()")
        pong.eval("self.paddle_step()")

    def ball_position():
        _, pos = pong.eval("(self.ball.x, self.ball.y)")
        return pos

    def paddles_positions():
        _, pos = pong.eval("[(p.x, p.y) for p in self.paddles]")
        return pos

    pong.start()

    ball1 = ball_position()
    paddles1 = paddles_positions()

    for _ in range(10):
        step()

    ball2 = ball_position()
    paddles2 = paddles_positions

    assert ball1 != ball2
    assert paddles1 != paddles2
