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
import os
import tempfile

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import pytest
from pytest_lazyfixture import lazy_fixture

import qtile_extras.widget.currentlayout

BAR_SIZE = 50
PADDING = 3
DEFAULT_ICON_SIZE = BAR_SIZE - 1
DEFAULT_QTILE_SIZE = BAR_SIZE - 2  # In qtile, default size in bar height - 2


class MissingIconLayout(libqtile.layout.Max):
    pass


@pytest.fixture
def layout_list(request):
    layouts = [libqtile.layout.Max(), libqtile.layout.MonadTall()]
    if extra := getattr(request, "param", None):
        layouts.append(extra)

    yield layouts


@pytest.fixture
def temp_icons(layout_list):
    with tempfile.TemporaryDirectory() as tempdir:
        for layout in layout_list:
            icon_file = os.path.join(tempdir, f"layout-{layout.name}.png")
            with open(icon_file, "w") as f:
                f.write("Not a proper image file!")

        yield {"custom_icon_paths": [tempdir]}


@pytest.fixture(scope="function")
def currentlayout_manager(request, layout_list, manager_nospawn):
    # We need to enable the mask here otherwise the widget is just the default qtile one.
    widget = qtile_extras.widget.currentlayout.CurrentLayoutIcon(
        **{**{"use_mask": True}, **getattr(request, "param", dict())}
    )

    class CurrentLayoutConfig(libqtile.confreader.Config):
        auto_fullscreen = True
        keys = []
        mouse = []
        groups = [
            libqtile.config.Group("a"),
        ]
        layouts = layout_list
        floating_layout = libqtile.resources.default_config.floating_layout
        screens = [
            libqtile.config.Screen(
                top=libqtile.bar.Bar(
                    [widget],
                    BAR_SIZE,
                ),
            )
        ]

    # with contextlib.suppress((AttributeError, )):
    manager_nospawn.start(CurrentLayoutConfig)
    yield manager_nospawn


@pytest.mark.parametrize(
    "currentlayout_manager,expected",
    [
        ({}, DEFAULT_ICON_SIZE + 2 * PADDING),
        ({"use_mask": False}, DEFAULT_QTILE_SIZE + 2 * PADDING),
        ({"scale": 0.5}, (BAR_SIZE - 1) // 2 + 2 * PADDING),
    ],
    indirect=["currentlayout_manager"],
)
def test_currentlayouticon_icon_size(currentlayout_manager, expected):
    info = currentlayout_manager.c.widget["currentlayouticon"].info()
    assert info["length"] == expected


@pytest.mark.parametrize("layout_list", [MissingIconLayout()], indirect=True)
def test_currentlayouticon_missing_icon(currentlayout_manager, logger):
    recs = logger.get_records("setup")
    assert recs
    assert recs[0].levelname == "WARNING"
    assert recs[0].msg == 'No icon found for layout "missingiconlayout".'


@pytest.mark.parametrize("currentlayout_manager", [lazy_fixture("temp_icons")], indirect=True)
def test_currentlayouticon_bad_icon(currentlayout_manager, logger):
    recs = logger.get_records("setup")
    assert recs
    assert recs[0].levelname == "WARNING"
    assert recs[0].msg.startswith("Failed to load icon")
