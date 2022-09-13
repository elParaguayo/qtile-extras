# Copyright (c) 2011 Florian Mounier
# Copyright (c) 2011 Anshuman Bhaduri
# Copyright (c) 2012-2014 Tycho Andersen
# Copyright (c) 2013 xarvh
# Copyright (c) 2013 Craig Barnes
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 Adi Sieker
# Copyright (c) 2014 Sebastien Blot
# Copyright (c) 2020 Mikel Ward
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
import sys
from pathlib import Path

import libqtile.bar
import libqtile.config
import libqtile.layout
import pytest
from libqtile.confreader import Config

from qtile_extras import widget
from test.helpers import Retry

SCRIPT = Path(__file__).resolve().parent / ".." / "scripts" / "cpoll.py"
COMMAND = f"{sys.executable} {SCRIPT.resolve()}"


@Retry(ignore_exceptions=(AssertionError,))
def check_line(widget, line):
    assert widget.info()["text"] == line


class CPollConfig(Config):
    auto_fullscreen = True
    groups = [
        libqtile.config.Group("a"),
    ]
    layouts = [
        libqtile.layout.max.Max(),
    ]

    screens = [
        libqtile.config.Screen(
            top=libqtile.bar.Bar(
                [widget.ContinuousPoll(cmd=COMMAND)],
                20,
            ),
        )
    ]


cpoll_config = pytest.mark.parametrize("manager", [CPollConfig], indirect=True)


@cpoll_config()
def test_continuous_poll(manager):
    widget = manager.c.widget["continuouspoll"]

    # Process starts automatically
    check_line(widget, "Line: 1")
    check_line(widget, "Line: 2")

    # Stop it and it should clear the text
    widget.stop_process()
    check_line(widget, "")

    # Restart it
    widget.run_process()
    check_line(widget, "Line: 1")
    check_line(widget, "Line: 2")
