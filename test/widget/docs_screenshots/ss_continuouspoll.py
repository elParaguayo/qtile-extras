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
from functools import partial

import pytest

from qtile_extras.widget.continuous_poll import ContinuousPoll
from test.helpers import Retry
from test.widget.docs_screenshots.conftest import widget_config
from test.widget.test_continuous_poll import COMMAND


def strip_line_prefix(line):
    text = line.decode()
    return text.replace("Line: ", "")


@pytest.fixture
def widget():
    return partial(ContinuousPoll, cmd=COMMAND)


@widget_config([{}, {"parse_line": strip_line_prefix}])
def ss_continuouspoll(screenshot_manager):
    def current_line():
        return screenshot_manager.c.widget["continuouspoll"].info()["text"]

    @Retry(ignore_exceptions=(AssertionError,))
    def wait_for_next_line(line):
        assert current_line() != line

    wait_for_next_line("")
    screenshot_manager.take_screenshot()

    wait_for_next_line(current_line())
    screenshot_manager.take_screenshot()
