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
from pathlib import Path

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import pytest
from libqtile.command.base import expose_command

from qtile_extras.widget import AnimatedImage
from test.helpers import Retry

LOCAL_ICON = (
    Path(__file__).parent
    / ".."
    / ".."
    / "qtile_extras"
    / "resources"
    / "github-icons"
    / "github.svg"
)


class PatchedWidget(AnimatedImage):
    def __init__(self, *args, **kwargs):
        AnimatedImage.__init__(self, *args, **kwargs)
        self._displayed_images = []

    def _queue_next(self):
        """Add each displayed image index to our list."""
        AnimatedImage._queue_next(self)
        self._displayed_images.append(self.index)

    @expose_command
    def finished(self):
        """Return list of displayed indexes only when looping finished."""
        if self._do_loop:
            return []

        return self._displayed_images

    @expose_command
    def looping(self):
        if not self._do_loop:
            return False

        return len(self._displayed_images) > 0


@pytest.fixture(scope="function")
def widget(request, manager_nospawn):
    class AnimatedImageConfig(libqtile.confreader.Config):
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
                    [
                        PatchedWidget(
                            filenames=[LOCAL_ICON, LOCAL_ICON, LOCAL_ICON],
                            name="animatedimage",
                            loop_interval=0.1,
                            **getattr(request, "param", dict())
                        )
                    ],
                    50,
                ),
            )
        ]

    manager_nospawn.start(AnimatedImageConfig)
    yield manager_nospawn.c.widget["animatedimage"]


def config(**kwargs):
    return pytest.mark.parametrize("widget", [kwargs], indirect=True)


@Retry(ignore_exceptions=(AssertionError,))
def assert_shown_images(widget, pattern, negate=False):
    if not negate:
        assert widget.finished() == pattern
    else:
        assert widget.finished() != pattern


@Retry(ignore_exceptions=(AssertionError,))
def assert_looping(widget):
    assert widget.looping()


def test_default(widget):
    assert_shown_images(widget, [])
    widget.animate()
    assert_shown_images(widget, [0, 1, 2])


@config(loop_count=3)
def test_multiple_loops(widget):
    assert_shown_images(widget, [])
    widget.animate()
    assert_shown_images(widget, [0, 1, 2] * 3)


@config(loop_count=3)
def test_stop(widget):
    assert_shown_images(widget, [])
    widget.animate()
    assert_looping(widget)
    widget.stop()
    assert_shown_images(widget, [0, 1, 2] * 10, negate=True)


def test_width_default(widget):
    assert widget.info()["width"] == 56


@config(padding=0)
def test_width_no_padding(widget):
    assert widget.info()["width"] == 50
