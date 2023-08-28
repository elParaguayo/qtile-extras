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
from pathlib import Path

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import pytest
from libqtile import confreader
from libqtile.log_utils import init_log

import qtile_extras.widget.alsavolumecontrol
from test.helpers import Retry  # noqa: I001

ICON_FOLDER = (Path(__file__).parent / ".." / "resources" / "icons").as_posix()


@Retry(ignore_exceptions=(AssertionError,))
def wait_for_hide(widget):
    assert widget.info()["width"] == 0


class FakeProcess:
    vol = 50
    mute = False
    fmt = "Playback 1234 [{vol}%] [{mute}]"

    @classmethod
    def do_output(cls):
        class Output:
            @property
            def stdout(self):
                return cls.fmt.format(vol=cls.vol, mute="on" if not cls.mute else "off").encode()

        return Output()

    @classmethod
    def set_vol(cls, cmd):
        # get last item in command list and remove trailing chars (% + or -)
        step = int(cmd[-1][:-2])
        if cmd[-1].endswith("-"):
            step *= -1

        cls.vol += step

        # Keep to 0-100 range
        cls.vol = min(100, max(0, cls.vol))

        return cls.do_output()

    @classmethod
    def run(cls, cmd, *args, **kwargs):
        if "get" in cmd:
            return cls.do_output()

        elif "set" in cmd:
            if "toggle" in cmd:
                cls.mute = not cls.mute
                return cls.do_output()

            else:
                return cls.set_vol(cmd)


# We need to pretend alsamix is installed
def which_amixer(_):
    return True


@pytest.fixture(scope="function")
def alsa_manager(manager_nospawn, monkeypatch, request):
    """
    Fixture provides a manager instance with ScriptExit in the bar.
    """
    FakeProcess.vol = 50
    monkeypatch.setattr("qtile_extras.widget.alsavolumecontrol.subprocess", FakeProcess)
    monkeypatch.setattr("qtile_extras.widget.alsavolumecontrol.shutil.which", which_amixer)

    class ALSAConfig(libqtile.confreader.Config):
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
                        qtile_extras.widget.alsavolumecontrol.ALSAWidget(
                            hide_interval=0.5, **getattr(request, "param", dict())
                        )
                    ],
                    50,
                ),
            )
        ]

    manager_nospawn.start(ALSAConfig)
    yield manager_nospawn


def test_alsawidget_defaults(alsa_manager):
    """Check widget reads and parses volume"""
    widget = alsa_manager.c.widget["alsawidget"]

    info = widget.info()

    # Widget does not immediately load volume
    assert info["volume"] == -1
    assert not info["muted"]

    # # widget is visible at start
    # assert info["width"] == 75

    # # Wait until it hides
    # wait_for_hide(widget)

    # Method that's called on an interval
    widget.eval("self.refresh()")
    assert widget.info()["volume"] == 50


def test_controls(alsa_manager):
    """Check widget reads and parses volume"""
    widget = alsa_manager.c.widget["alsawidget"]

    widget.volume_up()
    assert widget.info()["volume"] == 55

    for _ in range(10):
        widget.volume_up()

    widget.toggle_mute()
    assert widget.info()["muted"]

    widget.toggle_mute()
    assert not widget.info()["muted"]

    assert widget.info()["volume"] == 100
    assert widget.info()["width"] == 75
    wait_for_hide(widget)

    for _ in range(20):
        widget.volume_down()

    assert widget.info()["volume"] == 0
    assert widget.info()["width"] == 75
    wait_for_hide(widget)


@pytest.mark.parametrize("alsa_manager", [{"step": 10}], indirect=True)
def test_step(alsa_manager):
    """Check widget reads and parses volume"""
    widget = alsa_manager.c.widget["alsawidget"]
    widget.volume_up()

    # Volume should be 60 (default 50 + step 10)
    assert widget.info()["volume"] == 60


@pytest.mark.parametrize(
    "alsa_manager", [{"theme_path": ICON_FOLDER, "mode": "icon", "padding": 0}], indirect=True
)
def test_icons(alsa_manager):
    """Check widget reads and parses volume"""
    widget = alsa_manager.c.widget["alsawidget"]

    # We need to set levels to display each icon
    widget.toggle_mute()
    widget.toggle_mute()

    for _ in range(4):
        widget.volume_down()

    assert widget.info()["volume"] == 30

    for _ in range(13):
        widget.volume_up()

    assert widget.info()["volume"] == 95

    widget.volume_up()
    assert widget.info()["volume"] == 100


def test_no_amixer(monkeypatch, caplog):
    def which(_):
        return None

    init_log(logging.INFO)
    monkeypatch.setattr("qtile_extras.widget.alsavolumecontrol.shutil.which", which)
    widget = qtile_extras.widget.alsavolumecontrol.ALSAWidget()
    widget.get_volume()
    assert "'amixer' is not installed." in caplog.text


def test_no_theme_path(monkeypatch):
    """Widget should raise config error if no theme_path for icons."""

    def no_op(*args, **kwargs):
        pass

    monkeypatch.setattr("qtile_extras.widget.base.base._Widget._configure", no_op)
    monkeypatch.setattr("qtile_extras.widget.alsavolumecontrol.ALSAWidget.get_volume", no_op)
    widget = qtile_extras.widget.alsavolumecontrol.ALSAWidget(mode="icon")

    # No idea why decorations code is being injected in the tests.
    widget._configure = widget.old_configure
    with pytest.raises(confreader.ConfigError):
        widget._configure(None, None)


@pytest.mark.parametrize(
    "alsa_manager", [{"theme_path": "/no/path", "mode": "icon"}], indirect=True
)
@pytest.mark.flaky(reruns=5)
def test_no_icons(alsa_manager, logger):
    """Icons are loaded in background and will log a failure if not found."""

    @Retry(ignore_exceptions=(AssertionError,))
    def wait_for_failure():
        assert any(
            "Could not find volume icons at /no/path." in r.msg
            for r in logger.get_records("setup")
        )

    wait_for_failure()
