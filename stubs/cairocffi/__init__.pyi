from typing import Any

from .constants import *
from .context import Context as Context
from .ffi_build import ffi as ffi
from .fonts import FontFace as FontFace
from .fonts import FontOptions as FontOptions
from .fonts import ScaledFont as ScaledFont
from .fonts import ToyFontFace as ToyFontFace
from .matrix import Matrix as Matrix
from .patterns import Gradient as Gradient
from .patterns import LinearGradient as LinearGradient
from .patterns import Pattern as Pattern
from .patterns import RadialGradient as RadialGradient
from .patterns import SolidPattern as SolidPattern
from .patterns import SurfacePattern as SurfacePattern
from .surfaces import ImageSurface as ImageSurface
from .surfaces import PDFSurface as PDFSurface
from .surfaces import PSSurface as PSSurface
from .surfaces import RecordingSurface as RecordingSurface
from .surfaces import Surface as Surface
from .surfaces import SVGSurface as SVGSurface
from .surfaces import Win32PrintingSurface as Win32PrintingSurface
from .surfaces import Win32Surface as Win32Surface
from .xcb import XCBSurface as XCBSurface

VERSION: Any
version: str
version_info: Any

def dlopen(ffi, library_names, filenames): ...  # noqa: F811

cairo: Any

class _keepref:
    ref: Any
    func: Any
    def __init__(self, ref, func) -> None: ...
    def __call__(self, *args, **kwargs) -> None: ...

class CairoError(Exception):
    status: Any
    def __init__(self, message, status) -> None: ...

Error = CairoError
STATUS_TO_EXCEPTION: Any

def cairo_version(): ...
def cairo_version_string(): ...
def install_as_pycairo() -> None: ...
