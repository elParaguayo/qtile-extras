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
import inspect
import math

import cairocffi
import xcffib.xproto
from libqtile import qtile
from libqtile.configurable import Configurable
from libqtile.confreader import ConfigError
from libqtile.utils import rgb

try:
    from libqtile.backend.wayland._ffi import ffi, lib
    from libqtile.backend.wayland.window import _rgb
    from wlroots import ffi as wlr_ffi
    from wlroots import lib as wlr_lib
    from wlroots.wlr_types import Buffer, SceneBuffer
    from wlroots.wlr_types.scene import SceneRect

    HAS_WAYLAND = True
except (ImportError, ModuleNotFoundError):
    HAS_WAYLAND = False

HALF_ROOT_2 = 0.70711


class _BorderStyle(Configurable):
    """
    Base class for border decorations. Should be instantiated directly.

    This class is responsible for initialising the objects required to generate
    more complext borders.

    Decorations that render their design to a surface can just use the ``draw``
    method for this.
    """

    needs_surface = True

    def _check_colours(self):
        for colour in self.colours:
            try:
                rgb(colour)
            except ValueError:
                raise ConfigError(f"Invalid colour value in border decoration: {colour}.")

    def _create_xcb_surface(self):
        root = self.window.conn.conn.get_setup().roots[0]

        def find_visual(visual):
            for d in root.allowed_depths:
                if d.depth == self.depth:
                    for v in d.visuals:
                        if v.visual_id == visual:
                            return v

        return cairocffi.XCBSurface(
            self.window.conn.conn,
            self.pixmap,
            find_visual(self.visual),
            self.outer_w,
            self.outer_h,
        )

    def _new_buffer(self):
        surface = cairocffi.ImageSurface(cairocffi.FORMAT_ARGB32, self.outer_w, self.outer_h)
        stride = surface.get_stride()
        data = cairocffi.cairo.cairo_image_surface_get_data(surface._pointer)
        image_buffer = lib.cairo_buffer_create(self.outer_w, self.outer_h, stride, data)
        if image_buffer == ffi.NULL:
            raise RuntimeError("Couldn't allocate cairo buffer.")

        return image_buffer, surface

    def _get_edges(self, bw, x, y, width, height):
        return [
            (x, y, width, bw),
            (self.outer_w - bw - x, bw + y, bw, height - 2 * bw),
            (x, self.outer_h - y - bw, width, bw),
            (x, bw + y, bw, height - bw * 2),
        ]

    def _x11_draw(
        self, window, depth, pixmap, gc, outer_w, outer_h, borderwidth, x, y, width, height
    ):
        self.visual = window.get_attributes().visual
        self.window = window
        self.core = window.conn.conn.core
        self.wid = window.wid
        self.depth = depth
        self.pixmap = pixmap
        self.gc = gc
        self.outer_w = outer_w
        self.outer_h = outer_h
        if self.needs_surface:
            surface = self._create_xcb_surface()
        else:
            surface = None
        self.x11_draw(borderwidth, x, y, width, height, surface)
        if surface is not None:
            surface.finish()

    def x11_draw(self, borderwidth, x, y, width, height, surface):
        self.draw(surface, borderwidth, x, y, width, height)

    def _wayland_draw(self, window, outer_w, outer_h, borderwidth, x, y, width, height):
        if not HAS_WAYLAND:
            raise ConfigError("Unable to load wayland backend during imports.")
        self.window = window
        self.wid = window.wid
        self.outer_w = outer_w
        self.outer_h = outer_h
        self.rects = self._get_edges(borderwidth, x, y, width, height)
        if self.needs_surface:
            image_buffer, surface = self._new_buffer()
        else:
            image_buffer = None
            surface = None

        scenes = self.wayland_draw(borderwidth, x, y, width, height, surface)

        if self.needs_surface:
            scenes = []
            for x, y, w, h in self.rects:
                scene_buffer = SceneBuffer.create(self.window.container, Buffer(image_buffer))
                scene_buffer.node.set_position(x, y)
                wlr_lib.wlr_scene_buffer_set_dest_size(scene_buffer._ptr, w, h)
                fbox = wlr_ffi.new("struct wlr_fbox *")
                fbox.x = x
                fbox.y = y
                fbox.width = w
                fbox.height = h
                wlr_lib.wlr_scene_buffer_set_source_box(scene_buffer._ptr, fbox)
                scenes.append(scene_buffer)

        return scenes, image_buffer, surface

    def wayland_draw(self, borderwidth, x, y, width, height, surface):
        self.draw(surface, borderwidth, x, y, width, height)

    def draw(self, surface, bw, x, y, width, height):
        pass


class GradientBorder(_BorderStyle):
    """
    Renders borders with a gradient.

    ``colours`` defines the list of colours in the gradient.

    The angle/direction of the gradient is set by the ``points``
    parameter. This is a list of a two (x, y) tuples. The x and y
    values are relative to the window. A value of (0, 0) is the top
    left corner while (1, 1) represents the bottom right corner.

    ``offsets`` is used to adjust the position of the colours within
    the gradient. Leaving this as ``None`` will space the colours evenly. The
    values need to be in ascending order and in the range of 0.0 (the very start of
    the gradient) and 1.0 (the end of the gradient). These represent positions on the
    imagninary line between the two ``points`` defined above.

    When ``radial=True`` the ``points`` parameter has no impact. The gradient will be drawn from the center
    of the window to the corner of the window. ``offsets`` can still be used to adjust the
    spacing of the colours.
    """

    defaults = [
        ("colours", ["00ffff", "0000ff"], "List of colours in the gradient"),
        ("points", [(0, 0), (0, 1)], "Points to size/angle the gradient. See docs for more."),
        (
            "offsets",
            None,
            "Offset locations (in range of 0.0-1.0) for gradient stops. ``None`` to use regular spacing.",
        ),
        ("radial", False, "Use radial gradient"),
    ]

    _screenshots = [
        ("max_gradient_border.png", 'border_focus=GradientBorder(colours=["00f", "0ff"])'),
        (
            "max_gradient_border_2.png",
            'border_focus=GradientBorder(colours=["f0f", "00f", "0ff"], points=[(0, 1), (1, 0)])',
        ),
    ]

    def __init__(self, **config):
        _BorderStyle.__init__(self, **config)
        self.add_defaults(GradientBorder.defaults)

        if not isinstance(self.colours, (list, tuple)):
            raise ConfigError("colours must be a list or tuple.")

        if self.offsets is None:
            self.offsets = [x / (len(self.colours) - 1) for x in range(len(self.colours))]
        elif len(self.offsets) != len(self.colours):
            raise ConfigError("'offsets' must be same length as 'colours'.")

        self._check_colours()

    def draw(self, surface, bw, x, y, width, height):
        def pos(point):
            return tuple(p * d for p, d in zip(point, (width, height)))

        with cairocffi.Context(surface) as ctx:
            ctx.save()
            ctx.translate(x, y)

            # Use winding rules to clip an area equal to the borders
            ctx.rectangle(0, 0, width, height)
            ctx.rectangle(width - bw, bw, -(width - 2 * bw), (height - 2 * bw))
            ctx.clip()

            if self.radial:
                ctx.translate(width // 2, height // 2)
                ctx.scale(width, height)
                gradient = cairocffi.RadialGradient(0, 0, 0, 0, 0, HALF_ROOT_2)
            else:
                gradient = cairocffi.LinearGradient(*pos(self.points[0]), *pos(self.points[1]))

            for offset, c in zip(self.offsets, self.colours):
                gradient.add_color_stop_rgba(offset, *rgb(c))

            ctx.set_source(gradient)
            ctx.paint()
            ctx.restore()


class GradientFrame(_BorderStyle):
    """
    Renders a frame with a gradient. Each edge's gradient is from the outside towards the centre.
    """

    defaults = [
        ("colours", ["00ffff", "0000ff"], "List of colours in the gradient"),
    ]

    _screenshots = [
        ("max_gradient_frame.png", 'border_focus=GradientFrame(colours=["00f", "0ff"])'),
    ]

    def __init__(self, **config):
        _BorderStyle.__init__(self, **config)
        self.add_defaults(GradientFrame.defaults)
        self.offsets = [x / (len(self.colours) - 1) for x in range(len(self.colours))]

        if not isinstance(self.colours, (list, tuple)):
            raise ConfigError("colours must be a list or tuple.")

        self._check_colours()

    def draw(self, surface, bw, x, y, width, height):
        with cairocffi.Context(surface) as ctx:
            ctx.save()
            ctx.translate(x, y)

            edges = [
                ([(0, 0), (width, 0), (width - bw, bw), (bw, bw)], (0, 0, 0, bw)),
                (
                    [(width, 0), (width, height), (width - bw, height - bw), (width - bw, bw)],
                    (width, 0, width - bw, 0),
                ),
                (
                    [(0, height), (bw, height - bw), (width - bw, height - bw), (width, height)],
                    (0, height, 0, height - bw),
                ),
                ([(0, 0), (bw, bw), (bw, height - bw), (0, height)], (0, 0, bw, 0)),
            ]

            for points, grad_points in edges:
                ctx.new_path()
                ctx.move_to(*points.pop(0))
                for p in points:
                    ctx.line_to(*p)
                ctx.close_path()
                ctx.clip()
                gradient = cairocffi.LinearGradient(*grad_points)
                for offset, c in zip(self.offsets, self.colours):
                    gradient.add_color_stop_rgba(offset, *rgb(c))
                ctx.set_source(gradient)
                ctx.paint()
                ctx.reset_clip()
            ctx.restore()


class ScreenGradientBorder(GradientBorder):
    """
    Renders a border with a gradient which is scaled to the screen, rather than the window.
    This means that a window's border will change depending on where it is in the screen.

    ``colours`` defines the list of colours in the gradient.

    The angle/direction of the gradient is set by the ``points``
    parameter. This is a list of a two (x, y) tuples. The x and y
    values are relative to the screen. A value of (0, 0) is the top
    left corner while (1, 1) represents the bottom right corner.

    ``offsets`` is used to adjust the position of the colours within
    the gradient. Leaving this as ``None`` will space the colours evenly. The
    values need to be in ascending order and in the range of 0.0 (the very start of
    the gradient) and 1.0 (the end of the gradient). These represent positions on the
    imagninary line between the two ``points`` defined above.

    When ``radial=True`` the ``points`` parameter has no impact. The gradient will be drawn from the center
    of the screen to the corner of the screen. ``offsets`` can still be used to adjust the
    spacing of the colours.
    """

    _to_add = """
    Setting ``per_screen=False`` will render the gradient across all monitors with the behaviour of
    ``points`` being adjusted to represent the full screen area covered by all monitors.
    """
    defaults = [
        # ("per_screen", True, "Whether gradient is redrawn per screen. If False, gradient spans all monitors."),
    ]

    _screenshots = [
        (
            "matrix_screen_gradient_1.png",
            'ScreenGradientBorder(colours=["f00", "0f0", "00f"], points=[(0,0), (1,1)])',
        ),
        ("matrix_screen_gradient_2.png", "Gradient is applied to screen..."),
        ("matrix_screen_gradient_3.png", "...no matter how many windows are open."),
    ]

    def __init__(self, **config):
        GradientBorder.__init__(self, **config)
        self.add_defaults(ScreenGradientBorder.defaults)

    def draw(self, surface, bw, x, y, width, height):
        assert qtile is not None
        win = qtile.windows_map.get(self.wid)
        if win and win.group and win.group.screen:
            w = win.group.screen.width
            h = win.group.screen.height
            win_x = win.x
            win_y = win.y
        else:
            w = width
            h = height
            win_x = win_y = 0

        def pos(point):
            return tuple(
                (p * d) - n - m for p, d, n, m in zip(point, (w, h), (x, y), (win_x, win_y))
            )

        with cairocffi.Context(surface) as ctx:
            ctx.save()
            ctx.translate(x, y)

            # Use winding rules to clip an area equal to the borders
            ctx.rectangle(0, 0, width, height)
            ctx.rectangle(width - bw, bw, -(width - 2 * bw), (height - 2 * bw))
            ctx.clip()

            if self.radial:
                ctx.translate(w // 2 - x - win_x, h // 2 - y - win_y)
                ctx.scale(w, h)
                gradient = cairocffi.RadialGradient(0, 0, 0, 0, 0, HALF_ROOT_2)
            else:
                gradient = cairocffi.LinearGradient(*pos(self.points[0]), *pos(self.points[1]))

            for offset, c in zip(self.offsets, self.colours):
                gradient.add_color_stop_rgba(offset, *rgb(c))

            ctx.set_source(gradient)
            ctx.paint()
            ctx.restore()


class SolidEdge(_BorderStyle):
    """
    A decoration that renders a solid border. Colours can be specified for
    each edge.
    """

    _screenshots = [("max_solid_edge.png", 'SolidEdge(colours=["00f", "0ff", "00f", "0ff"])')]

    needs_surface = False

    defaults = [
        (
            "colours",
            ["00f", "00f", "00f", "00f"],
            "List of colours for each edge of the window [N, E, S, W].",
        )
    ]

    def __init__(self, **config):
        _BorderStyle.__init__(self, **config)
        self.add_defaults(SolidEdge.defaults)

        if not (isinstance(self.colours, (list, tuple)) and len(self.colours) == 4):
            raise ConfigError("colours must have 4 values.")

        self._check_colours()

    def x11_draw(self, borderwidth, x, y, width, height, surface):
        edges = self._get_edges(borderwidth, x, y, width, height)
        for (x, y, w, h), c in zip(edges, self.colours):
            self.core.ChangeGC(
                self.gc, xcffib.xproto.GC.Foreground, [self.window.conn.color_pixel(c)]
            )
            rect = xcffib.xproto.RECTANGLE.synthetic(x, y, w, h)
            self.core.PolyFillRectangle(self.pixmap, self.gc, 1, [rect])

    def wayland_draw(self, borderwidth, x, y, width, height, surface):
        scene_rects = []
        edges = self._get_edges(borderwidth, x, y, width, height)
        for (x, y, w, h), c in zip(edges, self.colours):
            rect = SceneRect(self.window.container, w, h, _rgb(c))
            rect.node.set_position(x, y)
            scene_rects.append(rect)

        return scene_rects


class ConditionalBorder(_BorderStyle):
    """
    A decoration that allows finer control as to which border is applied to which window.

    To configure the decoration, you need to provide two parameters:

      * ``matches``: a list of tuples of (Match rules, border style)
      * ``fallback``: border style to apply if no matches

    Example:

    .. code:: python

        from qtile_extras.layout.decorations import ConditionalBorder, GradientBorder

        layouts = [
            layout.MonadTall(
                border_focus=ConditionalBorder(
                    matches=[
                        (Match(wm_class="vlc"), GradientBorder(colours=["e85e00", "e80000", "e85e00"])),
                        (Match(wm_class="firefox"), "f0f")
                    ],
                    fallback="00f"),
                border_width=4
            ),
        ]

    The above code will draw an orange/red gradient border when VLC is focused, a solid purple border when
    firefox is focused and a solid blue border when any other window is focused.

    Matches can be provided as single rule or a list of rules. The advanced combination of rules (using
    ``&``, ``|``, ``~``) is also supported here.

    """

    needs_surface = False

    defaults = [
        ("matches", [], "List of tuples of match rules and applicable"),
        (
            "fallback",
            "fff",
            "Border to be applied if no matches",
        ),
    ]

    def __init__(self, **config):
        _BorderStyle.__init__(self, **config)
        self.add_defaults(ConditionalBorder.defaults)

    def compare(self, win):
        if not win:
            return self.fallback

        for match, colour in self.matches:
            if isinstance(match, (list, str)):
                matched = any(m.compare(win) for m in match)
            else:
                matched = match.compare(win)

            if matched:
                return colour

        return self.fallback


class CustomBorder(_BorderStyle):
    """
    Decoration to allow users to create custom borders.

    To use this border, you need to define a function that takes four arguments:

        - ``ctx``: A ``cairocffi.Context`` object for the drawing operations
        - ``border_width``: the width of the border to be drawn
        - ``width``: the width of the area to be drawn
        - ``height``: the height of the area to be drawn

    ``width`` and ``height`` are defined that the top left corner of the border is
    at (0, 0) in the context. The bottom right corner is (width, height).

    For example:

    .. code:: python

        from qtile_extras.layout.decorations import CustomBorder


        def stripey_red_border(ctx, bw, w, h):
            ctx.set_source_rgb(1,0,0)
            for x in range(0, h, 10):
                ctx.new_path()
                ctx.move_to(0, x)
                ctx.line_to(w, x)
                ctx.set_line_width(4)
                ctx.stroke()


        layouts = [
            layout.Max(
                margin=5,
                border_width=10,
                border_focus=CustomBorder(func=stripey_red_border)
            ),
        ]

    .. note::

        The decoration will not clip the drawing to the area within the specified border
        width. Therefore, if you draw outside this area and have defined multiple borders,
        this drawing may overlap those borders.

    """

    needs_surface = True

    defaults = [
        ("func", None, "Custom function to render border. See docstring for more."),
    ]

    _screenshots = [
        ("border_red_stripe.png", "Red stripey border"),
        ("border_green_diagonal.png", "Diagonal green border"),
    ]

    def __init__(self, **config):
        _BorderStyle.__init__(self, **config)
        self.add_defaults(CustomBorder.defaults)

        if self.func is None:
            raise ConfigError("Draw function is not set.")
        elif not callable(self.func):
            raise ConfigError("Draw function is not callable.")
        elif len(inspect.signature(self.func).parameters) != 4:
            raise ConfigError("Draw function must take 4 arguments.")

    def draw(self, surface, bw, x, y, width, height):
        with cairocffi.Context(surface) as ctx:
            ctx.translate(x, y)
            self.func(ctx, bw, width, height)


class RoundedCorners(_BorderStyle):
    """
    A simple decoration to draw rounded corners.

    .. note::

        This border will not render well on x11 backends as it does not implement transparency.
        As a result, the border will display with black artefacts in the corners.

    """

    needs_surface = True

    defaults = [
        ("colour", "00f", "Border colour"),
    ]

    _screenshots = [
        ("border_rounded_corners.png", "Rounded corners"),
    ]

    def __init__(self, **config):
        _BorderStyle.__init__(self, **config)
        self.add_defaults(RoundedCorners.defaults)

    def draw(self, surface, bw, x, y, width, height):
        with cairocffi.Context(surface) as ctx:
            ctx.translate(x, y)

            radius = bw / 2
            degrees = math.pi / 180.0

            ctx.new_sub_path()
            ctx.arc(width - bw, bw, radius, -90 * degrees, 0 * degrees)
            ctx.arc(width - bw, height - bw, radius, 0 * degrees, 90 * degrees)
            ctx.arc(bw, height - bw, radius, 90 * degrees, 180 * degrees)
            ctx.arc(bw, bw, radius, 180 * degrees, 270 * degrees)
            ctx.close_path()

            ctx.set_line_width(bw)
            ctx.set_source_rgba(*rgb(self.colour))
            ctx.stroke()


class ConditionalBorderWidth(Configurable):
    """
    A class that allows finer control as to which border width is applied to which window.

    To configure the border width, you need to provide two parameters:

      * ``matches``: a list of tuples of (Match rules, border width)
      * ``default``: border width to apply if no matches

    Matches are applied in order and will return a border width as soon as a rule matches.

    It can be used in place of the integer border width layout when defining layouts in your
    config. For example:

    .. code:: python

        from qtile_extras.layout.decorations import ConditionalBorderWidth

        layouts = [
            layout.Columns(
                border_focus_stack=["#d75f5f", "#8f3d3d"],
                border_width=ConditionalBorderWidth(
                    default=2,
                    matches=[(Match(wm_class="vlc"), 0)])
            ),
            ...
        ]

    The above code will default to a border width of 2 but will apply a border width of zero
    for VLC windows.

    """

    defaults = [
        ("default", 0, "Default border width value if no rule is matched"),
        ("matches", [], "List of rules to apply border widths. See docs for more details."),
    ]

    def __init__(self, **config):
        Configurable.__init__(self, **config)
        self.add_defaults(ConditionalBorderWidth.defaults)

    def get_border_for_window(self, win):
        for rule, value in self.matches:
            if rule.compare(win):
                return value
        return self.default

    # Layouts size windows by subtracting the border width so we
    # need to allow the multiplication to work on the custom class
    # The size will be fixed with the injected window.place code.
    def __mul__(self, other):
        return other * self.default

    __rmul__ = __mul__
