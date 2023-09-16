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
import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import pytest

import qtile_extras.resources.dbusmenu
import qtile_extras.widget
from test.helpers import Retry  # noqa: I001

# Tests using glib to create a window have started to fail so let them
# fail silently for now
pytestmark = pytest.mark.xfail


@Retry(ignore_exceptions=(AssertionError,))
def wait_for_text(manager, hidden=True):
    width = manager.c.widget["globalmenu"].info()["width"]
    if hidden:
        assert width == 0
    else:
        assert width > 0


@Retry(ignore_exceptions=(AssertionError,))
def wait_for_menu(manager, hidden=True):
    windows = len(manager.c.internal_windows())
    if hidden:
        assert windows == 1
    else:
        assert windows == 2


class GlobalMenuConfig(libqtile.confreader.Config):
    screens = [
        libqtile.config.Screen(
            top=libqtile.bar.Bar(
                [qtile_extras.widget.GlobalMenu()],
                50,
            ),
        )
    ]


gmconfig = pytest.mark.parametrize("manager", [GlobalMenuConfig], indirect=True)


@gmconfig
@pytest.mark.usefixtures("dbus")
def test_global_menu(manager, backend_name):
    """Check widget displays text, opens menu and triggers events."""
    if backend_name == "wayland":
        pytest.skip("Can't get window ID on Wayland.")

    # Widget has 0 width when no window open
    assert manager.c.widget["globalmenu"].info()["width"] == 0
    assert len(manager.c.windows()) == 0

    # Open a window which export menu so we should see some text
    manager.test_window("GlobalMenu", export_global_menu=True)
    wait_for_text(manager, hidden=False)
    assert len(manager.c.windows()) == 1

    # Open another window with no menu so widget should hide text
    manager.test_window("No Menu")
    wait_for_text(manager, hidden=True)
    assert len(manager.c.windows()) == 2

    # Focus back on window with menu and check text appears
    manager.c.layout.next()
    wait_for_text(manager, hidden=False)

    # Left-click on top menu to open menu window
    manager.c.bar["top"].fake_button_press(0, "top", 10, 0, 1)
    wait_for_menu(manager, hidden=False)

    menu = [x for x in manager.c.internal_windows() if x.get("name", "") == "popupmenu"][0]
    assert menu
    assert menu["controls"]

    # Hacky way to press menu item. Last item is "Quit"
    manager.c.widget["globalmenu"].eval("self.menu.controls[-1].button_press(0, 0, 1)")
    wait_for_text(manager, hidden=True)
    assert len(manager.c.windows()) == 1
