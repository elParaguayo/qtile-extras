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
from libqtile import bar, widget


class QTEMirror(widget.Mirror):
    """
    A modified version of Qtile's Mirror widget.

    The only difference is to ensure mirrored widgets are sized correctly.

    ..important::

        The mirror will also reflect any decorations of the original widget. Therefore,
        if you need different decoration behaviour, you must create a new instance of the
        widget.

    This widget should not be created directly by users.
    """

    _qte_compatibility = True

    def __init__(self, reflection, **config):
        widget.Mirror.__init__(self, reflection, **config)
        self.decorations = getattr(reflection, "decorations", list())

        if self.length_type in [bar.CALCULATED, bar.STRETCH]:
            self.length = 0
        else:
            self.length = self.reflects._length
