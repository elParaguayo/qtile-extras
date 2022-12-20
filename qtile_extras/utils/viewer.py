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
import xcffib.render
from libqtile.backend.base import Internal
from libqtile.configurable import Configurable
from libqtile.lazy import lazy

from qtile_extras.popup.toolkit import PopupAbsoluteLayout, PopupFrame, PopupText


DEFAULT_LAYOUT = PopupAbsoluteLayout(
    width=600,
    height=400,
    controls=[
        PopupText(
            pos_x=10,
            pos_y=10,
            name="label",
            width=580,
            height=20,
            h_align="center"
        ),
        PopupFrame(
            pos_x=10,
            pos_y=40,
            name="frame",
            width=580,
            height=350
        )
    ]
)


def double_to_fixed(double):
    """Recreates the XDoubleToFixed macro in XRender."""
    return int(double * 65536)


class WindowSwitcher(Configurable):

    defaults = [
        ("layout", DEFAULT_LAYOUT, "Layout for showing window previews")
    ]

    def __init__(self, **config):
        Configurable.__init__(self, **config)
        self.add_defaults(WindowSwitcher.defaults)
        self.visible = False
        self.index = 0
        self.conn = None
        self.render = None

    def _setup_render(self):
        self.conn = self.qtile.core.conn.conn
        self.render = self.conn(xcffib.render.key)
        self.render.QueryVersion(xcffib.render.MAJOR_VERSION, xcffib.render.MINOR_VERSION)

        setup = self.conn.get_setup()
        depth = setup.roots[0].root_depth
        visual = setup.roots[0].root_visual
        self.root_depth = depth
        self.root_visual = visual

        screens = self.render.QueryPictFormats().reply().screens
        self.screen = screens[0]

    def _find_format(self, screen, depth=None, visual=None):
        if depth is None:
            depth = self.root_depth

        fmt = None
        for d in screen.depths:
            if d.depth == depth:
                for v in d.visuals:
                    if visual is None or v.visual == visual:
                        fmt = v.format
                        break
            if fmt:
                break
        else:
            raise RuntimeError("Can't find format for screen")

        return fmt

    def show(self, qtile):
        """Method to launch the window preview. Should be bound to a lazy.function call."""
        if self.visible:
            return

        # X11 only for now
        if qtile.core.name != "x11":
            return

        self.qtile = qtile
        self.windows = [k for k, v in qtile.windows_map.items() if not isinstance(v, Internal)]
        print(self.windows)

        if not self.render:
            self._setup_render()

        self.qtile.switcher = self
    
        self.layout._configure(self.qtile)
        wid = self.layout.popup.win.wid
        self.layout.update_controls(label=str(wid))


        pic_window = self.conn.generate_id()
        self.render.CreatePicture(
            pic_window,
            self.windows[0],
            self._find_format(self.screen, visual=self.root_visual),
            0,
            None
        )
 
        self.layout.show(centered=True)

        pic_popup = self.conn.generate_id()
        self.render.CreatePicture(
            pic_popup,
            wid,
            self._find_format(self.screen, 32),
            0,
            None
        )
        self.render.Composite(
            xcffib.render.PictOp.Src,
            pic_window,
            0,
            pic_popup,
            0,
            0,
            0,
            0,
            0,
            0,
            580,
            350
        ) 

        self.conn.flush()