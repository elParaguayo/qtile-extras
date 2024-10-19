from numbers import Number
from typing import Any, Protocol

import pint
from _typeshed import Incomplete
from stravalib.exc import warn_units_deprecated as warn_units_deprecated

class UnitsQuantity(Protocol):
    num: float
    unit: str

class Quantity:
    q: Incomplete
    def __init__(self, q: pint.Quantity) -> None: ...
    @property
    def num(self): ...
    @property
    def unit(self): ...
    def __int__(self) -> int: ...
    def __float__(self) -> float: ...
    def __getattr__(self, item): ...

class UnitConverter:
    unit: Incomplete
    def __init__(self, unit: str) -> None: ...
    def __call__(self, q: Number | pint.Quantity | UnitsQuantity): ...

def is_quantity_type(obj: Any): ...

meter: Incomplete

meters: Incomplete
second: Incomplete
seconds: Incomplete
hour: Incomplete
hours: Incomplete
foot: Incomplete
feet: Incomplete
mile: Incomplete
miles: Incomplete
kilometer: Incomplete
kilometers: Incomplete
meters_per_second: Incomplete
miles_per_hour: Incomplete
mph: Incomplete
kilometers_per_hour: Incomplete
kph: Incomplete
kilogram: Incomplete
kilograms: Incomplete
kg: Incomplete
kgs: Incomplete
pound: Incomplete
pounds: Incomplete
lb: Incomplete
lbs: Incomplete

def c2f(celsius): ...
