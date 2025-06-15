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

import pytest
from libqtile.bar import Bar
from libqtile.config import Screen

from qtile_extras.widget.snake import Snake, add_tuples
from test.helpers import BareConfig


@pytest.fixture
def smanager(manager_nospawn, request):
    config = {"interval": 100, "length": 100, "autostart": False}

    class PatchedSnake(Snake):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **{**config, **kwargs})
            self.name = "snake"
            self.place_count = 0

        def timeout_add(self, *args, **kwargs):
            return None

    class SnakeConfig(BareConfig):
        screens = [
            Screen(top=Bar([PatchedSnake()], 50)),
        ]

    manager_nospawn.start(SnakeConfig)

    yield manager_nospawn


class DummyBar:
    width = 300
    height = 30
    length = 300
    horizontal = True


@pytest.fixture
def snake_widget():
    widget = Snake()
    widget.bar = DummyBar()
    widget.timeout_add = lambda *args: None
    widget.draw = lambda *args: None
    widget.size = 10
    widget._length = widget.bar.width
    return widget


def test_add_tuples():
    assert add_tuples((1, 2), (3, 4)) == (4, 6)


def test_random_point_within_bounds(snake_widget):
    for _ in range(100):
        x, y = snake_widget._random_point()
        assert 0 <= x * snake_widget.size <= snake_widget.length
        assert 0 <= y * snake_widget.size <= snake_widget.height


def test_spawn_food_not_in_snake(snake_widget):
    snake_widget.snake = [(0, 0)]
    food = snake_widget.spawn_food()
    assert food not in snake_widget.snake


def test_set_direction_moves_closer_to_food(snake_widget):
    snake_widget.size = 10
    snake_widget.snake = [(1, 1)]
    snake_widget.food = (2, 1)
    snake_widget.set_direction()
    assert snake_widget.direction == "RIGHT"


def test_step_eats_food_and_grows(snake_widget):
    snake_widget.snake = [(1, 1)]
    snake_widget.food = (2, 1)
    snake_widget.direction = "RIGHT"
    snake_widget.started = True
    snake_widget.spawn_food = lambda *args: (3, 1)
    snake_widget.draw = lambda *args: None

    snake_widget.step()

    assert snake_widget.snake[0] == (2, 1)
    assert len(snake_widget.snake) == 2
    assert snake_widget.food == (3, 1)


def test_step_hits_wall_and_stops_loop(snake_widget):
    call_args = None

    def call(*args):
        nonlocal call_args
        call_args = args

    snake_widget.bar.width = 20
    snake_widget.bar.height = 20
    snake_widget._length = 20
    snake_widget.size = 10
    snake_widget.snake = [(1, 0), (0, 0)]
    snake_widget.direction = "RIGHT"
    snake_widget.loop = False
    snake_widget.started = True
    snake_widget.timeout_add = call
    snake_widget.food = (3, 0)
    snake_widget.set_direction = lambda: None

    snake_widget.step()
    assert call_args == (snake_widget.restart_interval, snake_widget.stop)


def test_restart_starts_game(snake_widget):
    snake_widget.bar.width = 100
    snake_widget.bar.height = 100
    snake_widget.started = False
    snake_widget.restart()
    assert snake_widget.started


def test_move_point_returns_pixel_coords(snake_widget):
    snake_widget.size = 10
    assert snake_widget.move_point((3, 2)) == (35, 25)


def test_game_logic(smanager):
    snake = smanager.c.widget["snake"]

    def step():
        snake.eval("self.step()")

    def get_snake():
        _, s = snake.eval("self.snake")
        return s

    def get_snake_len():
        _, l = snake.eval("len(self.snake)")
        return int(l)

    snake.start()

    snake1 = get_snake()
    len1 = get_snake_len()

    assert len1 == 1

    step()

    assert get_snake() != snake1

    count = 0

    while get_snake_len() < 2:
        step()
        count += 1
        if count > 100:
            assert False

    assert get_snake_len() > 1
