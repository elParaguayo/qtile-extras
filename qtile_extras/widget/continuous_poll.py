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
import asyncio
import os
import signal

from libqtile.command.base import expose_command
from libqtile.log_utils import logger
from libqtile.widget.base import _TextBox


class ContinuousPoll(_TextBox):
    """
    A widget for displaying the continuous output from a process.

    Every time a new line is output, the widget will update.

    The widget takes an optional ``parse_line`` parameter which should
    be a callable object accepting a ``line`` object. The object should
    return a string to be displayed in the widget. NB the line received
    by the object is a raw bytestring so you may want to ``decode()`` it
    before manipulating it. The default behaviour (i.e. with no function)
    is to run ``.decode().strip()`` on the text to remove any trailing
    new line character.
    """

    defaults = [
        ("cmd", None, "Command to execute."),
        ("parse_line", None, "Function to parse output of line. See docs for more."),
    ]

    def __init__(self, **config):
        _TextBox.__init__(self, **config)
        self.add_defaults(ContinuousPoll.defaults)
        self._process = None
        self._finalized = False

    async def _config_async(self):
        await self.run()

    async def run(self):
        if not self.cmd:
            return

        self._process = await asyncio.create_subprocess_shell(
            self.cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            preexec_fn=os.setsid,
        )

        while not self._finalized:
            out = await self._process.stdout.readline()
            # process has exited so clear text and exit loop
            if not out:
                self.update("")
                self._process = None
                break

            if self.parse_line:
                output = self.parse_line(out)
            else:
                output = out.decode().strip()

            self.qtile.call_soon_threadsafe(self.update, output)

    def _stop(self, kill=False):
        # Make sure we kill any processes in the same group
        os.killpg(os.getpgid(self._process.pid), signal.SIGKILL if kill else signal.SIGTERM)

        self.update("")

    @expose_command()
    def stop_process(self, kill=False):
        """Stop the running process."""
        if self._process is None:
            return

        self._stop(kill=kill)

    @expose_command()
    def run_process(self, command=None):
        """Re-run the command or provide a new command to run."""
        if self._process is not None:
            logger.warning("Cannot start process while another is running.")
            return

        if command is not None:
            self.cmd = command

        asyncio.create_task(self.run())

    def finalize(self):
        self._finalized = True
        self.stop_process()
        _TextBox.finalize(self)
