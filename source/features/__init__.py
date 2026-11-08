"""Sculpt workflow features, one sub-package each (operators, toolbar tools, headers, gizmos and settings)."""

from types import ModuleType

from ..core import register_parts, unregister_parts
from . import array, mirror, objects

# modules with register()/unregister(), registered in this order and unregistered in reverse
PARTS: list[ModuleType] = [
    objects,
    # toolbar tools join the end of Local Transform's section in registration order: Mirror, then the arrays
    mirror,
    array,
]


def register():
    register_parts(PARTS)


def unregister():
    unregister_parts(PARTS)
