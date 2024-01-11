# Copyright (c) 2022, elParaguayo. All rights reserved.
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
import mmap
import os
import shutil
import signal
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from time import sleep

import cairocffi
from libqtile.command.base import expose_command
from libqtile.confreader import ConfigError
from libqtile.widget import base

SHM = "/tmp/shm.mmap"
LOCK = "/tmp/lock.mmap"

DEFAULT_LENGTH = 100
CAVA_DRAW = Path(__file__).parent.parent / "resources" / "visualiser" / "cava_draw.py"
PYTHON = sys.executable if sys.executable is not None else "python"

CONFIG = """
[general]
bars = {bars}
framerate = {framerate}
[output]
channels = {channels}
method = raw
raw_target = {pipe}
bit_format = 8bit
"""

fps_lock = Lock()


class Visualiser(base._Widget):
    """
    A widget to draw an audio visualiser in your bar.

    The widget requires `cava <https://github.com/karlstav/cava>`__ to be installed.
    This may also be packaged by your distro.

    cava is configured through the widget. Currently, you can set the number of bars and
    the framerate.

    .. warning::

        Rendering the visualiser directly in qtile's bar is almost certainly not an efficient way
        to have a visualiser in your setup. You should therefore be aware that this widget uses
        more processing power than other widgets so you may see CPU usage increase when using this.
        However, if the CPU usage continues to increase the longer you use the widget then that is
        likely to be a bug and should be reported!

    """

    _experimental = True

    orientations = base.ORIENTATION_HORIZONTAL

    defaults = [
        ("framerate", 25, "Cava sampling rate."),
        ("bars", 8, "Number of bars"),
        ("width", DEFAULT_LENGTH, "Widget width"),
        ("cava_path", shutil.which("cava"), "Path to cava. Set if file is not in your PATH."),
        ("spacing", 2, "Space between bars"),
        ("cava_pipe", "/tmp/cava.pipe", "Pipe for cava's output"),
        ("bar_height", 20, "Height of visualiser bars"),
        ("bar_colour", "#ffffff", "Colour of visualiser bars"),
        ("autostart", True, "Start visualiser automatically"),
        ("hide", True, "Hide the visualiser when not active"),
        ("channels", "mono", "Visual channels. 'mono' or 'stereo'."),
        ("invert", False, "When True, bars will draw from the top down"),
    ]

    _screenshots = [("visualiser.gif", "Default config.")]

    def __init__(self, **config):
        self._config_length = config.pop("width", DEFAULT_LENGTH)
        base._Widget.__init__(self, self._config_length, **config)
        self.add_defaults(Visualiser.defaults)
        self._procs_started = False
        self._shm = None
        self._timer = None
        self._draw_count = 0
        self._toggling = False
        self._starting = False
        self._last_time = time.time()

    def _configure(self, qtile, bar):
        if self.cava_path is None:
            raise ConfigError("cava cannot be found.")

        base._Widget._configure(self, qtile, bar)

        if not self.configured:
            config = CONFIG.format(
                bars=self.bars,
                framerate=self.framerate,
                pipe=self.cava_pipe,
                channels=self.channels,
            )
            with tempfile.NamedTemporaryFile(delete=False) as self.config_file:
                self.config_file.write(config.encode())
                self.config_file.flush()
            self._interval = 1 / self.framerate
            self.y_offset = (self.height - self.bar_height) // 2
            if self.autostart:
                self.timeout_add(1, self._start)

        self._set_length()

    def _set_length(self):
        old = self.length

        if self._procs_started or not self.hide:
            new = self._config_length
        else:
            new = 0

        if old != new or not self.hide:
            self.bar.draw()

        self.length = new

    def _start(self):
        self._starting = True
        self.cava_proc = self.qtile.spawn([self.cava_path, "-p", self.config_file.name])
        cmd = [
            PYTHON,
            CAVA_DRAW.resolve().as_posix(),
            "--width",
            f"{self._config_length}",
            "--height",
            f"{self.bar_height}",
            "--bars",
            f"{self.bars}",
            "--spacing",
            f"{self.spacing}",
            "--pipe",
            f"{self.cava_pipe}",
            "--background",
            self.bar_colour,
        ]
        if self.invert:
            cmd.append("--invert")

        self.draw_proc = self.qtile.spawn(cmd)
        self._timer = self.timeout_add(1, self._open_shm)

    def _stop(self):
        if self._timer:
            self._timer.cancel()

        if not self._procs_started:
            return

        # Try to terminate subprocesses
        if hasattr(self, "cava_proc"):
            os.kill(self.cava_proc, signal.SIGTERM)

        if hasattr(self, "draw_proc"):
            os.kill(self.draw_proc, signal.SIGTERM)

        self._procs_started = False

        # Close shared memory objects
        self._shm.close()
        self._shmfile.close()
        self._lock.close()
        self._lockfile.close()

        if fps_lock.locked():
            fps_lock.release()

        self._set_length()

    def _open_shm(self):
        self._lockfile = open(LOCK, "rb+")
        self._shmfile = open(SHM, "rb")
        self._lock = mmap.mmap(self._lockfile.fileno(), length=1, access=mmap.ACCESS_WRITE)
        self._shm_size = self.bar_height * self._config_length * 4
        self._shm = mmap.mmap(
            self._shmfile.fileno(), length=self._shm_size, access=mmap.ACCESS_READ
        )

        # Context manager to prevent race conditions when accessing shared memory
        @contextmanager
        def lock_shm():
            while self._lock[0]:
                sleep(0.001)

            self._lock[0] = 1
            yield
            self._lock[0] = 0

        self._take_lock = lock_shm
        self._procs_started = True
        self._starting = False
        self._set_length()

    @contextmanager
    def lock_state(self):
        """Startup takes a while and involves timers so set a flag when changing state."""
        self._toggling = True
        yield
        self._toggling = False

    def draw(self):
        # If the processes aren't running, trying to access the shared memory will fail.
        if not self._procs_started:
            self.drawer.clear(self.background or self.bar.background)
            self.drawer.draw(offsetx=self.offsetx, offsety=self.offsety, width=self.length)
            return

        # We need to lock the redraw to our set framerate. We can't rely solely on timers
        # as any call to bar.draw() by another widget will trigger a draw of the widget.
        # We use a non-blocking lock and only allow the widget to draw if the lock was
        # successfully acquired. The lock is only released after the required interval has
        # elapsed.
        if not fps_lock.acquire(blocking=False):
            return

        self._draw()

    def _draw(self):
        with self._take_lock():
            surface = cairocffi.ImageSurface.create_for_data(
                bytearray(self._shm[: self._shm_size]),
                cairocffi.FORMAT_ARGB32,
                self._config_length,
                self.bar_height,
            )

        self.drawer.clear(self.background or self.bar.background)
        self.drawer.ctx.set_source_surface(surface, 0, self.y_offset)
        self.drawer.ctx.paint()
        self.drawer.draw(offsetx=self.offsetx, offsety=self.offsety, width=self.length)

        self._timer = self.timeout_add(self._interval, self.loop)

    def loop(self):
        # Release the lock and redraw.
        fps_lock.release()
        self.draw()

    def finalize(self):
        self._stop()
        Path(self.config_file.name).unlink()
        base._Widget.finalize(self)

    @expose_command()
    def stop(self):
        """Stop this visualiser."""
        if self._toggling or not self._procs_started:
            return

        with self.lock_state():
            self._stop()

    @expose_command()
    def start(self):
        """Start the visualiser."""
        if self._procs_started or self._toggling or self._starting:
            return

        with self.lock_state():
            self._start()

    @expose_command()
    def toggle(self):
        """Toggle visualiser state."""
        if self._toggling:
            return

        with self.lock_state():
            if self._procs_started:
                self._stop()
            else:
                self._start()


# For the Americans...
Visualizer = Visualiser
