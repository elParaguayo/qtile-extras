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
import textwrap

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import pytest
from libqtile.lazy import lazy

from qtile_extras.popup.toolkit import PopupGridLayout, PopupText


class ToolkitConfig(libqtile.confreader.Config):
    def show_menu(qtile):  # noqa: N805
        controls = []
        for x in range(3):
            for y in range(3):
                label = f"{y + (x * 3) + 1}"
                controls.append(
                    PopupText(
                        label,
                        col=y,
                        row=x,
                        mouse_callbacks={"Button1": lazy.widget["textbox"].update(label)},
                    )
                )

        menu = PopupGridLayout(qtile, rows=3, cols=3, close_on_click=False, controls=controls)

        menu.show()

        qtile.popupmenu = menu

    auto_fullscreen = True
    keys = [libqtile.config.Key(["mod4"], "m", lazy.function(show_menu))]
    mouse = []
    groups = [
        libqtile.config.Group("a"),
    ]
    layouts = [libqtile.layout.Max()]
    floating_layout = libqtile.resources.default_config.floating_layout
    screens = [
        libqtile.config.Screen(
            top=libqtile.bar.Bar(
                [libqtile.widget.TextBox("BLANK")],
                50,
            ),
        )
    ]


toolkit_config = pytest.mark.parametrize("manager", [ToolkitConfig], indirect=True)


@toolkit_config
def test_menu_navigation(manager):
    def press_key(keycode):
        manager.c.eval(f"self.popupmenu.fake_key_press('{keycode}')")

    assert manager.c.widget["textbox"].get() == "BLANK"

    manager.c.simulate_keypress(["mod4"], "m")

    # Use tab to loop over all 9 controls
    for i in range(9):
        press_key("space")
        assert manager.c.widget["textbox"].get() == f"{i + 1}"
        press_key("Tab")

    # We're back at square 1
    press_key("space")
    assert manager.c.widget["textbox"].get() == "1"

    # Try arrow keys
    press_key("Right")
    press_key("Down")
    press_key("space")
    assert manager.c.widget["textbox"].get() == "5"

    press_key("Right")
    press_key("Down")
    press_key("space")
    assert manager.c.widget["textbox"].get() == "9"

    press_key("Up")
    press_key("Up")
    press_key("space")
    assert manager.c.widget["textbox"].get() == "3"

    press_key("Left")
    press_key("Left")
    press_key("space")
    assert manager.c.widget["textbox"].get() == "1"


def test_absolute_layout(manager):
    layout = textwrap.dedent(
        """
        from qtile_extras.popup.toolkit import PopupAbsoluteLayout, PopupText
        self.popup = PopupAbsoluteLayout(
            self,
            controls=[
                PopupText(
                    "Test",
                    pos_x=10,
                    pos_y=10,
                    width=100,
                    height=100
                )
            ]
        )

        self.popup.show()
    """
    )
    manager.c.eval(layout)
    _, info = manager.c.eval("self.popup.info()")
    info = eval(info)
    control = info["controls"][0]
    assert control["x"] == 10
    assert control["y"] == 10
    assert control["width"] == 100
    assert control["height"] == 100


def test_relative_layout(manager):
    layout = textwrap.dedent(
        """
        from qtile_extras.popup.toolkit import PopupRelativeLayout, PopupText
        self.popup = PopupRelativeLayout(
            self,
            controls=[
                PopupText(
                    "Test",
                    pos_x=0.1,
                    pos_y=0.2,
                    width=0.5,
                    height=0.6
                )
            ],
            margin=0
        )

        self.popup.show()
    """
    )
    manager.c.eval(layout)
    _, info = manager.c.eval("self.popup.info()")
    info = eval(info)
    control = info["controls"][0]
    assert control["x"] == 20
    assert control["y"] == 40
    assert control["width"] == 100
    assert control["height"] == 120


def test_grid_layout(manager):
    layout = textwrap.dedent(
        """
        from qtile_extras.popup.toolkit import PopupGridLayout, PopupText
        self.popup = PopupGridLayout(
            self,
            controls=[
                PopupText(
                    "Test",
                    row=0,
                    col=1,
                    row_span=2,
                    col_span=3,
                )
            ],
            margin=0,
            rows=4,
            cols=4
        )

        self.popup.show()
    """
    )
    manager.c.eval(layout)
    _, info = manager.c.eval("self.popup.info()")
    info = eval(info)
    control = info["controls"][0]
    assert control["x"] == 50
    assert control["y"] == 0
    assert control["width"] == 150
    assert control["height"] == 100


def test_disable_navigation():
    """Where there are no focusable controls, keyboard navigation is disabled."""
    controls = [
        PopupText(
            text="TEST",
            row=0,
            col=0,
        ),
    ]

    layout = PopupGridLayout(
        None, width=500, height=200, controls=controls, keyboard_navigation=True, initial_focus=0
    )

    assert not layout.keyboard_navigation
    assert layout._focused is None


def test_initial_focus_index_error():
    """Where there are focusable controls but index is too high, default to first control."""
    controls = [
        PopupText(text="TEST", row=0, col=0, mouse_callbacks={"Button1": lambda: None}),
    ]

    layout = PopupGridLayout(
        None, width=500, height=200, controls=controls, keyboard_navigation=True, initial_focus=1
    )

    assert layout._focused == controls[0]
    assert layout.keyboard_navigation


class TwoScreensConfig(libqtile.confreader.Config):
    fake_screens = [
        libqtile.config.Screen(x=0, y=0, width=400, height=600),
        libqtile.config.Screen(x=400, y=0, width=400, height=600),
    ]


@pytest.mark.parametrize("manager", [TwoScreensConfig], indirect=True)
def test_multiple_screens(manager):
    """Check window is positioned correctly on different screens."""
    layout = textwrap.dedent(
        """
        from qtile_extras.popup.toolkit import PopupGridLayout, PopupText
        self.popup = PopupGridLayout(
            self,
            controls=[
                PopupText(
                    "Test",
                    row=0,
                    col=1,
                    row_span=2,
                    col_span=3,
                )
            ],
            margin=0,
            rows=4,
            cols=4
        )
    """
    )
    manager.c.eval(layout)

    # Show popup on screen 0 which is at (0, 0) and has dimensions of (400, 600)
    manager.c.eval("self.popup.show(centered=True)")
    _, info = manager.c.eval("self.popup.info()")
    info = eval(info)
    assert info["width"] == 200
    assert info["height"] == 200
    assert info["x"] == (400 - 200) / 2
    assert info["y"] == (600 - 200) / 2

    # Show popup on screen 1 which is at (400, 0) and has dimensions of (400, 600)
    # Popup should therefore be adjusted for x offset
    manager.c.eval("self.popup.hide()")
    manager.c.to_screen(1)
    manager.c.eval("self.popup.show(centered=True)")
    _, info = manager.c.eval("self.popup.info()")
    info = eval(info)
    assert info["width"] == 200
    assert info["height"] == 200
    assert info["x"] == (400 - 200) / 2 + 400
    assert info["y"] == (600 - 200) / 2

    # Show popup on screen 0 which is at (0, 0) and has dimensions of (400, 600)
    # Not centered so popup should be at (0, 0)
    manager.c.eval("self.popup.hide()")
    manager.c.to_screen(0)
    manager.c.eval("self.popup.show()")
    _, info = manager.c.eval("self.popup.info()")
    info = eval(info)
    assert info["width"] == 200
    assert info["height"] == 200
    assert info["x"] == 0
    assert info["y"] == 0

    # Show popup on screen 1 which is at (400, 0) and has dimensions of (400, 600)
    # Not centered so popup should be at (400, 0)
    manager.c.eval("self.popup.hide()")
    manager.c.to_screen(1)
    manager.c.eval("self.popup.show()")
    _, info = manager.c.eval("self.popup.info()")
    info = eval(info)
    assert info["width"] == 200
    assert info["height"] == 200
    assert info["x"] == 400
    assert info["y"] == 0

    # Show popup on screen 1 while screen 0 is focussed
    manager.c.eval("self.popup.hide()")
    manager.c.to_screen(0)
    manager.c.eval("self.popup.show(x=500, y=200)")
    _, info = manager.c.eval("self.popup.info()")
    info = eval(info)
    assert info["width"] == 200
    assert info["height"] == 200
    assert info["x"] == 500
    assert info["y"] == 200


def test_popup_widgets(manager):
    layout = textwrap.dedent(
        """
        from libqtile import widget
        from qtile_extras.popup.toolkit import PopupRelativeLayout, PopupWidget
        self.popup = PopupRelativeLayout(
            self,
            controls=[
                PopupWidget(
                    widget=widget.TextBox("TEST"),
                    pos_x=0.1,
                    pos_y=0.1,
                    width=0.4,
                    height=0.4
                ),
                PopupWidget(
                    widget=widget.CPUGraph(),
                    pos_x=0.5,
                    pos_y=0.1,
                    width=0.4,
                    height=0.4
                ),
                PopupWidget(
                    widget=widget.Clock(),
                    pos_x=0.1,
                    pos_y=0.5,
                    width=0.8,
                    height=0.4
                ),
            ],
            margin=0
        )

        self.popup.show()
    """
    )
    manager.c.eval(layout)
    _, info = manager.c.eval("self.popup.info()")
    info = eval(info)

    for control in info["controls"]:
        # Check that widget is created (provide its info)
        assert control["widget"]

        # Check that widget fits the control
        for key in ["height", "width"]:
            assert control[key] == control["widget"][key]

        assert control["width"] == control["widget"]["length"]


def test_popup_widgets_vertical(manager):
    layout = textwrap.dedent(
        """
        from libqtile import widget
        from qtile_extras.popup.toolkit import PopupRelativeLayout, PopupWidget
        self.popup = PopupRelativeLayout(
            self,
            controls=[
                PopupWidget(
                    widget=widget.TextBox("TEST ONE"),
                    pos_x=0.1,
                    pos_y=0.1,
                    width=0.4,
                    height=0.8,
                    horizontal=False
                ),
                PopupWidget(
                    widget=widget.TextBox("TEST TWO"),
                    pos_x=0.5,
                    pos_y=0.1,
                    width=0.4,
                    height=0.8,
                    horizontal=False,
                    vertical_left=False
                ),
            ],
            margin=0
        )

        self.popup.show()
    """
    )
    manager.c.eval(layout)
    _, info = manager.c.eval("self.popup.info()")
    info = eval(info)

    for control in info["controls"]:
        # Check that widget is created (provide its info)
        assert control["widget"]

        # Check that widget fits the control
        for key in ["height", "width"]:
            assert control[key] == control["widget"][key]

        assert control["height"] == control["widget"]["length"]
