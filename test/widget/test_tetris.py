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
import pytest
from libqtile.bar import Bar
from libqtile.config import Screen

from qtile_extras.widget.tetris import Tetris, get_all_rotations, rotate
from test.helpers import BareConfig


@pytest.fixture
def tmanager(manager_nospawn, request):
    config = {"speed": 0.001, "length": 100, "autostart": False, "blockify": True}

    class PatchedTetris(Tetris):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **{**config, **kwargs})
            self.name = "tetris"
            self.place_count = 0

        def timeout_add(self, *args, **kwargs):
            return None

        def place(self, *args, **kwargs):
            super().place(*args, **kwargs)
            self.place_count += 1

    class TetrisConfig(BareConfig):
        screens = [
            Screen(top=Bar([PatchedTetris()], 50)),
        ]

    manager_nospawn.start(TetrisConfig)

    yield manager_nospawn


# -- SHAPE TESTING -- #


def test_rotate():
    shape = [[1, 0], [1, 1]]
    expected = [[1, 1], [1, 0]]
    assert rotate(shape) == expected


def test_get_all_rotations():
    shape = [[1, 0], [1, 1]]
    rotations = get_all_rotations(shape)
    assert len(rotations) >= 2
    assert all(isinstance(r, list) for r in rotations)


# -- TETRIS LOGIC -- #


@pytest.fixture
def widget():
    """Fixture for a dummy Tetris widget."""
    w = Tetris()
    w.columns = 5
    w.rows = 5
    w.grid = [[0 for _ in range(w.columns)] for _ in range(w.rows)]
    return w


def test_can_place(widget):
    shape = [[1, 1], [1, 1]]
    assert widget.can_place(shape, 0, 0) is True
    widget.grid[0][0] = 1  # Block it
    assert widget.can_place(shape, 0, 0) is False


def test_place_and_clear_lines(widget):
    # Fill a row
    row = [1, 1, 1, 1, 1]
    widget.grid[-1] = row.copy()
    cleared = widget.clear_lines()
    assert cleared == 1
    assert all(cell == 0 for cell in widget.grid[0])


def test_ai_choose_best_placement(widget):
    widget.shape = [[1, 1], [1, 1]]
    widget.weight_holes = 1000
    widget.weight_row = 10
    widget.weight_completion = 20
    shape, row, col = widget.ai_choose_best_placement()
    assert isinstance(shape, list)
    assert 0 <= row < widget.rows
    assert 0 <= col < widget.columns


def test_find_path_success(widget):
    shape = [[1]]
    path = widget.find_path(0, 0, 4, 0, shape)
    assert path is not None
    assert path.count("down") >= 4


def test_find_path_fail(widget):
    shape = [[1]]
    widget.grid[1][0] = 1  # Block directly below
    path = widget.find_path(0, 0, 1, 0, shape)
    assert path is None


def test_tetris_game_steps(tmanager):
    tetris = tmanager.c.widget["tetris"]

    def step():
        tetris.eval("self.step()")

    def assert_eval(statement):
        _, result = tetris.eval(statement)
        assert result == "True"

    def get_grid():
        _, grid = tetris.eval("self.grid")
        return grid

    assert_eval("self.shape is None")

    tetris.start()
    assert_eval("self.is_falling")
    assert_eval("self.fall_row == 0")
    assert_eval("self.fall_col == 0")
    assert_eval("self.shape is None")
    assert_eval("not self.found_position")
    grid1 = get_grid()

    step()
    assert_eval("self.shape is not None")
    assert_eval("self.found_position")
    assert_eval("bool(self.path)")
    assert_eval("self.place_count == 0")
    grid2 = get_grid()
    assert grid1 == grid2

    _, fall_grid1 = tetris.eval("self.fall_grid")

    step()
    _, fall_grid2 = tetris.eval("self.fall_grid")
    assert fall_grid1 != fall_grid2

    count = 0

    while get_grid() == grid1:
        step()
        count += 1
        if count > 100:
            assert False, "Grid not updated after 100 steps"

    assert count > 1
    assert_eval("self.place_count == 1")
