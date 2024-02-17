# Copyright (c) 2024 elParaguayo
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

from cairocffi.pixbuf import ImageLoadingError
from libqtile import bar
from libqtile.command.base import expose_command
from libqtile.log_utils import logger
from libqtile.widget import base

from qtile_extras.images import Img


class AnimatedImage(base._Widget, base.MarginMixin):
    """
    A widget to display an animation when clicked.
    """

    defaults = [
        ("filenames", list(), "List of image filename. Can contain '~'. Can also be a url."),
        (
            "padding",
            0,
            "Padding to left and right of image on horizontal bar, or above and below widget on vertical bar.",
        ),
        ("loop_count", 1, "Number of time to loop through images. 0 to loop forever."),
        ("frame_interval", 0.1, "Time between individual images"),
        ("loop_interval", 1, "Interval before restarting loop"),
        ("scale", True, "Resize images to fit bar (as adjusted by margin settings)."),
    ]

    def __init__(self, length=bar.CALCULATED, **config):
        base._Widget.__init__(self, length, **config)
        self.add_defaults(AnimatedImage.defaults)
        self.add_defaults(base.MarginMixin.defaults)
        self.add_callbacks({"Button1": self.animate})
        self.images = []
        self.index = 0
        self._timer = None
        self.loop_index = 0
        self._do_loop = False

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)

        # Make sure we don't have a negative loop count
        self.loop_count = max(self.loop_count, 0)

        self._load_images()
        if self.images:
            self.max_width = max(img.width for img in self.images)
            self.max_height = max(img.height for img in self.images)

    def _load_images(self):
        for filename in self.filenames:
            img = self._load_image(filename)
            if img is not None:
                self.images.append(img)

    def _load_image(self, filename):
        img = None

        filename = os.path.expanduser(filename)

        if filename.startswith("http"):
            img = Img.from_url(filename)

        else:
            if not os.path.exists(filename):
                logger.warning("Image does not exist: %s", filename)
                return
            try:
                img = Img.from_path(filename)
            except ImageLoadingError:
                logger.error("Could not load image: %s.", filename)

        if img is not None and self.scale:
            if self.bar.horizontal:
                new_height = self.bar.height - (self.margin_y * 2)
                img.resize(height=new_height)
            else:
                new_width = self.bar.width - (self.margin_x * 2)
                img.resize(width=new_width)

        return img

    def draw(self):
        if not self.images:
            return

        img = self.images[self.index]

        pad_x = self.padding if self.bar.horizontal else 0
        pad_y = self.padding if not self.bar.horizontal else 0

        self.drawer.clear(self.background or self.bar.background)
        self.drawer.ctx.save()
        self.drawer.ctx.translate(self.margin_x + pad_x, self.margin_y + pad_y)

        self.drawer.ctx.set_source(img.pattern)
        self.drawer.ctx.paint()
        self.drawer.ctx.restore()

        if self.bar.horizontal:
            self.drawer.draw(offsetx=self.offset, offsety=self.offsety, width=self.width)
        else:
            self.drawer.draw(offsety=self.offset, offsetx=self.offsetx, height=self.width)

        if self._do_loop and (self._timer is None or not self._timer._scheduled):
            self._queue_next()

    def calculate_length(self):
        if not self.images:
            return 0

        if self.bar.horizontal:
            return self.max_width + (self.margin_x * 2) + (self.padding * 2)
        else:
            return self.max_height + (self.margin_y * 2) + (self.padding * 2)

    def _queue_next(self):
        # Are we in the middle of a loop?
        if self.index < len(self.images) - 1:
            self._timer = self.timeout_add(self.frame_interval, self._next_frame)

        # Or are we at end of loop?
        elif self.index == len(self.images) - 1:
            # Do we need another loop?
            if not self.loop_count or self.loop_index + 1 < self.loop_count:
                self._timer = self.timeout_add(self.loop_interval, self._next_loop)
            # Or have we finished?
            else:
                self._timer = self.timeout_add(self.loop_interval, self._loop_finished)

    def _next_frame(self):
        self.index += 1
        self.draw()

    def _next_loop(self):
        # Go back to first frame but increment loop counter
        self.index = 0
        self.loop_index += 1
        self.draw()

    def _loop_finished(self):
        # Set the flag to say we're not looping
        self._do_loop = False

        # Reset indexes to first frame
        self.index = 0
        self.loop_index = 0
        self.draw()

    @expose_command
    def animate(self):
        """Start the animation."""
        self._do_loop = True
        self.index = 0
        self.loop_index = 0
        self.draw()

    @expose_command
    def stop(self):
        """Stop the animation."""
        if self._timer is not None and not self._timer.cancelled():
            self._timer.cancel()
        self._loop_finished()
