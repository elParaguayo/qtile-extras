# Copyright (c) 2021 elParaguayo
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
import json
import os
import shutil
from functools import partial
from pathlib import Path

import cairocffi
import pytest
from libqtile.bar import Bar
from libqtile.command.base import expose_command
from libqtile.config import Group, Key, Screen
from libqtile.lazy import lazy

from qtile_extras.popup.toolkit import _PopupLayout
from test.helpers import DBusPopup, Retry


@pytest.fixture(scope="function")
def vertical(request):
    yield getattr(request, "param", False)


vertical_bar = pytest.mark.parametrize("vertical", [True], indirect=True)


@pytest.fixture(scope="function")
def sni(request):
    yield getattr(request, "param", False)


statusnotifier = pytest.mark.parametrize("sni", [True], indirect=True)


@pytest.fixture(scope="function")
def gm(request):
    yield getattr(request, "param", False)


globalmenu = pytest.mark.parametrize("gm", [True], indirect=True)


@pytest.fixture(scope="session")
def target():
    folder = Path(__file__).parent / "screenshots"
    docs_folder = (
        Path(__file__).parent
        / ".."
        / ".."
        / ".."
        / "docs"
        / "_static"
        / "screenshots"
        / "widgets"
    )
    log = os.path.join(docs_folder, "shots.json")
    if folder.is_dir():
        shutil.rmtree(folder)
    folder.mkdir()
    key = {}

    def get_file_name(w_name, config):
        nonlocal key

        # Convert config into a string of key=value
        if isinstance(config, dict):
            entry = ", ".join(f"{k}={repr(v)}" for k, v in config.items())
        else:
            entry = config

        # Check if widget is in the key dict
        if w_name not in key:
            key[w_name] = {}

        # Increment the index number
        indexes = [int(x) for x in key[w_name]]
        index = max(indexes) + 1 if indexes else 1

        # Record the config
        key[w_name][index] = entry

        # Define the target folder and check it exists
        shots_dir = os.path.join(folder, w_name)
        if not os.path.isdir(shots_dir):
            os.mkdir(shots_dir)

        # Returnt the path for the screenshot
        return os.path.join(shots_dir, f"{index}.png")

    yield get_file_name

    # We copy the screenshots from the test folder to the docs folder at the end
    # This prevents pytest deleting the files itself

    # Remove old screenshots
    if os.path.isdir(docs_folder):
        shutil.rmtree(docs_folder)

    # Copy to the docs folder
    shutil.copytree(folder, docs_folder)
    with open(log, "w") as f:
        json.dump(key, f)

    # Clear up the tests folder
    shutil.rmtree(folder)


@pytest.fixture
def screenshot_manager(
    widget, request, manager_nospawn, minimal_conf_noscreen, target, vertical, sni, gm
):
    """
    Create a manager instance for the screenshots. Individual "tests" should only call
    `screenshot_manager.take_screenshot()` but the destination path is also available in
    `screenshot_manager.target`.

    Widgets should create their own `widget` fixture in the relevant file (applying
    monkeypatching etc as necessary).

    Configs can then be passed by parametrizing "screenshot_manager".
    """
    # Partials are used to hide some aspects of the config from being displayed in the
    # docs. We need to split these out into their constituent parts.
    if type(widget) is partial:
        widget_class = widget.func
        widget_config = widget.keywords
    else:
        widget_class = widget
        widget_config = {}

    class ScreenshotWidget(widget_class):
        def __init__(self, *args, **kwargs):
            widget_class.__init__(self, *args, **kwargs)
            # We need the widget's name to be the name of the inherited class
            self.name = widget_class.__name__.lower()

        def _configure(self, bar, screen):
            widget_class._configure(self, bar, screen)

            # By setting `has_mirrors` to True, the drawer will keep a copy of the latest
            # contents in a separate RecordingSurface which we can access for our screenshots.
            self.drawer.has_mirrors = True

        @expose_command()
        def take_screenshot(self, target):
            if not self.configured:
                return

            source = self.drawer.last_surface

            dest = cairocffi.ImageSurface(cairocffi.FORMAT_ARGB32, self.width, self.height)
            with cairocffi.Context(dest) as ctx:
                ctx.set_source_surface(source)
                ctx.paint()

            dest.write_to_png(target)

        @expose_command()
        def take_screenshot_with_popup(self, target):
            if not self.configured:
                return

            # Check if we have an active popup
            popup = getattr(self, "popup", None)
            menu = getattr(self, "menu", None)
            win = popup if popup else menu
            if win is None:
                return

            width = max(self.width, win.width)
            height = self.height + win.height

            if isinstance(win, _PopupLayout):
                win = win.popup

            dest = cairocffi.ImageSurface(cairocffi.FORMAT_ARGB32, width, height)
            with cairocffi.Context(dest) as ctx:
                ctx.set_source_surface(self.drawer.last_surface)
                ctx.paint()
                ctx.translate(win.x, win.y)
                ctx.set_source_surface(win.drawer._xcb_surface)
                ctx.paint()

            dest.write_to_png(target)

        @expose_command()
        def take_extended_popup_screenshot(self, target):
            if not self.configured:
                return

            # Check if we have an active popup
            popup = getattr(self, "extended_popup")
            if popup is None:
                return

            dest = cairocffi.ImageSurface(cairocffi.FORMAT_ARGB32, popup.width, popup.height)
            with cairocffi.Context(dest) as ctx:
                ctx.set_source_surface(popup.popup.drawer._xcb_surface)
                ctx.paint()

            dest.write_to_png(target)

    class ScreenshotBar(Bar):
        def _configure(self, qtile, screen, **kwargs):
            Bar._configure(self, qtile, screen, **kwargs)

            # By setting `has_mirrors` to True, the drawer will keep a copy of the latest
            # contents in a separate RecordingSurface which we can access for our screenshots.
            self.drawer.has_mirrors = True

        @expose_command()
        def take_screenshot(self, target, x=0, y=0, width=None, height=None):
            """Takes a screenshot of the bar. The area can be selected."""
            if not self._configured:
                return

            if width is None:
                width = self.drawer.width

            if height is None:
                height = self.drawer.height

            # Widgets aren't drawn to the bar's drawer so we first need to render them all to a single surface
            bar_copy = cairocffi.ImageSurface(
                cairocffi.FORMAT_ARGB32, self.drawer.width, self.drawer.height
            )
            with cairocffi.Context(bar_copy) as ctx:
                ctx.set_source_surface(self.drawer.last_surface)
                ctx.paint()

                for i in self.widgets:
                    ctx.set_source_surface(i.drawer.last_surface, i.offsetx, i.offsety)
                    ctx.paint()

            # Then we copy the desired area to our destination surface
            dest = cairocffi.ImageSurface(cairocffi.FORMAT_ARGB32, width, height)
            with cairocffi.Context(dest) as ctx:
                ctx.set_source_surface(bar_copy, x=x, y=y)
                ctx.paint()

            dest.write_to_png(target)

    # Get the widget and config
    config = getattr(request, "param", dict())
    wdgt = ScreenshotWidget(**{**widget_config, **config})
    name = wdgt.name

    # Create a function to generate filename
    def filename(caption=None):
        return target(name, caption if caption else config)

    # define bars
    position = "left" if vertical else "top"
    bar1 = {position: ScreenshotBar([wdgt], 32)}
    bar2 = {position: ScreenshotBar([], 32)}

    # Add the widget to our config
    minimal_conf_noscreen.groups = [Group(i) for i in "123456789"]
    minimal_conf_noscreen.fake_screens = [
        Screen(**bar1, x=0, y=0, width=300, height=300),
        Screen(**bar2, x=0, y=300, width=300, height=300),
    ]
    minimal_conf_noscreen.enable_sni = sni
    minimal_conf_noscreen.enable_global_menu = gm

    if sni or gm:

        def start_dbus(qtile):
            dbus_window = DBusPopup(
                qtile=qtile,
                width=1,
                height=1,
                x=-1,
                y=-1,
                # controls=[PopupText(text="Started", x=0, y=0, width=1, height=0.2, name="textbox")],
            )

            dbus_window.show()

        minimal_conf_noscreen.keys = [Key(["mod4"], "m", lazy.function(start_dbus))]

        request.getfixturevalue("dbus")  # Start dbus

    manager_nospawn.start(minimal_conf_noscreen)

    if sni or gm:
        manager_nospawn.c.simulate_keypress(["mod4"], "m")

        @Retry(ignore_exceptions=(AssertionError,))
        def wait_for_popup():
            assert len(manager_nospawn.c.internal_windows()) == 3

        wait_for_popup()

    # Add some convenience attributes for taking screenshots
    manager_nospawn.target = filename
    ss_widget = manager_nospawn.c.widget[name]
    manager_nospawn.take_screenshot = lambda f=filename, caption=None: ss_widget.take_screenshot(
        f(caption)
    )
    manager_nospawn.take_popup_screenshot = (
        lambda f=filename, caption=None: ss_widget.take_screenshot_with_popup(f(caption))
    )
    manager_nospawn.take_extended_popup_screenshot = (
        lambda f=filename, caption=None: ss_widget.take_extended_popup_screenshot(f(caption))
    )

    yield manager_nospawn


def widget_config(params):
    return pytest.mark.parametrize("screenshot_manager", params, indirect=True)
