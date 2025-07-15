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
import random

from libqtile import bar
from libqtile.command.base import expose_command
from libqtile.widget import base

DIRECTIONS = {
    "UP": (0, -1),
    "DOWN": (0, 1),
    "LEFT": (-1, 0),
    "RIGHT": (1, 0),
}


def add_tuples(a, b):
    return a[0] + b[0], a[1] + b[1]


class Snake(base._Widget):
    """
    A completely pointless widget.

    Plays a mini game of "Snake" in your bar with very, very basic AI
    control.

    Being honest, this will probably get very distracting very quickly!

    Can be used instead of a spacer widget in your bar. Options are available to have the
    widget be blank by default and trigger the game via commands.
    """

    orientations = base.ORIENTATION_BOTH

    defaults = [
        ("snake_colour", "090", "Colour of the snake."),
        (
            "fruit_colour",
            ["A00", "A40", "AA0", "09A", "00A"],
            "List of possible colours of the fruit",
        ),
        ("size", 3, "Size of snake and fruit"),
        ("interval", 0.04, "Interval between each step"),
        ("restart_interval", 2, "Interval between finished game and new game"),
        ("loop", True, "Whether a new game should start after the current one ends."),
        ("autostart", True, "Game runs as soon as the widget starts"),
    ]

    def __init__(self, length=bar.STRETCH, **config):
        base._Widget.__init__(self, length=length, **config)
        self.add_defaults(Snake.defaults)
        self.snake = []
        self.food = []
        self.started = False
        self._step_timer = None

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)

        # We want to hook into the length setter
        orig_setter = type(self).length.fset

        def new_setter(self, value):
            orig_setter(self, value)
            self._set_width()

        # Replace the setter with our wrapper
        type(self).length = type(self).length.setter(new_setter)

        self.direction = "RIGHT"
        if self.autostart:
            self.timeout_add(0.5, self.restart)

    def restart(self):
        if self.width == 0:
            self.timeout_add(1, self.restart)
            return
        if not self.started:
            self.started = True
            self._start_game()

    def _set_width(self):
        if not self.started or not self.food:
            return

        if not self.in_bar(self.food):
            self.food = self._random_point()

        if not self.in_bar(self.snake[0]):
            if self.bar.horizontal:
                x, y = self.snake[0]
                x = (self.width - self.size) // self.size
            else:
                x, y = self.snake[0]
                y = (self.height - self.size) // self.size
            self.snake[0] = (x, y)

    def _random_point(self):
        return (
            random.randint(0, ((self.width - self.size) // self.size)),
            random.randint(0, ((self.height - self.size) // self.size)),
        )

    def in_bar(self, point):
        if not point:
            return False

        x, y = point
        return x * self.size <= self.width and y * self.size <= self.height

    def _start_game(self):
        self.started = True
        self.snake = [self._random_point()]
        self.food = self.spawn_food()
        self.step()

    def spawn_food(self):
        while True:
            food = self._random_point()
            if food not in self.snake:
                self._fruit_colour = random.choice(self.fruit_colour)
                return food

    def step(self):
        self.set_direction()
        new_head = add_tuples(self.snake[0], DIRECTIONS[self.direction])

        if (
            new_head in self.snake
            or not (0 <= new_head[0] < self.width // self.size)
            or not (0 <= new_head[1] < self.height // self.size)
        ):
            if self.loop:
                func = self._start_game
            else:
                func = self.stop
            self.timeout_add(self.restart_interval, func)
            return

        self.snake.insert(0, new_head)

        hx, hy = new_head
        fx, fy = self.food

        if new_head == self.food:
            self.food = self.spawn_food()
        else:
            self.snake.pop()

        self.draw()
        if self.started:
            self._step_timer = self.timeout_add(self.interval, self.step)

    def set_direction(self):
        head = self.snake[0]
        fx, fy = self.food
        options = []

        for dir_name, (dx, dy) in DIRECTIONS.items():
            new_pos = (head[0] + dx, head[1] + dy)
            if (
                0 <= new_pos[0] < self.width // self.size
                and 0 <= new_pos[1] < self.height // self.size
                and new_pos not in self.snake
            ):
                distance = math.hypot(fx - new_pos[0], fy - new_pos[1])
                options.append((distance, dir_name))

        if options:
            options.sort()
            self.direction = options[0][1]

    def move_point(self, point):
        x, y = point
        return (x * self.size) + self.size // 2, (y * self.size) + self.size // 2

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)

        if not self.started or not (self.snake and self.food):
            self._finish_draw()
            return

        # Draw food
        self.drawer.set_source_rgb(self._fruit_colour)
        self.drawer.ctx.rectangle(
            *map(lambda point: point * self.size, self.food), self.size, self.size
        )
        self.drawer.ctx.fill()

        # Draw snake
        self.drawer.set_source_rgb(self.snake_colour)
        if len(self.snake) == 1:
            self.drawer.ctx.rectangle(
                *map(lambda point: point * self.size, self.snake[0]), self.size, self.size
            )
            self.drawer.ctx.fill()
        else:
            self.drawer.ctx.new_path()

            self.drawer.ctx.move_to(*self.move_point(self.snake[0]))
            for point in self.snake[1:]:
                self.drawer.ctx.line_to(*self.move_point(point))
            self.drawer.ctx.set_line_width(self.size)
            self.drawer.ctx.stroke()

        self._finish_draw()

    def _finish_draw(self):
        self.draw_at_default_position()

    @expose_command
    def start(self):
        """Start the game."""
        self.restart()

    @expose_command
    def stop(self):
        """Stop the game and clear the screen."""
        self.started = False
        if self._step_timer is not None:
            self._step_timer.cancel()
            self._step_timer = None
        self.draw()

    @expose_command
    def pause(self):
        """Pause the game."""
        if not self.started:
            return

        if self._step_timer is None:
            self._step_timer = self.timeout_add(self.interval, self.step)
        else:
            self._step_timer.cancel()
            self._step_timer = None
