"""Masks: Invert Mask and Reveal Hidden in Sculpt Mode, each with its own undo step."""

from types import ModuleType

from ...core import register_parts, unregister_parts
from . import mask_operators

# modules with register()/unregister(), registered in this order and unregistered in reverse
PARTS: list[ModuleType] = [
    mask_operators,
]


def register():
    register_parts(PARTS)


def unregister():
    unregister_parts(PARTS)
