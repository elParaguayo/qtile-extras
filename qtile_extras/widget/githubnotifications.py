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
from pathlib import Path

import requests
from libqtile import bar
from libqtile.command.base import expose_command
from libqtile.log_utils import logger
from libqtile.widget import base
from requests.exceptions import ConnectionError

from qtile_extras import hook
from qtile_extras.images import ImgMask

GITHUB_ICON = Path(__file__).parent / ".." / "resources" / "github-icons" / "github.svg"
NOTIFICATIONS = "https://api.github.com/notifications"


class GithubNotifications(base._Widget):
    """
    A widget to show when you have new github notifications.

    The widget requires a personal access token (see `here`_). The token needs
    the ``notifications`` scope to be enabled. This token should then be saved in
    a file and the path provided to the ``token_file`` parameter.

    If your key expires, re-generate a new key, save it to the same file and then
    call the ``reload_token`` command (e.g. via ``qtile cmd-obj``).

    .. _here: https://github.com/settings/tokens
    """

    orientations = base.ORIENTATION_HORIZONTAL
    defaults = [
        (
            "token_file",
            "~/.config/qtile-extras/github.token",
            "Path to file containing personal access token.",
        ),
        ("icon_size", None, "Icon size. None = autofit."),
        ("padding", 2, "Padding around icon."),
        (
            "inactive_colour",
            "ffffff",
            "Colour when there are no notifications.",
        ),
        ("active_colour", "00ffff", "Colour when there are notifications"),
        ("error_colour", "ffff00", "Colour when client has an error (check logs)"),
        ("update_interval", 150, "Number of seconds before checking status."),
    ]

    _screenshots = [("github_notifications.png", "")]

    _dependencies = ["requests"]

    _hooks = [h.name for h in hook.githubnotifications_hooks]

    def __init__(self, **config):
        base._Widget.__init__(self, bar.CALCULATED, **config)
        self.add_defaults(GithubNotifications.defaults)
        self.token = ""
        self.has_notifications = False
        self.error = False
        self._timer = None
        self._polling = False
        self._new_notification = False

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        self._load_token()
        self._load_icon()
        self.timeout_add(1, self.update)

    def _load_token(self):
        token_file = Path(self.token_file).expanduser()
        if not token_file.is_file():
            logger.error("No token_file provided.")
            self.error = True
            return

        with open(token_file, "r") as f:
            self.token = f.read().strip()

    def _load_icon(self):
        self.img = ImgMask.from_path(GITHUB_ICON)
        self.img.attach_drawer(self.drawer)

        if self.icon_size is None:
            size = self.bar.height - 1 - (self.padding * 2)
        else:
            size = min(self.icon_size, self.bar.height - 1)

        self.img.resize(size)
        self.icon_size = self.img.width

    @property
    def icon_colour(self):
        if self.error:
            return self.error_colour
        elif self.has_notifications:
            return self.active_colour
        else:
            return self.inactive_colour

    @expose_command()
    def update(self):
        """Trigger a check for new notifications."""
        if not self.token:
            self.error = True
            logger.error("No access token provided.")
            return
        self._polling = True
        future = self.qtile.run_in_executor(self._get_data)
        future.add_done_callback(self._read_data)
        if self._timer is not None and not self._timer.cancelled():
            self._timer.cancel()

    def _get_data(self):
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {self.token}",
        }
        return requests.get(NOTIFICATIONS, headers=headers)

    def _read_data(self, reply):
        self.error = True
        self._polling = False

        # Check if an exception was raised when trying to retrieve data
        exc = reply.exception()
        if exc:
            if isinstance(exc, ConnectionError):
                logger.error("Unable to connect to Github API.")
            else:
                logger.error(  # noqa: G201
                    "Unexpected error when connecting to Github.", exc_info=exc
                )

        # If not, get the result
        else:
            r = reply.result()

            if r.status_code != 200:
                logger.warning("Github returned a %d status code.", r.status_code)

            else:
                self.error = False
                self.has_notifications = bool(r.json())
                if self.has_notifications and not self._new_notification:
                    hook.fire("ghn_new_notification")
                self._new_notification = self.has_notifications

        self._timer = self.timeout_add(self.update_interval, self.update)
        self.draw()

    def calculate_length(self):
        if self.img is None:
            return 0

        return self.icon_size + 2 * self.padding

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)
        offsety = (self.bar.height - self.img.height) // 2
        self.img.draw(colour=self.icon_colour, x=self.padding, y=offsety)
        self.drawer.draw(offsetx=self.offsetx, offsety=self.offsety, width=self.length)

    @expose_command()
    def reload_token(self):
        """Force reload of access token."""
        self._load_token()
        if self._timer and not self._timer.cancelled():
            self._timer.cancel()
            self.update()
