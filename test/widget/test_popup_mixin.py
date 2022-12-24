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
import libqtile
import pytest
from libqtile import widget

from qtile_extras.popup.toolkit import PopupAbsoluteLayout, PopupText
from qtile_extras.widget.mixins import ExtendedPopupMixin
from test.helpers import Retry


@Retry(ignore_exceptions=(AssertionError,))
def assert_window_count(manager, number):
    assert len(manager.c.internal_windows()) == number


class ModdedWidget(widget.TextBox, ExtendedPopupMixin):
    def __init__(self, text, **config):
        widget.TextBox.__init__(self, text, **config)
        ExtendedPopupMixin.__init__(self)
        self.add_defaults(ExtendedPopupMixin.defaults)

    def _update_popup(self):
        self.extended_popup.update_controls(textbox1="Text set ok")

    def info(self):
        return {"text": self.extended_popup.controls[0].text if self.has_popup else ""}


class PopupConfig(libqtile.confreader.Config):
    auto_fullscreen = True
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
                    ModdedWidget(
                        "",
                        popup_layout=PopupAbsoluteLayout(controls=[PopupText(name="textbox1")]),
                        popup_hide_timeout=1,
                    )
                ],
                50,
            ),
        )
    ]


@pytest.mark.parametrize("manager", [PopupConfig], indirect=True)
def test_popup_mixin(manager, backend_name):
    number = len(manager.c.internal_windows())
    widget = manager.c.widget["moddedwidget"]
    assert not widget.info()["text"]

    widget.eval("self.update_or_show_popup()")
    widget.eval("self.update_or_show_popup()")

    assert_window_count(manager, number + 1)
    assert widget.info()["text"] == "Text set ok"

    if backend_name == "x11":
        pytest.xfail("X11 fails last check.")

    # Popup should close automatically
    assert_window_count(manager, number)


def test_popup_missing_method():
    widget = ModdedWidget("")
    widget._update_popup = ExtendedPopupMixin._update_popup
    with pytest.raises(NotImplementedError):
        widget._update_popup(widget)
