"""Viewport navigation by touch: pan, rotate and zoom regions and their overlay. Kept apart so it can be removed
as a unit once Blender ships its own touch navigation (ADR 0001)."""

from types import ModuleType

from ..core import register_parts, unregister_parts

# modules with register()/unregister(), registered in this order and unregistered in reverse
PARTS: list[ModuleType] = []


def register():
    register_parts(PARTS)


def unregister():
    unregister_parts(PARTS)
