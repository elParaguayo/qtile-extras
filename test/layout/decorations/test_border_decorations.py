# Copyright (c) 2024 elParaguayo
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
from libqtile.config import Screen
from libqtile.confreader import Config, ConfigError
from libqtile.layout import Matrix

from qtile_extras.layout.decorations import (
    GradientBorder,
    GradientFrame,
    ScreenGradientBorder,
    SolidEdge,
)


@pytest.fixture
def manager(request, manager_nospawn):
    class BorderDecorationConfig(Config):
        decoration = getattr(request, "param", None)
        if decoration is None:
            raise ValueError("No border decoration provided")

        layouts = [Matrix(border_focus=decoration)]
        screens = [Screen()]

    manager_nospawn.start(BorderDecorationConfig)

    yield manager_nospawn


@pytest.mark.parametrize(
    "manager",
    [
        GradientFrame(),
        GradientFrame(colours=["f00", "0f0", "00f"]),
        GradientBorder(),
        GradientBorder(colours=["f00", "0f0", "00f"]),
        GradientBorder(colours=["f00", "0f0", "00f"], points=[(0, 0), (1, 0)]),
        GradientBorder(colours=["f00", "0f0", "00f"], offsets=[0, 0.1, 1]),
        GradientBorder(colours=["f00", "0f0", "00f"], radial=True),
        ScreenGradientBorder(),
        ScreenGradientBorder(colours=["f00", "0f0", "00f"], points=[(0, 0), (1, 0)]),
        ScreenGradientBorder(colours=["f00", "0f0", "00f"], offsets=[0, 0.1, 1]),
        ScreenGradientBorder(colours=["f00", "0f0", "00f"], radial=True),
        # SolidEdge(),
        # SolidEdge(colours=["f00", "00f", "f00", "00f"])
    ],
    indirect=True,
)
def test_window_decoration(manager):
    manager.test_window("one")
    manager.test_window("two")
    assert True


@pytest.mark.parametrize(
    "classname,config",
    [
        (GradientBorder, {"colours": "f00"}),  # not a list
        (GradientBorder, {"colours": [1, 2, 3, 4]}),  # not a valid color
        (
            GradientBorder,
            {"colours": ["f00", "0ff"], "offsets": [0, 0.5, 1]},
        ),  # offsets doesn't match colours length
        (GradientFrame, {"colours": "f00"}),  # not a list
        (GradientFrame, {"colours": [1, 2, 3, 4]}),  # not a valid color
        (ScreenGradientBorder, {"colours": "f00"}),  # not a list
        (ScreenGradientBorder, {"colours": [1, 2, 3, 4]}),  # not a valid color
        (
            ScreenGradientBorder,
            {"colours": ["f00", "0ff"], "offsets": [0, 0.5, 1]},
        ),  # offsets doesn't match colours length
        (SolidEdge, {"colours": ["f00", "f00"]}),  # not enough values
        (SolidEdge, {"colours": "f00"}),  # not a list
        (SolidEdge, {"colours": [1, 2, 3, 4]}),  # not a valid color
    ],
)
def test_decoration_config_errors(classname, config):
    with pytest.raises(ConfigError):
        classname(**config)
