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
import importlib
import traceback

from libqtile.log_utils import logger
from libqtile.widget import widgets as qtile_widgets
from libqtile.widget.import_error import make_error

from qtile_extras.widget.decorations import inject_decorations

widgets = {
    "ALSAWidget": "alsavolumecontrol",
    "AnalogueClock": "analogueclock",
    "AnimatedImage": "animatedimage",
    "Bluetooth": "bluetooth",
    "BrightnessControl": "brightnesscontrol",
    "ContinuousPoll": "continuous_poll",
    "CurrentLayoutIcon": "currentlayout",
    "CPUGraph": "graph",
    "GithubNotifications": "githubnotifications",
    "GlobalMenu": "globalmenu",
    "GroupBox2": "groupbox2",
    "HDDGraph": "graph",
    "HDDBusyGraph": "graph",
    "Image": "image",
    "IWD": "iwd",
    "LiveFootballScores": "livefootballscores",
    "MemoryGraph": "graph",
    "Mpris2": "mpris2widget",
    "NetGraph": "graph",
    "QTEMirror": "mirror",
    "PulseVolume": "pulse_volume",
    "PulseVolumeExtra": "pulse_extra",
    "ScriptExit": "scriptexit",
    "SnapCast": "snapcast",
    "StatusNotifier": "statusnotifier",
    "StravaWidget": "strava",
    "SwapGraph": "graph",
    "Syncthing": "syncthing",
    "Systray": "systray",
    "TVHWidget": "tvheadend",
    "UnitStatus": "unitstatus",
    "UPowerWidget": "upower",
    "Visualiser": "visualiser",
    "Visualizer": "visualiser",
    "WiFiIcon": "network",
    "WordClock": "wordclock",
}


def modify(classdef, *args, initialise=True, **config):
    """
    Function to add additional code needed by widgets to use mods
    provided by qtile-extras.

    The function can also be used to inject code into user-defined
    widgets e.g.

        modify(CustomWidget, **config)

    """

    # Inject the decorations code into the widget
    inject_decorations(classdef)

    if initialise:
        return classdef(*args, **config)

    return classdef


# import_class and lazify_imports adapted from qtile/qtile


def import_class(module_path, class_name, fallback=None):
    """Import a class safely

    Try to import the class module, and if it fails because of an ImporError
    it logs on WARNING, and logs the traceback on DEBUG level
    """
    try:
        module = importlib.import_module(module_path)
        classdef = getattr(module, class_name)

        classdef = modify(classdef, initialise=False)

        return classdef

    except ImportError as error:
        logger.warning(  # noqa: G200
            "Unmet dependencies for '%s.%s': %s", module_path, class_name, error
        )
        if fallback:
            logger.debug("%s", traceback.format_exc())  # noqa: G200
            return fallback(module_path, class_name)
        raise


def lazify_imports(registry, fallback=None):
    """Leverage PEP 562 to make imports lazy in an __init__.py

    The registry must be a dictionary with the items to import as keys and the
    modules they belong to as a value.
    """
    __all__ = tuple(registry.keys())

    def __dir__():
        return __all__

    def __getattr__(name):
        if name not in registry:
            raise AttributeError

        if name in widgets:
            package = "qtile_extras.widget"
        else:
            package = "libqtile.widget"

        module_path = f"{package}.{registry[name]}"

        return import_class(module_path, name, fallback=fallback)

    return __all__, __dir__, __getattr__


# We need all widgets, not just the qtile_extras ones so we can inject code into
# everything and have all widgets available in qtile_extras.widget
all_widgets = {**widgets, **qtile_widgets}

__all__, __dir__, __getattr__ = lazify_imports(all_widgets, fallback=make_error)
