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
import logging
import tempfile
from pathlib import Path

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import pytest
from libqtile.log_utils import init_log
from libqtile.widget import QuickExit

import qtile_extras.widget
from test.helpers import Retry  # noqa: I001

WINDOW = Path(__file__).parent.parent / "scripts" / "exit.py"


@Retry(ignore_exceptions=(AssertionError, FileNotFoundError))
def read_file(fname):
    with open(fname, "r") as f:
        text = f.read()
        assert text == "CLOSED"


@pytest.fixture(scope="function")
def temp_output():
    with tempfile.TemporaryDirectory() as tempdir:
        yield f"python {WINDOW} {tempdir}/exit.log"


@pytest.fixture(scope="function")
def exit_manager(manager_nospawn, monkeypatch, temp_output):
    """
    Fixture provides a manager instance with ScriptExit in the bar.
    """

    def no_op(self, *args, **kwargs):
        def _():
            self.is_counting = False

        return _

    def new_config(self, qtile, bar):
        QuickExit._configure(self, qtile, bar)
        self.qtile.stop = no_op(self)

    monkeypatch.setattr("qtile_extras.widget.ScriptExit._configure", new_config)

    class ExitConfig(libqtile.confreader.Config):
        """Config for the test."""

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
                        qtile_extras.widget.ScriptExit(
                            timer_interval=0.05, exit_script=temp_output
                        )
                    ],
                    50,
                ),
            )
        ]

    manager_nospawn.start(ExitConfig)
    yield manager_nospawn


def test_exit(exit_manager, temp_output):
    """Check script activated."""
    assert not exit_manager.c.windows()
    exit_manager.c.bar["top"].fake_button_press(0, "top", 0, 0, 1)
    fname = temp_output.split(" ")[-1]
    read_file(fname)


def test_error_handling(caplog, temp_output):
    """Check invalid script."""

    def no_op(*args, **kwargs):
        pass

    init_log(logging.INFO)

    # Adding an extra arg to the script will cause it to raise an error when run
    invalid_script = f"{temp_output} extra_arg"

    widget = qtile_extras.widget.ScriptExit(exit_script=invalid_script, countdown_start=1)

    # Disable some things we don't need here
    widget.draw = no_op
    widget.future = None
    widget.timeout_add = no_op
    QuickExit.update = no_op

    # Start the timer
    widget.trigger()

    # Check the output
    assert caplog.record_tuples == [
        ("libqtile", logging.ERROR, f"Exit script ({invalid_script}) failed to run.")
    ]
