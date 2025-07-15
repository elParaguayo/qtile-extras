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


class Velocity:
    """Class to store x, v velocity"""

    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

    def normalise(self):
        """Ensure velocity always has a magnitude of 1."""
        magnitude = (self.x**2 + self.y**2) ** 0.5
        if magnitude != 0:
            self.x /= magnitude
            self.y /= magnitude

    def randomise(self):
        self.x = random.uniform(-1, 1)
        self.y = random.uniform(-1, 1)
        self.normalise()


class _PongObject:
    """Base class for game objects."""

    def __init__(self, x=0, y=0, height=1, width=1, colour="fff"):
        self.x = x
        self.y = y
        self.height = height
        self.width = width
        self.colour = colour
        self.velocity = Velocity()

    def step(self):
        """Move the object."""
        self.x += self.velocity.x
        self.y += self.velocity.y

    def draw(self, drawer):
        """Draw the object in a widget drawer object."""
        drawer.set_source_rgb(self.colour)
        drawer.ctx.rectangle(self.x, self.y, self.width, self.height)
        drawer.ctx.fill()


class Ball(_PongObject):
    """Pong's ball."""

    def __init__(self, x=0, y=0, size=1, colour="fff", max_angle=60):
        super().__init__(x=x, y=y, width=size, height=size, colour=colour)
        self.max_angle = math.sin(math.radians(max_angle))
        self._max_angle_x = math.cos(math.radians(max_angle))
        self.random_start()

    def random_start(self):
        self.velocity.randomise()

        while abs(self.velocity.y) > math.sin(self.max_angle):
            self.velocity.randomise()

    def bounce(self, paddles, space):
        """Checks if ball bounces on paddles or edges."""
        if self.y <= 0 or self.y + self.height >= space.height:
            self.velocity.y *= -1

        for paddle in paddles:
            x = self.x if paddle.left else self.x + self.width
            if paddle.x <= x <= (paddle.x + paddle.width) and (
                paddle.y <= self.y <= paddle.y + paddle.height
            ):
                self.velocity.x *= -1
                rel = (self.y - paddle.y) / paddle.height  # 0.0 to 1.0
                norm = (rel - 0.5) * 2  # -1.0 to 1.0
                self.velocity.y *= norm * 3
                self.clamp()

    def clamp(self):
        """Keeps ball in desired angle range."""
        self.velocity.normalise()
        if abs(self.velocity.y) > math.sin(self.max_angle):
            self.velocity.y = self.max_angle if self.velocity.y > 0 else -self.max_angle
            self.velocity.x = self._max_angle_x if self.velocity.x > 0 else -self._max_angle_x

    def is_score(self, space):
        """Returns true if ball reaches one of the edges."""
        return self.x < 0 or self.x + self.width > space.width


class Paddle(_PongObject):
    """Paddle object."""

    def __init__(self, left=True, react_distance=100, **kwargs):
        super().__init__(**kwargs)
        self.left = left
        self.react_distance = react_distance
        self.velocity = Velocity(y=1)

    def move(self, ball):
        """Basic control to move paddle up or down."""
        if abs(ball.x - self.x) > self.react_distance:
            self.velocity.y = 0
        elif (self.left and ball.x < self.x) or (not self.left and ball.x > self.x + self.width):
            self.velocity.y = 0
        elif ball.y < self.y:
            self.velocity.y = -1
        elif ball.y > (self.y + self.height):
            self.velocity.y = 1
        else:
            self.velocity.y = 1


class Pong(base._Widget):
    """
    A completely pointless widget.

    Plays a mini game of "Pong" in your bar with very, very basic AI
    control.

    Being honest, this will probably get very distracting very quickly!

    Can be used instead of a spacer widget in your bar. Options are available to have the
    widget be blank by default and trigger the game via commands.
    """

    orientations = base.ORIENTATION_HORIZONTAL

    defaults = [
        ("paddle_colour", "fff", "Colour of the snake."),
        ("paddle_length", 8, "Paddle length"),
        ("paddle_thickness", 2, "Paddle thickness"),
        ("paddle_speed", 10, "Paddle speed"),
        (
            "paddle_react_distance",
            500,
            "Paddle only moves when ball is within x pixels of the paddle",
        ),
        ("ball_colour", "aaa", "Colour of the ball"),
        ("ball_size", 3, "Size of snake and fruit"),
        ("ball_speed", 40, "Ball speed"),
        ("ball_max_angle", 45, "Maximum angle above/below horizontal"),
        ("restart_interval", 2, "Interval between finished game and new game"),
        ("loop", True, "Whether a new game should start after the current one ends."),
        ("autostart", True, "Game runs as soon as the widget starts"),
    ]

    def __init__(self, length=bar.STRETCH, **config):
        base._Widget.__init__(self, length=length, **config)
        self.add_defaults(Pong.defaults)
        self.started = False
        self._paddle_timer = None
        self._ball_timer = None
        self.paddles = []
        self.ball = None

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)

        # We want to hook into the length setter
        orig_setter = type(self).length.fset

        def new_setter(self, value):
            orig_setter(self, value)
            self._set_width()

        # Replace the setter with our wrapper
        type(self).length = type(self).length.setter(new_setter)

        self.paddle_length = min(self.paddle_length, self.height // 2)

        if self.autostart:
            self.timeout_add(0.5, self.restart)

    def restart(self):
        if self.width == 0:
            self.timeout_add(self.restart_interval, self.restart)
            return
        if not self.started:
            self.started = True
            self._start_game()

    def _set_width(self):
        if not self.started:
            return

        self._stop_timers()
        self.started = False

        self.restart()

    def _start_game(self):
        self.started = True
        paddle_y = (self.bar.height - self.paddle_length) // 2
        self.paddles = [
            Paddle(
                x=5,
                y=paddle_y,
                height=self.paddle_length,
                width=self.paddle_thickness,
                colour=self.paddle_colour,
                react_distance=self.paddle_react_distance,
            ),
            Paddle(
                x=self.width - 5,
                y=paddle_y,
                height=self.paddle_length,
                width=self.paddle_thickness,
                colour=self.paddle_colour,
                left=False,
                react_distance=self.paddle_react_distance,
            ),
        ]
        self.ball = Ball(
            x=(self.width - self.ball_size) // 2,
            y=(self.height - self.ball_size) // 2,
            size=self.ball_size,
            colour=self.ball_colour,
            max_angle=self.ball_max_angle,
        )
        self._paddle_timer = self.timeout_add(1 / self.paddle_speed, self.paddle_step)
        self._ball_timer = self.timeout_add(1 / self.ball_speed, self.ball_step)
        self.draw()

    def paddle_step(self):
        for paddle in self.paddles:
            paddle.move(self.ball)
            paddle.step()

        self._paddle_timer = self.timeout_add(1 / self.paddle_speed, self.paddle_step)
        self.draw()

    def ball_step(self):
        self.ball.bounce(self.paddles, self)
        self.ball.step()

        if self.ball.is_score(self):
            self.started = False
            self._stop_timers()
            self.timeout_add(2, self.restart)
        else:
            self._ball_timer = self.timeout_add(1 / self.ball_speed, self.ball_step)
        self.draw()

    def _stop_timers(self):
        if self._ball_timer is not None:
            self._ball_timer.cancel()
            self._ball_timer = None

        if self._paddle_timer is not None:
            self._paddle_timer.cancel()
            self._paddle_timer = None

    def draw(self):
        if self.ball is None:
            return

        self.drawer.clear(self.background or self.bar.background)

        if self.started:
            for paddle in self.paddles:
                paddle.draw(self.drawer)

            self.ball.draw(self.drawer)

        self.draw_at_default_position()

    @expose_command
    def start(self):
        """Start the game."""
        self.restart()

    @expose_command
    def stop(self):
        """Stop the game and clear the screen."""
        self.started = False
        self._stop_timers()
        self.draw()

    @expose_command
    def pause(self):
        """Pause the game."""
        if not self.started:
            return

        if self._ball_timer is None:
            self._ball_timer = self.timeout_add(1 / self.ball_speed, self.ball_step)
            self._paddle_timer = self.timeout_add(1 / self.paddle_speed, self.paddle_step)
        else:
            self._stop_timers()
