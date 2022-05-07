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

import libqtile.bar
import libqtile.config
import libqtile.confreader
import libqtile.layout
import pytest
from dbus_next import Variant
from dbus_next.constants import BusType
from libqtile.log_utils import init_log
from libqtile.widget import base

import qtile_extras.widget


@pytest.fixture(scope="function")
def unit_manager(manager_nospawn):
    """
    Fixture provides a manager instance with ScriptExit in the bar.
    """

    class UnitConfig(libqtile.confreader.Config):
        """
        Config for the test.

        The default unit used by the widget, NetworkManager.service, is
        available on CI so, to ensure tests can be run consistently on
        local and remote builds, we use a unit that definitely doesn't
        exist.
        """

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
                    [qtile_extras.widget.UnitStatus(unitname="QtileTest.service", label="Qtile")],
                    50,
                ),
            )
        ]

    manager_nospawn.start(UnitConfig)
    yield manager_nospawn


def test_unit_status_defaults(unit_manager):
    """If this runs with no errors then it's all good!"""
    info = unit_manager.c.widget["unitstatus"].info()
    assert info["unit"] == "QtileTest.service"
    assert info["bus"] == "system"
    assert info["text"] == "Qtile"
    assert info["state"] == "not-found"


def test_unit_status_invalid_bus(caplog):
    """Check for a valid bus"""
    init_log(logging.INFO)

    widget = qtile_extras.widget.UnitStatus(bus_name="test_bus")
    assert caplog.record_tuples == [
        ("libqtile", logging.WARNING, "Unknown bus name. Defaulting to system bus.")
    ]

    assert widget.bus_type == BusType.SYSTEM


def test_unit_status_session_bus(caplog):
    """Check session bus is set correctly"""
    widget = qtile_extras.widget.UnitStatus(bus_name="session")
    assert widget.bus_type == BusType.SESSION


def test_unit_status_check_properties():
    """Check handling of changed properties."""

    def no_op():
        pass

    widget = qtile_extras.widget.UnitStatus()
    widget.draw = no_op

    assert widget.state == "not-found"

    widget._changed(None, {"OtherProperty": Variant("s", "active")}, None)
    assert widget.state == "not-found"

    widget._changed(None, {"ActiveState": Variant("s", "active")}, None)
    assert widget.state == "active"


def test_unit_status_indicator_size():
    """Check indicator size is limited."""

    def no_op(*args, **kwargs):
        pass

    class Bar:
        height = 50

    class Drawer:
        def textlayout(self, *args, **kwargs):
            class Layout:
                width = 0

            return Layout()

        def clear(self, *args, **kwargs):
            pass

        def draw(self, *args, **kwargs):
            pass

    widget = qtile_extras.widget.UnitStatus(indicator_size=None)
    base._Widget._configure = no_op
    widget.bar = Bar()
    widget.draw = no_op
    widget.text_width = no_op
    widget.drawer = Drawer()
    widget._configure(None, None)

    # Indicator size is bar height (50) - 2 * margin (3) = 44
    assert widget.bar.height == 50
    assert widget.margin == 3
    assert widget.indicator_size == 44
