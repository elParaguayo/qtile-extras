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
from pathlib import Path

from qtile_extras.popup.toolkit import (
    PopupCircularProgress,
    PopupImage,
    PopupRelativeLayout,
    PopupSlider,
    PopupText,
)

IMAGES_FOLDER = Path(__file__).resolve() / ".." / ".." / ".." / "resources" / "media-icons"
DEFAULT_IMAGE = (IMAGES_FOLDER / "default.png").resolve().as_posix()

DEFAULT_LAYOUT = PopupRelativeLayout(
    None,
    width=400,
    height=200,
    controls=[
        PopupText(
            "",
            name="title",
            pos_x=0.35,
            pos_y=0.1,
            width=0.55,
            height=0.14,
            h_align="left",
            v_align="top",
        ),
        PopupText(
            "",
            name="artist",
            pos_x=0.35,
            pos_y=0.24,
            width=0.55,
            height=0.14,
            h_align="left",
            v_align="middle",
        ),
        PopupText(
            "",
            name="album",
            pos_x=0.35,
            pos_y=0.38,
            width=0.55,
            height=0.14,
            h_align="left",
            v_align="bottom",
        ),
        PopupImage(
            name="artwork",
            filename=DEFAULT_IMAGE,
            pos_x=0.1,
            pos_y=0.1,
            width=0.21,
            height=0.42,
        ),
        PopupSlider(name="progress", pos_x=0.1, pos_y=0.6, width=0.8, height=0.1, marker_size=0),
        PopupImage(
            name="previous",
            filename=(IMAGES_FOLDER / "previous.svg").resolve().as_posix(),
            mask=True,
            pos_x=0.125,
            pos_y=0.8,
            width=0.15,
            height=0.1,
        ),
        PopupImage(
            name="play_pause",
            filename=(IMAGES_FOLDER / "play_pause.svg").resolve().as_posix(),
            mask=True,
            pos_x=0.325,
            pos_y=0.8,
            width=0.15,
            height=0.1,
        ),
        PopupImage(
            name="stop",
            filename=(IMAGES_FOLDER / "stop.svg").resolve().as_posix(),
            mask=True,
            pos_x=0.525,
            pos_y=0.8,
            width=0.15,
            height=0.1,
        ),
        PopupImage(
            name="next",
            filename=(IMAGES_FOLDER / "next.svg").resolve().as_posix(),
            mask=True,
            pos_x=0.725,
            pos_y=0.8,
            width=0.15,
            height=0.1,
        ),
    ],
    close_on_click=False,
)

COMPACT_LAYOUT = PopupRelativeLayout(
    None,
    width=150,
    height=220,
    controls=[
        PopupImage(
            name="artwork",
            filename=DEFAULT_IMAGE,
            pos_x=0.1,
            pos_y=0.05,
            width=0.8,
            height=0.4,
        ),
        PopupText(
            "",
            name="title",
            pos_x=0.1,
            pos_y=0.5,
            width=0.8,
            height=0.075,
            h_align="left",
            v_align="top",
        ),
        PopupText(
            "",
            name="artist",
            pos_x=0.1,
            pos_y=0.575,
            width=0.8,
            height=0.075,
            h_align="left",
            v_align="middle",
        ),
        PopupText(
            "",
            name="album",
            pos_x=0.1,
            pos_y=0.65,
            width=0.8,
            height=0.075,
            h_align="left",
            v_align="bottom",
        ),
        PopupImage(
            name="previous",
            filename=(IMAGES_FOLDER / "previous.svg").resolve().as_posix(),
            mask=True,
            pos_x=0.15,
            pos_y=0.75,
            width=0.1,
            height=0.25,
            highlight="00ffff",
            highlight_method="mask",
        ),
        PopupImage(
            name="play_pause",
            filename=(IMAGES_FOLDER / "play_pause.svg").resolve().as_posix(),
            mask=True,
            pos_x=0.4,
            pos_y=0.75,
            width=0.2,
            height=0.25,
            highlight="00ffff",
            highlight_method="mask",
        ),
        PopupCircularProgress(
            name="progress",
            pos_x=0.2,
            pos_y=0.75,
            width=0.6,
            height=0.25,
            colour_below="00ffff",
        ),
        PopupImage(
            name="next",
            filename=(IMAGES_FOLDER / "next.svg").resolve().as_posix(),
            mask=True,
            pos_x=0.75,
            pos_y=0.75,
            width=0.1,
            height=0.25,
            highlight="00ffff",
            highlight_method="mask",
        ),
    ],
    close_on_click=False,
)
