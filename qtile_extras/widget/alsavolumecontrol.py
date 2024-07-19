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
from __future__ import annotations

import re
import shutil
import subprocess

from libqtile.command.base import expose_command
from libqtile.log_utils import logger

from qtile_extras.widget.base import _Volume

RE_VOL = re.compile(r"Playback\s[0-9]+\s\[([0-9]+)%\].*\[(on|off)\]")


class ALSAWidget(_Volume):
    __doc__ = (
        """
    The widget is very simple and, so far, just allows controls for
    volume up, down and mute.

    Volume control is handled by running the appropriate amixer command.
    The widget is updated instantly when volume is changed via this
    code, but will also update on an interval (i.e. it will reflect
    changes to volume made by other programs).

    """
        + _Volume._instructions
    )

    _screenshots = [
        ("volumecontrol-icon.gif", "'icon' mode"),
        ("volumecontrol-bar.gif", "'bar' mode"),
        ("volumecontrol-both.gif", "'both' mode"),
    ]

    def _run(self, cmd):
        if not shutil.which("amixer"):
            logger.warning("'amixer' is not installed. Unable to set volume.")
            return

        # Run the amixer command and use regex to capture volume line
        proc = subprocess.run(cmd.split(), capture_output=True)
        matched = RE_VOL.search(proc.stdout.decode())

        # If we find a match, extract volume and mute status
        if matched:
            self.volume = int(matched.groups()[0])
            self.muted = matched.groups()[1] == "off"

        # If volume or mute status has changed
        # then we need to trigger callback
        if (self.volume, self.muted) != self._previous_state:
            if not self.first_run:
                self.status_change(self.volume, self.muted)
            else:
                self.first_run = False

            # Record old values
            self._previous_state = (self.volume, self.muted)

    def get_volume(self):
        cmd = "amixer get {}".format(self.device)
        self._run(cmd)

    @expose_command()
    def volume_up(self, *args, **kwargs):
        """Increase volume"""
        cmd = "amixer set {} {}%+".format(self.device, self.step)
        self._run(cmd)

    @expose_command()
    def volume_down(self, *args, **kwargs):
        """Decrease volume"""
        cmd = "amixer set {} {}%-".format(self.device, self.step)
        self._run(cmd)

    @expose_command()
    def toggle_mute(self, *args, **kwargs):
        """Mute audio output"""
        cmd = "amixer set {} toggle".format(self.device)
        self._run(cmd)
