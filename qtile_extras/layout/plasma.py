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
from libqtile.command.base import expose_command
from libqtile.layout.plasma import AddMode
from libqtile.layout.plasma import Plasma as QtilePlasma


class Plasma(QtilePlasma):
    """
    This is a modified version of the Plasma layout in the main qtile repo.

    The change is to add new ``border_highlight_...`` parameters which can be used to
    highlight the add_mode for the current window. These values will benefit from
    the new window border decorations in qtile-extras i.e. single edges can now be
    highlighted.

    To have this behaviour enabled by default, you should set ``highlight=True``.
    Alternatively, the behaviour can be toggled with ``lazy.layout.toggle_highlight()``.
    """

    defaults = [
        ("highlight", False, "Highlights the add_mode for the layout."),
        ("border_highlight_vertical", None, "Border for focused window with vertical add_mode."),
        (
            "border_highlight_vertical_split",
            None,
            "Border for focused window with vertical split add_mode.",
        ),
        (
            "border_highlight_horizontal",
            None,
            "Border for focused window with horizontal add_mode.",
        ),
        (
            "border_highlight_horizontal_split",
            None,
            "Border for focused window with horizontal add_mode.",
        ),
    ]

    def __init__(self, **config):
        QtilePlasma.__init__(self, **config)
        self.add_defaults(Plasma.defaults)

        self.highlights = {
            AddMode.VERTICAL: self.border_highlight_vertical,
            AddMode.VERTICAL | AddMode.SPLIT: self.border_highlight_vertical_split,
            AddMode.HORIZONTAL: self.border_highlight_horizontal,
            AddMode.HORIZONTAL | AddMode.SPLIT: self.border_highlight_horizontal_split,
        }

    def configure(self, client, screen_rect):
        self.root.x = screen_rect.x
        self.root.y = screen_rect.y
        self.root.width = screen_rect.width
        self.root.height = screen_rect.height
        node = self.root.find_payload(client)
        border_width = self.border_width_single if self.root.tree == [node] else self.border_width
        border_color = getattr(
            self,
            "border_"
            + ("focus" if client.has_focus else "normal")
            + ("" if node.flexible else "_fixed"),
        )

        if client is self.focused and self.highlight:
            if self.horizontal:
                if self.split:
                    add_mode = AddMode.HORIZONTAL | AddMode.SPLIT
                else:
                    add_mode = AddMode.HORIZONTAL
            else:
                if self.split:
                    add_mode = AddMode.VERTICAL | AddMode.SPLIT
                else:
                    add_mode = AddMode.VERTICAL

            highlight = self.highlights[add_mode]

            border_color = highlight if highlight else border_color

        x, y, width, height = node.pixel_perfect
        client.place(
            x,
            y,
            width - 2 * border_width,
            height - 2 * border_width,
            border_width,
            border_color,
            margin=self.margin,
        )
        # Always keep tiles below floating windows
        client.unhide()

    @expose_command
    def toggle_highlight(self):
        """Toggle window border highlighting."""
        if self.group is not None:
            self.highlight = not self.highlight
            self.group.layout_all()
