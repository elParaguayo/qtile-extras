from .constants import *
from .context import Context as Context
from .ffi_build import ffi as ffi
from .fonts import FontFace as FontFace, FontOptions as FontOptions, ScaledFont as ScaledFont, ToyFontFace as ToyFontFace
from .matrix import Matrix as Matrix
from .patterns import Gradient as Gradient, LinearGradient as LinearGradient, Pattern as Pattern, RadialGradient as RadialGradient, SolidPattern as SolidPattern, SurfacePattern as SurfacePattern
from .surfaces import ImageSurface as ImageSurface, PDFSurface as PDFSurface, PSSurface as PSSurface, RecordingSurface as RecordingSurface, SVGSurface as SVGSurface, Surface as Surface, Win32PrintingSurface as Win32PrintingSurface, Win32Surface as Win32Surface
from .xcb import XCBSurface as XCBSurface
from typing import Any

VERSION: Any
version: str
version_info: Any

def dlopen(ffi, library_names, filenames): ...

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
