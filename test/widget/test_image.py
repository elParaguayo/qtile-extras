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
from pathlib import Path

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import pytest

import qtile_extras.widget.image

LOCAL_ICON = (
    Path(__file__).parent
    / ".."
    / ".."
    / "qtile_extras"
    / "resources"
    / "github-icons"
    / "github.svg"
)
WEB_ICON = "https://raw.githubusercontent.com/elParaguayo/qtile-extras/main/qtile_extras/resources/github-icons/github.svg"

BAR_SIZE = 50
PADDING = 3

RAW_ICON_SIZE = 1030


@pytest.fixture(scope="function")
def image_manager(request, manager_nospawn):
    widget = qtile_extras.widget.image.Image

    class ImageConfig(libqtile.confreader.Config):
        auto_fullscreen = True
        keys = []
        mouse = []
        groups = [
            libqtile.config.Group("a"),
        ]
        layouts = [libqtile.layout.Max()]
        floating_layout = libqtile.resources.default_config.floating_layout
        screens = [
            libqtile.config.Screen(
                top=libqtile.bar.Bar(
                    [widget(**getattr(request, "param", dict()))],
                    BAR_SIZE,
                ),
                left=libqtile.bar.Bar(
                    [widget(name="left_image", **getattr(request, "param", dict()))],
                    BAR_SIZE,
                ),
            )
        ]

    manager_nospawn.start(ImageConfig)
    yield manager_nospawn


@pytest.mark.parametrize(
    "image_manager,expected",
    [
        ({}, 0),
        ({"filename": LOCAL_ICON}, BAR_SIZE + 2 * PADDING),
        ({"filename": WEB_ICON}, BAR_SIZE + 2 * PADDING),
        ({"filename": LOCAL_ICON, "margin_y": 10}, BAR_SIZE + 2 * PADDING - 2 * 10),
        ({"filename": LOCAL_ICON, "scale": False}, RAW_ICON_SIZE),
    ],
    indirect=["image_manager"],
)
def test_image_size_horizontal(image_manager, expected):
    top_info = image_manager.c.widget["image"].info()
    assert top_info["length"] == expected


@pytest.mark.parametrize(
    "image_manager,expected",
    [
        ({}, 0),
        ({"filename": LOCAL_ICON}, BAR_SIZE + 2 * PADDING),
        ({"filename": WEB_ICON}, BAR_SIZE + 2 * PADDING),
        ({"filename": LOCAL_ICON, "margin_x": 10}, BAR_SIZE + 2 * PADDING - 2 * 10),
        ({"filename": LOCAL_ICON, "scale": False}, RAW_ICON_SIZE),
    ],
    indirect=["image_manager"],
)
def test_image_size_vertical(image_manager, expected):
    left_info = image_manager.c.widget["left_image"].info()
    assert left_info["length"] == expected


@pytest.mark.parametrize(
    "image_manager",
    [
        {"filename": LOCAL_ICON, "mask": True},
    ],
    indirect=["image_manager"],
)
def test_image_size_mask(image_manager, logger):
    recs = logger.get_records("setup")
    assert not recs

    recs = logger.get_records("call")
    assert not recs


@pytest.mark.flaky(reruns=5)
def test_no_filename(image_manager, logger):
    recs = logger.get_records("setup")
    assert recs

    assert recs[0].levelname == "WARNING"
    assert recs[0].msg == "Image filename not set!"


@pytest.mark.parametrize("image_manager", [{"filename": "/does/not/exist"}], indirect=True)
@pytest.mark.flaky(reruns=5)
def test_no_image(image_manager, logger):
    recs = logger.get_records("setup")
    assert recs

    assert recs[0].levelname == "WARNING"
    assert recs[0].msg.startswith("Image does not exist")
