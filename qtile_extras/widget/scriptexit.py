# Based on original "QuickExit" widget, modified by elParaguayo 2020
#
# Copyright (c) 2019, Shunsuke Mie
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
import os
import shlex
import subprocess

from libqtile.log_utils import logger
from libqtile.widget.quick_exit import QuickExit


class ScriptExit(QuickExit):
    """
    An updated version of Qtile's QuickExit widget.

    Takes an additional argument ``exit_script`` which will
    be run before qtile exits.
    """

    defaults = [
        ("exit_script", "", "Script to run on exit."),
    ]

    def __init__(self, **config):
        QuickExit.__init__(self, **config)
        self.add_defaults(ScriptExit.defaults)
        self.exit_script = os.path.expanduser(self.exit_script)
        self.exit_script = shlex.split(self.exit_script)

    def update(self):
        # The actual countdown is decremented in QuickExit.update
        # so we just check if it's going to be 0 here.
        if self.countdown - 1 == 0 and self.exit_script:
            try:
                subprocess.run(self.exit_script, check=True)
            except subprocess.CalledProcessError:
                raw = " ".join(self.exit_script)
                logger.error("Exit script (%s) failed to run.", raw)

        QuickExit.update(self)
