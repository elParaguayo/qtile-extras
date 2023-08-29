# Copyright (c) 2023 The-Repo-Club
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

from libqtile import widget
from libqtile.confreader import ConfigError


class MultiColorTag(widget.GroupBox):
    def __init__(self, **config):
        super().__init__(**config)
        self.tag_colors = config.get("tag_colors", [])
        self.this_current_screen_border = config.get("this_current_screen_border", [])

        if not isinstance(self.tag_colors, list):
            raise ConfigError("MultiColorTag: tag_colors must be a list")
        if not isinstance(self.this_current_screen_border, list):
            raise ConfigError(
                "MultiColorTag: this_current_screen_border must be a list"
            )

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)

        offset = self.margin_x
        num_colors = len(self.tag_colors)
        num_borders = len(self.this_current_screen_border)

        for i, g in enumerate(self.groups):
            effective_color_index = i % num_colors
            effective_border_index = i % num_borders

            to_highlight = False
            is_block = self.highlight_method == "block"
            is_line = self.highlight_method == "line"

            bw = self.box_width([g])

            if self.group_has_urgent(g) and self.urgent_alert_method == "text":
                text_color = self.urgent_text
            elif g.windows:
                text_color = self.active
            else:
                text_color = self.inactive

            if effective_color_index < len(self.tag_colors):
                text_color = self.tag_colors[effective_color_index]

            if g.screen:
                if self.highlight_method == "text":
                    border = None
                    text_color = self.this_current_screen_border[effective_border_index]
                else:
                    if self.block_highlight_text_color:
                        text_color = self.block_highlight_text_color
                    if self.bar.screen.group.name == g.name:
                        if self.qtile.current_screen == self.bar.screen:
                            border = self.this_current_screen_border[
                                effective_border_index
                            ]
                            to_highlight = True
                        else:
                            border = self.this_screen_border
                    else:
                        if self.qtile.current_screen == g.screen:
                            border = self.other_current_screen_border
                        else:
                            border = self.other_screen_border
            elif self.group_has_urgent(g) and self.urgent_alert_method in (
                "border",
                "block",
                "line",
            ):
                border = self.urgent_border
                if self.urgent_alert_method == "block":
                    is_block = True
                elif self.urgent_alert_method == "line":
                    is_line = True
            else:
                border = None

            self.drawbox(
                offset,
                g.label,
                border,
                text_color,
                highlight_color=self.highlight_color,
                width=bw,
                rounded=self.rounded,
                block=is_block,
                line=is_line,
                highlighted=to_highlight,
            )
            offset += bw + self.spacing
        self.drawer.draw(offsetx=self.offset, offsety=self.offsety, width=self.width)
