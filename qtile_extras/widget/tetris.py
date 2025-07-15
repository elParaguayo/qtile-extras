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
from collections import deque
from itertools import cycle

from libqtile import bar
from libqtile.command.base import expose_command
from libqtile.widget import base

NINETY_DEGREES = -math.pi / 2

# Colour palette
COLOURS = ["39f", "3f9", "9f3", "f93", "f39", "cc0", "c0c", "0cc"]

# Block shapes
SHAPES = [
    [[1, 1, 1, 1]],  # I
    [[1, 1], [1, 1]],  # O
    [[0, 1, 0], [1, 1, 1]],  # T
    [[1, 0, 0], [1, 1, 1]],  # J
    [[0, 0, 1], [1, 1, 1]],  # L
    [[0, 1, 1], [1, 1, 0]],  # S
    [[1, 1, 0], [0, 1, 1]],  # Z
    [[0, 1, 0], [1, 1, 1], [0, 1, 0]],  # +
]


# Rotation utilities
def rotate(shape):
    return [list(row)[::-1] for row in zip(*shape)]


def get_all_rotations(shape):
    rotations = []
    current = shape
    for _ in range(4):
        if current not in rotations:
            rotations.append(current)
        current = rotate(current)
    return rotations


class Tetris(base._Widget):
    """
    A completely pointless widget.

    Plays a mini game of "Tetris" in your bar with very, very basic AI
    control.

    There is no user control and this is just a little tribute to the original game that
    will, hopefully, bring a smile to your face. Howver, being honest, this will probably
    just get very distracting very quickly!

    The AI can be adjusted to tune the behaviour of how it decides where to place a shape.
    It looks at possible positions and scores them based on the following formula:

    .. code-block::

        (number of holes beneath blocks * weight_holes)
        - (row number of placed block * weight_row)
        - (number of rows to be completed * weight_completion)

    The option with the lowest score is selected,

    Can be used instead of a spacer widget in your bar. Options are available to have the
    widget be blank by default and trigger the game via commands.
    """

    orientations = base.ORIENTATION_BOTH

    defaults = [
        ("cell_size", 5, ""),
        ("speed", 10, "Maximum angle above/below horizontal"),
        (
            "blockify",
            False,
            "Show gaps between blocks. Best with cell size >= 5 as this reduces size of blocks.",
        ),
        ("gap_size", 1, "Size of 'blockify' gap."),
        ("weight_holes", 1000, "Weighting for holes created beneath piece"),
        ("weight_row", 400, "Weighting for row that shape is placed in."),
        ("weight_completion", 500, "Weighting for completing rows"),
        ("restart_interval", 2, "Interval between finished game and new game"),
        ("loop", True, "Whether a new game should start after the current one ends."),
        ("autostart", True, "Game runs as soon as the widget starts"),
    ]

    def __init__(self, length=bar.STRETCH, **config):
        base._Widget.__init__(self, length=length, **config)
        self.add_defaults(Tetris.defaults)
        self.started = False
        self.columns = 0
        self.rows = 0
        self.grid = []
        self.fall_grid = []
        self.is_falling = True
        self.shape = None
        self.found_position = False
        self.fall_row = 0
        self.fall_col = 0
        self.step_timer = None
        self.paused = False
        self.i = 0

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)

        orig_setter = type(self).length.fset

        def new_setter(self, value):
            orig_setter(self, value)
            self._set_width()

        type(self).length = type(self).length.setter(new_setter)

        self.columns = (self.height if self.bar.horizontal else self.width) // self.cell_size
        self.rows = (self.width if self.bar.horizontal else self.height) // self.cell_size

        self.shape_and_cols = zip(SHAPES, cycle(COLOURS))
        self.shape_dict = {col: shape for shape, col in self.shape_and_cols}
        self.step_interval = 1 / self.speed

        if self.autostart:
            self.timeout_add(0.5, self.restart)

    def _set_width(self):
        """Resize the grid if the length changes."""
        if not self.started:
            return

        self._stop_timers()

        # Work out how many extra rows we gain/lose
        row_count = self.length // self.cell_size
        grid_len = len(self.grid)
        diff = row_count - grid_len

        # Add/remove rows from the grids
        if diff > 0:
            for _ in range(diff):
                self.grid.insert(0, [0 for _ in range(self.columns)])
                self.fall_grid.insert(0, [0 for _ in range(self.columns)])
        elif diff < 0:
            for _ in range(abs(diff)):
                self.grid.pop(0)
                self.fall_grid.pop(0)

        # Update variables. Start dropping a new piece
        self.rows = row_count
        self.shape = None

        self.step_timer = self.timeout_add(self.step_interval, self.step)

    def _stop_timers(self):
        if self.step_timer is not None:
            self.step_timer.cancel()
            self.step_timer = None

    def restart(self):
        if self.width == 0:
            self.timeout_add(self.restart_interval, self.restart)
            return
        if not self.started:
            self.started = True
            self.clear()
            self.is_falling = True
            self.shape = None
            self.found_position = False
            self.fall_row = 0
            self.fall_col = 0
            self._start_game()

    def clear(self):
        self.grid = [[0 for _ in range(self.columns)] for _ in range(self.rows)]
        self.fall_grid = [[0 for _ in range(self.columns)] for _ in range(self.rows)]

    def _start_game(self):
        self.started = True
        self.step_timer = self.timeout_add(self.step_interval, self.step)
        self.draw()

    def step(self):
        """Decides what to do in each frame."""
        # No current shape so we need to pick one
        if self.shape is None:
            self.shape_colour, self.shape = random.choice(list(self.shape_dict.items()))
            self.found_position = False
            self.is_falling = False
            self.fall_row = 0
            self.fall_col = 0
            self.path = []

        # Find the best end location
        if not self.found_position:
            # AI picks best final placement
            self._best_shape, self._best_row, self._best_col = self.ai_choose_best_placement()

            # Start falling from top row (0) and some column (e.g., 0)
            start_row = 0
            start_col = self.columns // 2  # You can adjust this if needed

            # Find path to target position
            path = self.find_path(
                start_row, start_col, self._best_row, self._best_col, self._best_shape
            )
            if path is None:
                # No path found — could end game or pick different position
                self.timeout_add(self.restart_interval, self.restart)
                return

            self.path = path
            self.fall_row = start_row
            self.fall_col = start_col
            self.found_position = True
            self.is_falling = True

        # Animate the fall
        if self.is_falling:
            # Animate one step along path
            if self.path:
                move = self.path.pop(0)
                if move == "left":
                    self.fall_col -= 1
                elif move == "right":
                    self.fall_col += 1
                elif move == "down":
                    self.fall_row += 1

                # Draw shape at current position
                self.update_fall_grid(self._best_shape, self.fall_row, self.fall_col)

                self.is_falling = True
            else:
                # Path finished — lock piece
                self.place(self._best_shape, self.fall_row, self.fall_col)
                self.clear_lines()
                self.shape = None
                self.found_position = False
                self.is_falling = False
                self.fall_grid = [[0] * self.columns for _ in range(self.rows)]

        # Render the frame
        self.draw()

        if self.started:
            self.step_timer = self.timeout_add(self.step_interval, self.step)

    def update_fall_grid(self, shape, row, col):
        # Clear previous fall grid
        self.fall_grid = [[0] * self.columns for _ in range(self.rows)]
        for dy, line in enumerate(shape):
            for dx, cell in enumerate(line):
                if cell:
                    x = col + dx
                    y = row + dy
                    if 0 <= x < self.columns and 0 <= y < self.rows:
                        self.fall_grid[y][x] = self.shape_colour

    def find_path(self, start_row, start_col, target_row, target_col, shape):
        """
        Performs BFS to find a path for moving a shape from (start_row, start_col) to
        (target_row, target_col), including post-landing lateral movements.
        Returns the list of moves: ['down', 'down', 'right', ...]
        """
        moves = [("down", 1, 0), ("left", 0, -1), ("right", 0, 1)]
        visited = set()
        queue = deque()
        queue.append((start_row, start_col, []))

        while queue:
            row, col, path = queue.popleft()
            state = (row, col)

            if state in visited:
                continue
            visited.add(state)

            # If we're at the goal and the shape cannot fall further — success
            if row == target_row and col == target_col:
                if not self.can_place(shape, row + 1, col):
                    return path

            for move_name, dr, dc in moves:
                new_row = row + dr
                new_col = col + dc

                if (new_row, new_col) in visited:
                    continue

                if self.can_place(shape, new_row, new_col):
                    queue.append((new_row, new_col, path + [move_name]))

        return None  # No valid path found

    def animate_fall(self, shape, row, col):
        self.fall_grid = [[0 for _ in range(self.columns)] for _ in range(self.rows)]
        if self.can_place(shape, row + 1, col):
            self.fall_row += 1
        else:
            self.is_falling = False

        for dy, line in enumerate(shape):
            for dx, cell in enumerate(line):
                if cell:
                    x = col + dx
                    y = self.fall_row + dy
                    if 0 <= x < self.columns and 0 <= y < self.rows:
                        self.fall_grid[y][x] = self.shape_colour

    def ai_choose_best_placement(self):
        best_score = float("inf")
        best_row = 0
        best_col = 0
        best_shape = self.shape

        for rotation in get_all_rotations(self.shape):
            shape_height = len(rotation)
            shape_width = len(rotation[0])

            for col in range(self.columns - shape_width + 1):
                row = 0
                while row + shape_height <= self.rows and self.can_place(rotation, row, col):
                    row += 1
                row -= 1  # last valid row

                if row < 0:
                    continue

                # Simulate placement
                temp_grid = [r.copy() for r in self.grid]
                for dy, line in enumerate(rotation):
                    for dx, cell in enumerate(line):
                        if cell:
                            temp_grid[row + dy][col + dx] = 1

                # Count holes below filled cells
                holes = 0
                for x in range(self.columns):
                    block_found = False
                    for y in range(self.rows):
                        if temp_grid[y][x]:
                            block_found = True
                        elif block_found:
                            holes += 1

                # Count completed rows
                completed_rows = sum(1 for r in temp_grid if all(r))

                # Final score - weightings can be adjusted to trigger different behaviour
                score = (
                    holes * self.weight_holes
                    - row * self.weight_row
                    - completed_rows * self.weight_completion
                )

                if score < best_score:
                    best_score = score
                    best_shape = rotation
                    best_row = row
                    best_col = col

        return best_shape, best_row, best_col

    def can_place(self, shape, row, col):
        for dy, line in enumerate(shape):
            for dx, cell in enumerate(line):
                if cell:
                    x, y = col + dx, row + dy
                    if x < 0 or x >= self.columns or y < 0 or y >= self.rows:
                        return False
                    if self.grid[y][x]:
                        return False
        return True

    def place(self, shape, row, col):
        for dy, line in enumerate(shape):
            for dx, cell in enumerate(line):
                if cell:
                    self.grid[row + dy][col + dx] = self.shape_colour

    def clear_lines(self):
        new_grid = []
        cleared_rows = 0
        for row in self.grid:
            if all(row):
                cleared_rows += 1
            else:
                new_grid.append(row)

        for _ in range(cleared_rows):
            new_grid.insert(0, [0] * self.columns)

        self.grid = new_grid
        return cleared_rows

    def draw_grid(self):
        ctx = self.drawer.ctx
        for y in range(self.rows):
            for x in range(self.columns):
                cell = self.fall_grid[y][x] or self.grid[y][x]
                if cell:
                    self.drawer.set_source_rgb(cell)
                    ctx.rectangle(
                        x * self.cell_size, y * self.cell_size, self.cell_size, self.cell_size
                    )
                    ctx.fill()

    def draw_gridlines(self):
        ctx = self.drawer.ctx

        self.drawer.set_source_rgb(self.background or self.bar.background)
        self.drawer.ctx.set_line_width(self.gap_size)

        w = self.width
        h = self.height

        x_range = (w // self.cell_size) + 1
        y_range = (h // self.cell_size) + 1

        for x in range(x_range):
            ctx.move_to(x * self.cell_size, 0)
            ctx.line_to(x * self.cell_size, h)
        for y in range(y_range):
            ctx.move_to(0, y * self.cell_size)
            ctx.line_to(w, y * self.cell_size)
        ctx.stroke()

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)

        if self.started:
            self.drawer.ctx.save()

            if self.bar.horizontal:
                self.drawer.ctx.translate(0, self.height)
                self.drawer.ctx.rotate(NINETY_DEGREES)

            self.draw_grid()

            self.drawer.ctx.restore()

            if self.blockify:
                self.draw_gridlines()

        self.draw_at_default_position()

    @expose_command
    def start(self):
        """Start game."""
        self.restart()

    @expose_command
    def stop(self):
        """Stop game."""
        self.started = False
        self._stop_timers()
        self.clear()
        self.draw()

    @expose_command
    def pause(self):
        """Pause game."""
        if not self.started:
            return

        if self.step_timer is not None:
            self._stop_timers()
        else:
            self.step_timer = self.timeout_add(self.step_interval, self.step)

    @expose_command
    def toggle_blocks(self):
        """Toggles gaps between blocks."""
        self.blockify = not self.blockify
