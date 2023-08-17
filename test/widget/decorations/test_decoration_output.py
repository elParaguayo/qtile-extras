# Copyright (c) 2023 elParaguayo
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

from qtile_extras import widget
from qtile_extras.widget.decorations import BorderDecoration, PowerLineDecoration, RectDecoration


def widgets(decorations=list()):
    return [
        widget.TextBox(
            "This is a test of widget decorations...",
            name="red",
            background="ff0000",
            padding=10,
            font="Noto Sans",
            decorations=decorations,
        ),
        widget.TextBox(
            "...in qtile-extras.",
            name="blue",
            background="0000ff",
            padding=10,
            font="Noto Sans",
            decorations=decorations,
        ),
    ]


params = []

# POWERLINE DECORATIONS
for path in (
    "arrow_left",
    "arrow_right",
    "forward_slash",
    "back_slash",
    "zig_zag",
    "rounded_left",
    "rounded_right",
):
    decorations = [PowerLineDecoration(path=path)]
    params.append({"name": f"powerline-{path}", "widgets": widgets(decorations)})

    decorations = [PowerLineDecoration(path=path, padding_y=8)]
    params.append({"name": f"powerline-{path}-padding", "widgets": widgets(decorations)})

decorations = [PowerLineDecoration(path=[(0, 0.2), (0.5, 0.2), (0.5, 0.8), (0, 0.8)])]
params.append({"name": "powerline-custom-path", "widgets": widgets(decorations)})

# RECTDECORATION
params.append({"name": "rect-default", "widgets": widgets([RectDecoration(colour="ff00ff")])})
params.append(
    {
        "name": "rect-default-line",
        "widgets": widgets([RectDecoration(colour="ff00ff", line_width=2, padding=4, radius=10)]),
    }
)
params.append(
    {
        "name": "rect-default-filled",
        "widgets": widgets([RectDecoration(colour="ff00ff", filled=True, padding=4, radius=10)]),
    }
)
params.append(
    {
        "name": "rect-default-group-filled",
        "widgets": widgets(
            [RectDecoration(colour="770077", filled=True, padding=8, group=True, radius=10)]
        ),
    }
)
params.append(
    {
        "name": "rect-default-group-filled-no-radius",
        "widgets": widgets(
            [RectDecoration(colour="770077", filled=True, padding=8, group=True, radius=0)]
        ),
    }
)
params.append(
    {
        "name": "rect-default-group-filled-widget-background",
        "widgets": widgets(
            [
                RectDecoration(
                    use_widget_background=True, filled=True, padding=8, group=True, radius=10
                )
            ]
        ),
    }
)
params.append(
    {
        "name": "rect-stacked",
        "widgets": widgets(
            [
                RectDecoration(
                    use_widget_background=True, filled=True, padding=6, group=True, radius=10
                ),
                RectDecoration(colour="007777", filled=True, padding=10, group=True, radius=10),
            ]
        ),
    }
)

# BORDERDECORATION
params.append(
    {
        "name": "border-default",
        "widgets": widgets([BorderDecoration()]),
    }
)
params.append(
    {
        "name": "border-default-grouped",
        "widgets": widgets([BorderDecoration(group=True)]),
    }
)
params.append(
    {
        "name": "border-default-padding",
        "widgets": widgets([BorderDecoration(padding=4)]),
    }
)
params.append(
    {
        "name": "border-default-grouped-padding",
        "widgets": widgets([BorderDecoration(group=True, padding=4)]),
    }
)
params.append(
    {
        "name": "border-default-grouped-padding_x",
        "widgets": widgets([BorderDecoration(group=True, padding_x=4)]),
    }
)
params.append(
    {
        "name": "border-default-grouped-padding_y",
        "widgets": widgets([BorderDecoration(group=True, padding_y=4)]),
    }
)
for i in range(4):
    borders = [4 if x == i else 0 for x in range(4)]
    name = ("N", "E", "S", "W")[i]
    decorations = [BorderDecoration(colour="999900", border_width=borders)]
    params.append({"name": f"border-single-{name}", "widgets": widgets(decorations)})
    decorations = [BorderDecoration(colour="999900", border_width=borders, group=True)]
    params.append({"name": f"border-single-{name}-grouped", "widgets": widgets(decorations)})
params.append(
    {
        "name": "border-stacked",
        "widgets": widgets(
            [
                BorderDecoration(border_width=[4, 0, 0, 0], colour="00ff00"),
                BorderDecoration(border_width=[0, 4, 0, 0], colour="ffff00"),
                BorderDecoration(border_width=[0, 0, 4, 0], colour="00ffff"),
                BorderDecoration(border_width=[0, 0, 0, 4], colour="ff00ff"),
            ]
        ),
    }
)
params.append(
    {
        "name": "border-stacked-grouped",
        "widgets": widgets(
            [
                BorderDecoration(border_width=[4, 0, 0, 0], colour="00ff00", group=True),
                BorderDecoration(border_width=[0, 4, 0, 0], colour="ffff00", group=True),
                BorderDecoration(border_width=[0, 0, 4, 0], colour="00ffff", group=True),
                BorderDecoration(border_width=[0, 0, 0, 4], colour="ff00ff", group=True),
            ]
        ),
    }
)
params.append(
    {
        "name": "border-stacked-same-position",
        "widgets": widgets(
            [
                BorderDecoration(border_width=[4, 0, 0, 0], colour="00ff00", group=True),
                BorderDecoration(
                    border_width=[4, 0, 0, 0], colour="ffff00", group=True, padding_y=4
                ),
                BorderDecoration(
                    border_width=[4, 0, 0, 0], colour="00ffff", group=True, padding_y=8
                ),
            ]
        ),
    }
)

# COMBOS
decorations = [
    RectDecoration(
        use_widget_background=True, padding=5, filled=True, radius=10, clip=True, group=True
    ),
    PowerLineDecoration(path="arrow_right", padding_y=5),
]
params.append(
    {
        "name": "combo-rect-plus-powerline",
        "widgets": widgets(decorations),
    }
)


@pytest.mark.parametrize("camera", params, indirect=True, ids=[x["name"] for x in params])
def test_decoration_output(camera):
    camera.take_screenshot()
    camera.assert_similar()
