from units.composed_unit import ComposedUnit as ComposedUnit
from units.leaf_unit import LeafUnit as LeafUnit
from units.named_composed_unit import NamedComposedUnit as NamedComposedUnit
from units.registry import REGISTRY as REGISTRY

__contact__: str

def unit(specifier): ...
def named_unit(symbol, numer, denom, multiplier: int = ..., is_si: bool = ...): ...
def scaled_unit(new_symbol, base_symbol, multiplier, is_si: bool = ...): ...
def si_prefixed_unit(unit_str): ...
