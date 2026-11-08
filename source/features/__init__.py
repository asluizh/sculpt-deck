"""Sculpt workflow features, one sub-package each (operators, toolbar tools, headers, gizmos and settings)."""

from types import ModuleType

from ..core import register_parts, unregister_parts
from . import objects

# modules with register()/unregister(), registered in this order and unregistered in reverse
PARTS: list[ModuleType] = [
    objects,
]


def register():
    register_parts(PARTS)


def unregister():
    unregister_parts(PARTS)
