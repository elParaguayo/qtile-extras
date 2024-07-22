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
from __future__ import annotations

import itertools
import math
from copy import deepcopy
from enum import Flag, auto
from pathlib import Path
from typing import TYPE_CHECKING, Union

from cairocffi.pixbuf import ImageLoadingError
from libqtile import bar, hook
from libqtile.images import Img
from libqtile.log_utils import logger
from libqtile.scratchpad import ScratchPad
from libqtile.utils import describe_attributes
from libqtile.widget import base

if TYPE_CHECKING:
    from typing import Any, Callable, Literal


ColorType = Union[str, tuple[int, int, int], tuple[int, int, int, float]]
ColorsType = Union[ColorType, list[ColorType]]


IMAGE_CACHE: dict[str, Img] = {}
BAD_IMAGES: list[str] = []


class Sentinel:
    """
    Custom class that is "falsey" for boolean logic purposes and returns
    itself when copy.deepcopy is run on the object.
    """

    def __bool__(self) -> Literal[False]:
        return False

    def __deepcopy__(self, _memo) -> Sentinel:
        return self


# Sentinel instance is used so that we can allow "None" as an attribute value
SENTINEL = Sentinel()


# Custom flags for setting certain conditions
class ScreenRule(Flag):
    UNSET = auto()
    THIS = auto()
    OTHER = auto()
    ANY = THIS | OTHER
    NONE = auto()


class LinePosition(Flag):
    BOTTOM = auto()
    TOP = auto()
    LEFT = auto()
    RIGHT = auto()


def filter_attrs(attr: Any) -> bool:
    """
    Function for use with libqtile.utils.describe_attrs.

    Ignores None and UNSET screen flags.
    """
    if attr is None or attr is ScreenRule.UNSET:
        return False

    return True


class GroupBoxRule:
    # Aliases for screen and line position flags - reduces imports in config files
    SCREEN_UNSET = ScreenRule.UNSET
    SCREEN_THIS = ScreenRule.THIS
    SCREEN_OTHER = ScreenRule.OTHER
    SCREEN_ANY = SCREEN_THIS | SCREEN_OTHER
    SCREEN_NONE = ScreenRule.NONE

    LINE_TOP = LinePosition.TOP
    LINE_BOTTOM = LinePosition.BOTTOM
    LINE_RIGHT = LinePosition.RIGHT
    LINE_LEFT = LinePosition.LEFT

    attrs = [
        "text_colour",
        "block_colour",
        "block_border_width",
        "block_border_colour",
        "block_corner_radius",
        "line_width",
        "line_colour",
        "line_position",
        "image",
        "custom_draw",
        "text",
        "box_size",
        "visible",
    ]

    def __init__(
        self,
        text_colour: ColorType | Sentinel | None = SENTINEL,
        block_colour: ColorsType | Sentinel | None = SENTINEL,
        block_border_width: int | Sentinel | None = SENTINEL,
        block_border_colour: ColorType | Sentinel | None = SENTINEL,
        block_corner_radius: int | Sentinel | None = SENTINEL,
        line_width: int | Sentinel | None = SENTINEL,
        line_colour: ColorType | Sentinel | None = SENTINEL,
        line_position: LinePosition | Sentinel | None = SENTINEL,
        image: str | Sentinel | None = SENTINEL,
        custom_draw: Callable[[Box], None] | None | Sentinel = SENTINEL,
        text: str | Sentinel | None = SENTINEL,
        box_size: int | Sentinel | None = SENTINEL,
        visible: bool | Sentinel | None = SENTINEL,
    ):
        self.text_colour = text_colour
        self.block_colour = block_colour
        self.block_border_width = block_border_width
        self.block_border_colour = block_border_colour
        self.block_corner_radius = block_corner_radius
        self.line_width = line_width
        self.line_colour = line_colour
        self.line_position = line_position
        self.image = image
        self.custom_draw = custom_draw
        self.text = text
        self.box_size = box_size
        self.visible = visible
        self.screen = ScreenRule.UNSET
        self.focused: bool | None = None
        self.occupied: bool | None = None
        self.urgent: bool | None = None
        self.group_name: str | None = None
        self.func: Callable[[GroupBoxRule, Box], bool] | None = None

    size: int | Sentinel | None

    def when(
        self,
        screen: ScreenRule = ScreenRule.UNSET,
        focused: bool | None = None,
        occupied: bool | None = None,
        urgent: bool | None = None,
        group_name: str | None = None,
        func: Callable[[GroupBoxRule, Box], bool] | None = None,
    ):
        """Define criteria that rule must match in order to be applied."""
        if screen is not ScreenRule.UNSET:
            self.screen = screen

        if focused is not None:
            self.focused = focused

        if occupied is not None:
            self.occupied = occupied

        if urgent:
            self.urgent = urgent

        if group_name:
            self.group_name = group_name

        if func:
            self.func = func

        return self

    def match(self, box: Box) -> bool:
        """Returns True if box conditions match rule criteria."""
        if not self.screen & ScreenRule.UNSET:
            if not box.screen & self.screen:
                return False

        if self.focused is not None:
            if box.focused != self.focused:
                return False

        if self.occupied is not None:
            if box.occupied != self.occupied:
                return False

        if self.group_name is not None:
            if box.group.name != self.group_name:
                return False

        if self.func:
            if not self.func(self, box):
                return False

        return True

    def clone(self) -> GroupBoxRule:
        return deepcopy(self)

    def reset(self, attr: str) -> None:
        setattr(self, attr, SENTINEL)

    def __repr__(self) -> str:
        """Short representation of rule instance."""
        output = describe_attributes(self, GroupBoxRule.attrs, lambda x: x is not SENTINEL)
        when = describe_attributes(
            self, ["screen", "focused", "occupied", "urgent", "group_name", "func"], filter_attrs
        )
        return f"<GroupBoxRule format({output}) when({when})>"


class Box:
    # Attributes loaded dynamically from widget
    font: str
    fontsize: int | None
    fontshadow: bool | None
    markup: bool
    padding_x: int
    paddint_y: int
    rules: list[GroupBoxRule]
    margin_x: int
    margin_y: int

    # Attributes loaded dynamically from rules
    text_colour: ColorType | Sentinel | None
    block_colour: ColorsType | Sentinel | None
    block_border_width: int | Sentinel | None
    block_border_colour: ColorType | Sentinel | None
    block_corner_radius: int | Sentinel | None
    line_width: int | Sentinel | None
    line_colour: ColorType | Sentinel | None
    line_position: LinePosition | Sentinel | None
    image: str | Sentinel | None
    custom_draw: Callable[[Box], None] | Sentinel | None
    text: str | Sentinel | None
    box_size: int | Sentinel | None
    visible: bool | Sentinel | None

    def __init__(self, group, index, bar, qtile, drawer, config):
        self.group = group
        self.index = index
        self.bar = bar
        self.qtile = qtile
        self.drawer = drawer
        self.screen = SENTINEL
        self.focused = SENTINEL
        self.occupied = SENTINEL
        self.urgent = SENTINEL
        for k, v in config.items():
            setattr(self, k, v)
        self.rules = [rule.clone() for rule in self.rules]
        self.layout = self.drawer.textlayout(
            "",
            "ffffff",
            self.font,
            self.fontsize,
            self.fontshadow,
            markup=self.markup,
        )
        self._reset_format()
        self._prepare()

    def _prepare(self):
        """
        Checks the current state of the group and decides whether rules need to be
        run or not.
        """
        if self.group.screen is self.bar.screen:
            screen = ScreenRule.THIS
        elif self.group.screen:
            screen = ScreenRule.OTHER
        else:
            screen = ScreenRule.NONE

        focused = self.qtile.current_group is self.group
        occupied = bool(self.group.windows)
        urgent = any(w.urgent for w in self.group.windows)

        if (screen, focused, occupied, urgent) == (
            self.screen,
            self.focused,
            self.occupied,
            self.urgent,
        ):
            # Nothing has changed so we don't need to rerun rules
            return

        self.screen = screen
        self.focused = focused
        self.occupied = occupied
        self.urgent = urgent

        self._set_formats()

    def _set_formats(self):
        """Applies formats based on matching rules."""
        # Clear formatting
        self._reset_format()

        # Get matching rules
        rules = [rule for rule in self.rules if rule.match(self)]

        # Warn user if no rules match.
        if not rules:
            attrs = ["screen", "focused", "occupied", "urgent"]
            logger.error(
                "No matching groupboxrule for condition: %s",
                describe_attributes(self, attrs, lambda x: x is not None),
            )
            # Widget will fall back to white text.

        # Apply rule formatting with earlier rules having precedence over later ones
        for rule in rules:
            self._update_format(rule)

        if not self.text_colour:
            self.text_colour = "ffffff"

        if self.text is SENTINEL:
            self.text = self.group.label or self.group.name

        if self.block_border_colour and self.block_border_width is SENTINEL:
            self.block_border_width = 2

        if self.line_colour and self.line_width is SENTINEL:
            self.line_width = 2

        if self.has_line and self.line_position is SENTINEL:
            self.line_position = LinePosition.BOTTOM

        if self.image:
            if not self._load_image(self.image):
                self.image = None

    def _load_image(self, filename: str, scale=True) -> bool:
        """
        Loads an image file into an ``Img`` object and stores in a cache
        to prevent image being loaded multiple times.
        """
        # Image is in cache already so nothing further needed here
        if filename in IMAGE_CACHE:
            return True

        # We already know this is a bad file so we stop here
        if filename in BAD_IMAGES:
            return False

        path = Path(filename).expanduser()

        if not path.exists() and path.is_file():
            # We store bad filenames in the ``BAD_IMAGES`` list so there's only
            # one warning the first time we try to load a non-existent file.
            logger.warning("Image file does not exist: %s", path.as_posix())
            BAD_IMAGES.append(filename)
            return False

        try:
            img = Img.from_path(path.as_posix())
        except ImageLoadingError:
            logger.warning("Image file cannot be opened: %s.", path.as_posix())
            BAD_IMAGES.append(filename)
            return False

        if scale:
            img.resize(height=self.bar.height - 2 * self.margin_y)
        IMAGE_CACHE[filename] = img

        return True

    def get_image(self, filename: str, scale=True) -> Img | None:
        """Tries to load image from cache and return ``Img`` instance."""
        if filename in IMAGE_CACHE or self._load_image(filename, scale):
            return IMAGE_CACHE[filename]

        return None

    @property
    def rule_attrs(self) -> list[str]:
        return GroupBoxRule.attrs

    def _reset_format(self) -> None:
        """Clears all formatting for the box."""
        # Use ``SENTINEL`` instance as default value so we can allow a value
        # of ``None``
        for attr in self.rule_attrs:
            setattr(self, attr, SENTINEL)

    def _update_format(self, rule) -> None:
        """Updates box formatting attributes."""
        for attr in self.rule_attrs:
            # Only set the format if it's a ``SENTINEL`` object
            # i.e. it has not been set by an earlier rule.
            if getattr(self, attr) is SENTINEL and getattr(rule, attr) is not SENTINEL:
                setattr(self, attr, getattr(rule, attr))

    @property
    def size(self) -> int:
        """Returns the size of the box."""
        self._prepare()
        del self.layout.width
        self.layout.text = self.text

        if self.visible is False:
            return 0

        if self.box_size:
            return self.box_size

        elif self.image and self.image in IMAGE_CACHE:
            return IMAGE_CACHE[self.image].width + 2 * self.margin_x

        return self.layout.width + 2 * self.padding_x

    @property
    def has_block(self) -> bool:
        """Do we have the attributes needed to draw a block?"""
        return bool(self.block_colour or self.block_border_width)

    @property
    def has_line(self) -> bool:
        """Do we have the attributes needed to draw a line?"""
        return bool(self.line_colour and self.line_width)

    def draw_block(self) -> None:
        """Draws the block formatting: filled block and/or block border."""
        ctx = self.drawer.ctx

        # If there's no radius then we just draw a rectangle shape
        if not self.block_corner_radius:
            ctx.rectangle(
                self.margin_x,
                self.margin_y,
                self.size - 2 * self.margin_x,
                self.bar.height - 2 * self.margin_y,
            )

        # If not, we need to do rounded corers
        else:
            radius = self.block_corner_radius
            degrees = math.pi / 180.0

            ctx.new_sub_path()

            delta = radius + 1
            x = self.margin_x
            y = self.margin_y
            width = self.size - 2 * self.margin_x
            height = self.bar.height - 2 * self.margin_y
            ctx.arc(x + width - delta, y + delta, radius, -90 * degrees, 0 * degrees)
            ctx.arc(x + width - delta, y + height - delta, radius, 0 * degrees, 90 * degrees)
            ctx.arc(x + delta, y + height - delta, radius, 90 * degrees, 180 * degrees)
            ctx.arc(x + delta, y + delta, radius, 180 * degrees, 270 * degrees)
            ctx.close_path()

        # Fill the block and keep the path
        if self.block_colour:
            self.drawer.set_source_rgb(self.block_colour)
            ctx.fill_preserve()

        # Draw the border
        if self.block_border_colour and self.block_border_width:
            ctx.set_line_width(self.block_border_width)
            self.drawer.set_source_rgb(self.block_border_colour)
            ctx.stroke()

        # Clear the path
        ctx.new_path()

    def _draw_line(self, offset, vertical=False) -> None:
        """
        Draws a horizontal or vertical line.

        Horizontal lines are the width of the box. Vertical lines are the height
        of the box.
        """
        if vertical:
            start = (offset, 0)
            end = (0, self.bar.height)
        else:
            start = (0, offset)
            end = (self.size, 0)

        ctx = self.drawer.ctx
        ctx.save()
        ctx.translate(*start)
        ctx.set_line_width(self.line_width)
        self.drawer.set_source_rgb(self.line_colour)
        ctx.new_sub_path()
        ctx.move_to(0, 0)
        ctx.line_to(*end)
        ctx.stroke()
        ctx.restore()

    def draw_line(self, line_width: int) -> None:
        """Draws line(s) at the edge of the box."""
        assert isinstance(self.line_position, LinePosition)

        if self.line_position & LinePosition.TOP:
            self._draw_line(line_width // 2)

        if self.line_position & LinePosition.BOTTOM:
            self._draw_line(self.bar.height - line_width // 2)

        if self.line_position & LinePosition.LEFT:
            self._draw_line(line_width // 2, vertical=True)

        if self.line_position & LinePosition.RIGHT:
            self._draw_line(self.size - line_width // 2, vertical=True)

    def draw_image(self) -> None:
        """Draws the image, offset by margin_x and margin_y."""
        assert self.image
        img = self.get_image(self.image)

        # This shouldn't be needed but let's be safe...
        if img is None:
            return

        ctx = self.drawer.ctx
        ctx.save()
        ctx.translate((self.size - img.width) // 2, self.margin_y)
        ctx.set_source(img.pattern)
        ctx.paint()
        ctx.restore()

    def draw_text(self) -> None:
        """Draws text, centered vertically."""
        self.layout.colour = self.text_colour
        self.layout.draw(self.padding_x, (self.bar.height - self.layout.height) // 2)

    def draw(self, offset) -> None:
        """Main method to draw all formatting."""
        self.drawer.ctx.save()

        self.drawer.ctx.translate(offset, 0)

        if self.has_block:
            self.draw_block()

        if self.has_line and isinstance(self.line_width, int):
            self.draw_line(self.line_width)

        if self.image:
            self.draw_image()

        if self.custom_draw:
            self.drawer.ctx.save()
            self.custom_draw(self)
            self.drawer.ctx.restore()

        if self.text:
            self.draw_text()

        self.drawer.ctx.restore()


class GroupBox2(base._Widget, base.MarginMixin, base.PaddingMixin):
    """
    Formatting of the group box is determined by applying user-defined rules to each group.

    Overview:

    A rule can set any combination of the following formats:

    * text_colour - a string representing the hex value of the colour for the text
    * block_colour - a string or list of strings to fill a block
    * block_border_width - an integer representing the width of a block border
    * block_border_colour - a string representing the colour of the block border
    * block_corner_radius - an integer representing radius for curved corners
    * line_colour - a string representing the colour of a line
    * line_width - an integer representing the width of the line
    * line_position - a flag representing where the line should be drawn
    * image - path to an image file
    * custom_draw - a function that draws to the box
    * text - string representing text to display
    * box_size - integer to force the size of the individual box
    * visible - boolean to set visibility of box. Box will display by default unless a rule sets ``visible=False``

    Whether a rule is applied will depend on whether it meets the relevant conditions set for each rule.
    A rule can set any combination of the following conditions:

    * Which screen the group is on (same screen as bar, different screen, no screen)
    * Whether the group is focused (i.e. the current group) - boolean True/False
    * Whether the group has windows - boolean True/False
    * Whether the group has any urgent windows - boolean True/False
    * Whether the group name matches a given string
    * Whether a user-defined function returns True

    Order of drawing:

    The widget draws the groupbox in the following order:

    * Background colour
    * Block
    * Block border
    * Line
    * Image
    * Custom draw function
    * Text

    Explanation of groupbox items:

    Block:

    Block is a rectangle that can be filled (with ``block_colour``) and/or have an outline (with ``block_border_width`` and
    ``block_border_colour``). The corners of the rectangle can be curved by setting the ``block_corner_radius`` value.

    The block is positioned by using the ``margin(_x)`` and ``margin_y`` attributes. NB Currently, these are global for the widget
    and cannot be set by rules.

    Line:

    Line is a straight line on the edge of the widget. A line will be drawn at the bottom of the box by default (when a ``line_colour``
    and ``line_width`` have been set). The position of lines can be changed by setting the ``line_position`` attribute with
    a ``LinePosition`` flag. For example to drawn lines at the top and bottom of the box you would set the ``line_position`` value to:

    .. code:: python

        from qtile_extras.widget.groupbox2 import GroupBoxRule


        GroupBoxRule.LINE_TOP | GroupBoxRule.LINE_BOTTOM

    NB the line will be rendered at the edge of the box i.e. it is not currently offset by the margin value.

    Image:

    Image renders any image file in the box. The image will be shrunk so that the height fits within the bar and is also adjusted
    by the ``margin(_x)`` and ``margin(_y)`` attributes.

    Text:

    A rule is able to set custom text for a group box. Where this is not set, the box will display the group's label or name by
    default. Setting a value of ``None`` will prevent text from being shown.

    Custom draw:

    You can define a function to draw directly to the box. The function should take a single argument which is the instance of
    the box. You can access the drawer object and its context via the ``box.drawer`` and ``box.drawer.ctx`` attributes.

    The drawing should be constrained to the rectangle defined by (x=0, y=0, width=box.size, height=box.bar.height). The origin is
    the top left corner.

    For example, to define a rule that draws a red square in the middle of the box for occupied groups, you would do the following:

    .. code:: python

        from qtile_extras.widget.groupbox2 import GroupBoxRule


        def draw_red_square(box):

            w = 10
            h = 10
            x = (box.size - w) // 2
            y = (box.bar.height - h) // 2
            box.drawer.ctx.rectangle(x, y, w, h)
            box.drawer.set_source_rgb("ff0000")
            box.drawer.ctx.fill()

        # Add this to your rules:
        GroupBoxRule(custom_draw=draw_red_square).when(occupied=True)

    Creating rules:

    Creating a rule has two steps:

    * Setting the desired format
    * Setting the conditions required for that rule

    To help readibility of config files, this is split so the format is set in the rule's constructor while the conditions are
    set by the rule's ``when()`` method.

    For example, to set a rule that sets the font colour to cyan when a group has windows but is not focused, you would
    create the following rule:

    .. code:: python

        from qtile_extras.widget.groupbox2 import GroupBoxRule


        GroupBoxRule(text_colour="00ffff").when(focused=False, occupied=True)
        #                    ^                            ^
        #      Format set via constructor    Conditions set via when() method

    How to match conditions:

    Screen:

    Matching a screen condition uses a ScreenRule object. Available options are:

    * GroupBoxRule.SCREEN_UNSET (default) - rule ignores screen condition
    * GroupBoxRule.SCREEN_THIS - group is on same screen as widget's bar
    * GroupBoxRule.SCREEN_OTHER - group is a different screen to the widget's bar
    * GroupBoxRule.SCREEN_ANY (same as GroupBoxRule.SCREEN_THIS | GroupBoxRule.SCREEN_OTHER) - group is on any screen
    * GroupBoxRule.SCREEN_NONE - group is not displayed on a screen

    Group focus:

    You can match a rule if the group is focused or unfocused by setting ``focused`` to ``True`` or
    ``False`` respectively. Leaving this attribute blank will ignore focus.

    Group has windows:

    You can match a rule if the group has windows or is empty by setting ``occupied`` to ``True`` or
    ``False`` respectively. Leaving this attribute blank will ignore the contents of a group.

    Group has urgent windows:

    You can match a rule if the group has or does not have any ugent windows by setting ``urgent``
    to ``True`` or ``False`` respectively. Leaving this attribute blank will ignore the urgency state of a group.

    Match group name:

    You can tie a rule to a specific group by setting ``group_name`` to the name of a particular group. Leaving this
    blank will ignore the group's name.

    User-defined functions:

    Using custom functions can extend the possibilities for customising the widget. These are set via the ``func`` argument.

    A function must take two arguments (the `GroupBoxRule` object and the `Box` object (that draws the specific box)) and
    return a boolean (True if the rule should be applied or False if not).

    By accessing properties of the `Box` object, it is possible to fine tune the criteria against which the rule will match. The `Box`
    has the following attributes which may be of use here: `qtile` - the qtile object, `group` - the specific group represented by the box,
    `bar` - the Bar containing this widget.

    As an example, to create a rule that is matched when a specific app is open in the group:

    .. code:: python

        from qtile_extras.widget.groupbox2 import GroupBoxRule


        def has_vlc(rule, box):
            for win in box.group.windows:
                if "VLC" in win.name:
                    return True

            return False

        # Include this in your group box rules
        # Turns label a nice shade of orange if the group has a VLC window open
        GroupBoxRule(text_colour="E85E00").when(func=has_vlc)

    In addition, a user-defined function can set display properties dynamically. For example, to have a different icon
    depending on the state of the group:

    .. code:: python

        from qtile_extras.widget.groupbox2 import GroupBoxRule


        def set_label(rule, box):
            if box.focused:
                rule.text = "◉"
            elif box.occupied:
                rule.text = "◎"
            else:
                rule.text = "○"

            return True

        # Include this in your group box rules
        # NB: The function returns True so this rule will always be run
        GroupBoxRule().when(func=set_label)

    Rule hierarchy:

    Rules are applied in a hierarchy according to the order that they appear in the `rules` parameter. Once a format has been set by a rule,
    it cannot be updated by a later rule. However, if one rule sets the text colour a later rule can still set another format (e.g.
    border colour). To prevent lower priority rules from setting a value, a rule can set the `None` value for that attribute.

    For example:

    .. code:: python

        from qtile_extras.widget.groupbox2 import GroupBoxRule


        rules = [
            GroupBoxRule(block_colour="009999").when(screen=GroupBoxRule.SCREEN_THIS),
            GroupBoxRule(block_colour="999999").when(occupied=True),
            GroupBoxRule(text_colour="ffffff")
        ]

    This rule will set all text white but will apply a blue block when the group is shown on the same screen as the widget
    even if the group is occupied. An occupied group will have a grey background provided it's not on the same screen as the
    widget.

    """

    _experimental = True

    orientations = base.ORIENTATION_HORIZONTAL

    defaults: list[tuple[str, Any, str]] = [
        (
            "visible_groups",
            None,
            "List of names of groups to show in widget. 'None' (default) to show all groups.",
        ),
        ("font", "sans", "Font to use for label."),
        ("fontsize", None, "Fontsize for labels,"),
        ("fontshadow", None, "Font shadow"),
        ("markup", False, "Use markup."),
        (
            "current_screen_focused_width",
            None,
            "Sets a fixed width for the focused group on the current screen.",
        ),
        (
            "rules",
            [
                GroupBoxRule(line_colour="00ffff").when(screen=GroupBoxRule.SCREEN_THIS),
                GroupBoxRule(line_colour="999999").when(screen=GroupBoxRule.SCREEN_OTHER),
                GroupBoxRule(text_colour="ffffff").when(occupied=True),
                GroupBoxRule(text_colour="999999").when(occupied=False),
            ],
            "Rules for determining how to format group box. See docstring for fuller explanation.",
        ),
        ("invert_mouse_wheel", False, "Whether to invert mouse wheel group movement"),
        ("use_mouse_wheel", True, "Whether to use mouse wheel events"),
    ]

    def __init__(self, **config):
        base._Widget.__init__(self, length=bar.CALCULATED, **config)
        self.add_defaults(base.MarginMixin.defaults)
        self.add_defaults(base.PaddingMixin.defaults)
        self.add_defaults(GroupBox2.defaults)
        self._box_config = {}

        default_callbacks = {"Button1": self.select_group}
        if self.use_mouse_wheel:
            default_callbacks.update(
                {
                    "Button5" if self.invert_mouse_wheel else "Button4": self.prev_group,
                    "Button4" if self.invert_mouse_wheel else "Button5": self.next_group,
                }
            )
        self.add_callbacks(default_callbacks)

    def _configure(self, qtile, bar):
        base._Widget._configure(self, qtile, bar)
        self._get_groups()
        self.boxes = [
            Box(group, index, bar, qtile, self.drawer, self.box_config)
            for index, group in enumerate(self.groups)
        ]
        self.setup_hooks()

    def setup_hooks(self):
        hook.subscribe.client_managed(self._hook_response)
        hook.subscribe.client_urgent_hint_changed(self._hook_response)
        hook.subscribe.client_killed(self._hook_response)
        hook.subscribe.setgroup(self._hook_response)
        hook.subscribe.group_window_add(self._hook_response)
        hook.subscribe.current_screen_change(self._hook_response)
        hook.subscribe.changegroup(self._hook_response)

    def remove_hooks(self):
        hook.unsubscribe.client_managed(self._hook_response)
        hook.unsubscribe.client_urgent_hint_changed(self._hook_response)
        hook.unsubscribe.client_killed(self._hook_response)
        hook.unsubscribe.setgroup(self._hook_response)
        hook.unsubscribe.group_window_add(self._hook_response)
        hook.unsubscribe.current_screen_change(self._hook_response)
        hook.unsubscribe.changegroup(self._hook_response)

    def _hook_response(self, *args, **kwargs):
        self.bar.draw()

    def calculate_length(self):
        return sum(box.size for box in self.boxes)

    def _get_groups(self):
        self.groups = []
        for group in self.qtile.groups:
            if (
                self.visible_groups is None
                or (self.visible_groups and group.name in self.visible_groups)
            ) and not isinstance(group, ScratchPad):
                self.groups.append(group)

        if not self.groups:
            logger.warning("No matching groups found.")

    @property
    def box_config(self):
        if self._box_config:
            return self._box_config

        config_vars = [
            "font",
            "fontsize",
            "fontshadow",
            "markup",
            "padding_x",
            "rules",
            "margin_x",
            "margin_y",
        ]
        self._box_config = {k: getattr(self, k) for k in config_vars}

        return self._box_config

    def draw(self):
        self.drawer.clear(self.background or self.bar.background)
        offset = 0
        for box in self.boxes:
            if box.visible is False:
                continue
            box.draw(offset)
            offset += box.size

        self.drawer.draw(
            offsetx=self.offsetx, offsety=self.offsety, height=self.height, width=self.width
        )

    def button_press(self, x, y, button):
        self.click_pos = x
        base._Widget.button_press(self, x, y, button)

    def get_clicked_group(self):
        group = None
        offset = 0
        for box in self.boxes:
            offset += box.size
            if self.click_pos <= offset:
                group = box.group
                break
        return group

    def next_group(self):
        group = None
        current_group = self.qtile.current_group
        i = itertools.cycle(self.qtile.groups)
        while next(i) != current_group:
            pass
        while group is None or group not in self.groups:
            group = next(i)
        self.go_to_group(group)

    def prev_group(self):
        group = None
        current_group = self.qtile.current_group
        i = itertools.cycle(reversed(self.qtile.groups))
        while next(i) != current_group:
            pass
        while group is None or group not in self.groups:
            group = next(i)
        self.go_to_group(group)

    def select_group(self):
        group = self.get_clicked_group()
        self.go_to_group(group)

    def go_to_group(self, group):
        if group:
            if self.bar.screen.group != group:
                self.bar.screen.set_group(group, warp=False)

    def finalize(self):
        self.remove_hooks()
        base._Widget.finalize(self)

    def info(self):
        info = base._Widget.info(self)
        info["text"] = "|".join(
            box.text if box.text else "" for box in self.boxes if box.visible is not False
        )
        return info
