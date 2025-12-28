# Copyright (c) 2021 elParaguayo
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
from libqtile.widget.base import _TextBox

from qtile_extras.widget import add_decoration_support, modify


def test_decorator_no_initialise():
    class MyUndecoratedTextWidget(_TextBox):
        pass

    @add_decoration_support
    class MyDecoratedTextWidget(_TextBox):
        pass

    # undecorated class should have same dir() contents
    assert dir(_TextBox) == dir(MyUndecoratedTextWidget)

    # new methods have been injected so dir() should be different
    assert dir(_TextBox) != dir(MyDecoratedTextWidget)


def test_decorator_initialise():
    @add_decoration_support
    class MyTextWidget(_TextBox):
        pass

    txt = MyTextWidget(text="Test Widget", test_parameter=True)

    assert isinstance(txt, MyTextWidget)
    assert txt._text == "Test Widget"
    assert txt.test_parameter


def test_modify_no_initialise():
    class MyTextWidget(_TextBox):
        pass

    txt = MyTextWidget
    pre_type = type(txt)
    pre_dir = dir(txt)

    wrapped = modify(MyTextWidget, initialise=False)

    # modify returns same class
    assert pre_type is type(wrapped)

    # new methods have been injected so dir() should be different
    assert pre_dir != dir(wrapped)


def test_modify_initialise():
    class MyTextWidget(_TextBox):
        pass

    txt = modify(MyTextWidget, text="Test Widget", test_parameter=True)

    assert isinstance(txt, MyTextWidget)
    assert txt._text == "Test Widget"
    assert txt.test_parameter
