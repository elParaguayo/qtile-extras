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
from importlib import reload

import pytest
from libqtile.bar import Bar
from libqtile.config import Screen
from libqtile.confreader import Config

import qtile_extras
from test.helpers import Retry


@pytest.fixture(scope="function")
def visualiser(monkeypatch):
    monkeypatch.setattr("qtile_extras.widget.visualiser.os.kill", lambda *args: True)
    reload(qtile_extras)

    class GlobalMenuConfig(Config):
        screens = [
            Screen(
                top=Bar(
                    [qtile_extras.widget.Visualiser(cava_path="/not/installed")],
                    50,
                ),
            )
        ]

    yield GlobalMenuConfig


@Retry(ignore_exceptions=(AssertionError,))
def assert_length(manager, width):
    assert manager.c.widget["visualiser"].info()["width"] == width

    _, out = manager.c.widget["visualiser"].eval("self._toggling")
    assert out == "False"


def test_visualiser(manager_nospawn, visualiser):
    manager_nospawn.start(visualiser)
    assert_length(manager_nospawn, 100)

    manager_nospawn.c.widget["visualiser"].stop()
    assert_length(manager_nospawn, 0)

    manager_nospawn.c.widget["visualiser"].start()
    assert_length(manager_nospawn, 100)

    manager_nospawn.c.widget["visualiser"].toggle()
    assert_length(manager_nospawn, 0)

    manager_nospawn.c.widget["visualiser"].toggle()
    assert_length(manager_nospawn, 100)
