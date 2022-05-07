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
import logging
from importlib import reload

import pytest
from libqtile.log_utils import init_log
from libqtile.widget.import_error import ImportErrorWidget

import qtile_extras.widget


def bad_importer(*args, **kwargs):
    raise ImportError()


def test_init_import_error(monkeypatch, caplog):
    """Check we get an ImportError widget with missing import?"""
    init_log(logging.INFO)
    monkeypatch.setattr("qtile_extras.widget.importlib.import_module", bad_importer)
    widget = qtile_extras.widget.WiFiIcon()
    assert isinstance(widget, ImportErrorWidget)
    assert "Unmet dependencies" in caplog.text


def test_init_import_error_no_fallback(monkeypatch, caplog):
    """If there's no fallback, we get an ImportError"""
    init_log(logging.INFO)
    monkeypatch.setattr("qtile_extras.widget.importlib.import_module", bad_importer)
    monkeypatch.setattr("libqtile.widget.import_error.make_error", None)
    reload(qtile_extras.widget)

    with pytest.raises(ImportError):
        _ = qtile_extras.widget.WiFiIcon()


def test_init_widget_dir():
    """Check patched dir method"""
    assert dir(qtile_extras.widget) == sorted(list(qtile_extras.widget.all_widgets.keys()))
