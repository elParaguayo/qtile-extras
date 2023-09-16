# -*- coding: utf-8 -*-
# Copyright (c) 2023 elParaguayo
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
from libqtile.command.base import expose_command

from qtile_extras.widget.base import _Volume
from qtile_extras.widget.pulse_volume import PulseVolume


class PulseVolumeExtra(_Volume, PulseVolume):
    """
    Volume widget for systems using PulseAudio.

    The appearance is identical to ``ALSAWidget`` but this widget
    uses qtile's ``PulseVolume`` widget to set/retrieve volume levels.
    As a result, you will need the `pulsectl_asyncio <https://pypi.org/project/pulsectl-asyncio/>`__
    library to use this widget.

    Finally, the widget allows users to select the output sink by middle clicking on the widget or calling
    the ``select_sink()`` command.
    """

    _screenshots = [
        ("volumecontrol-icon.gif", "'icon' mode"),
        ("volumecontrol-bar.gif", "'bar' mode"),
        ("volumecontrol-both.gif", "'both' mode"),
    ]

    def __init__(self, **config):
        # There is some ugly hackery here...
        # The issue is that both __init__ methods reset the _variable_defaults dictionary
        # so we need to copy the dictionary after the first init and then update it after
        # the second!
        PulseVolume.__init__(self, **config)
        defaults = self._variable_defaults.copy()
        _Volume.__init__(self, **config)
        self._variable_defaults = {**defaults, **self._variable_defaults}

        # We need a flag to ensure we only try to connect to the Pulse server once
        self._connection_requested = False

    def _configure(self, qtile, bar):
        PulseVolume._configure(self, qtile, bar)
        _Volume._configure(self, qtile, bar)

    async def _config_async(self):
        if not self._connection_requested:
            self._connection_requested = True
            await PulseVolume._config_async(self)

    def update(self):
        """Modified version of PulseVolume.update to set variables."""
        length = self.length

        if not self.pulse.connected or not self.default_sink:
            vol = -1
            mute = False
        else:
            vol = self.get_volume()
            mute = self.default_sink.mute
        if vol != self.volume or mute != self.muted:
            self.volume = vol
            self.muted = mute
            self.hidden = False
            if length == self.length:
                self.draw()
            else:
                self.bar.draw()

    @expose_command()
    def volume_up(self, value=None):
        """Increase volume."""
        self.increase_vol(value)

    @expose_command()
    def volume_down(self, value=None):
        """Decrease volume."""
        self.decrease_vol(value)

    get_volume = PulseVolume.get_volume
