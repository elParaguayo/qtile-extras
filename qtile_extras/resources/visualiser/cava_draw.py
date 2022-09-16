#!/usr/bin/env python

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
import argparse
import signal
from contextlib import contextmanager
from multiprocessing import shared_memory
from pathlib import Path
from time import sleep

import cairocffi
from libqtile.utils import rgb


def draw_cava(width, height, num_bars, pad, bar_width, spacing, pipe, background):
    mem_size = width * height * 4
    shm = shared_memory.SharedMemory(name="qte_cava_visualiser", create=True, size=mem_size)
    lock = shared_memory.SharedMemory(name="qte_cava_lock", create=True, size=1)

    # Create a context manager to lock access to shared memory to prevent race conditions
    @contextmanager
    def lock_memory(buf):
        while buf[0]:
            sleep(0.001)
        buf[0] = 1
        yield
        buf[0] = 0

    # Handler to tidy up shared memory objects if script is terminated
    def kill_shm():
        try:
            shm.close()
            shm.unlink()
        except FileNotFoundError:
            pass

        try:
            lock.close()
            lock.unlink()
        except FileNotFoundError:
            pass

    signal.signal(signal.SIGTERM, kill_shm)

    surface = cairocffi.ImageSurface(cairocffi.FORMAT_ARGB32, width, height)
    ctx = cairocffi.Context(surface)
    buffer = shm.buf
    lock_buffer = lock.buf
    lock_buffer[0] = 0

    with open(pipe, "rb") as reader:

        while True:
            out = reader.read(num_bars)

            while out:
                ctx.set_operator(cairocffi.OPERATOR_CLEAR)
                ctx.rectangle(0, 0, width, height)
                # ctx.set_source_rgb(0, 0, 0)
                ctx.fill()
                ctx.set_operator(cairocffi.OPERATOR_SOURCE)
                x = pad
                for bar in out:
                    ctx.move_to(x, height)
                    h = int(bar * height / 255)
                    ctx.line_to(x, height - h)
                    x += bar_width
                    ctx.line_to(x, height - h)
                    ctx.line_to(x, height)
                    x += spacing

                ctx.close_path()

                ctx.set_source_rgba(*background)
                ctx.fill()

                with lock_memory(lock_buffer):
                    buffer[:] = bytearray(surface.get_data())

                out = reader.read(num_bars)

            break


if __name__ == "__main__":
    # Tidy up left over shared memory files
    for shm in ["qte_cava_lock", "qte_cava_visualiser"]:
        p = Path("/dev/shm") / shm
        if p.is_file():
            p.unlink()

    parser = argparse.ArgumentParser(description="Script to offload visualiser image generation.")
    parser.add_argument("--width", dest="width", type=int, help="Image width", required=True)
    parser.add_argument("--height", dest="height", type=int, help="Image height", required=True)
    parser.add_argument("--bars", dest="num_bars", type=int, help="Number of bars", required=True)
    parser.add_argument(
        "--spacing", dest="spacing", type=int, help="Spacing between bars", required=True
    )
    parser.add_argument("--background", dest="background", type=rgb, help="Background colour")
    parser.add_argument(
        "--pipe", dest="pipe", type=str, help="Pipe for cava output", required=True
    )

    args = parser.parse_args()

    bar_width = args.width // args.num_bars
    pad = (args.width - (bar_width * args.num_bars)) // 2
    bar_width -= args.spacing

    draw_cava(
        args.width,
        args.height,
        args.num_bars,
        pad,
        bar_width,
        args.spacing,
        args.pipe,
        args.background,
    )
