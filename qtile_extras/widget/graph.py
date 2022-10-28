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
import libqtile.widget.graph as _graph

__all__ = [
    "CPUGraph",
    "MemoryGraph",
    "SwapGraph",
    "NetGraph",
    "HDDGraph",
    "HDDBusyGraph",
]


class _Graph(_graph._Graph):
    _qte_compatibility = True

    @property
    def graphwidth(self):
        """Amended property to ensure graph doesn't draw over the decoration."""
        return self._length - self.border_width * 2 - self.margin_x * 2


class CPUGraph(_Graph, _graph.CPUGraph):
    pass


class MemoryGraph(_Graph, _graph.MemoryGraph):
    pass


class SwapGraph(_Graph, _graph.SwapGraph):
    pass


class NetGraph(_Graph, _graph.NetGraph):
    pass


class HDDGraph(_Graph, _graph.HDDGraph):
    pass


class HDDBusyGraph(_Graph, _graph.HDDBusyGraph):
    pass
