"""Viewport navigation by touch: pan, rotate and zoom regions and their overlay, Recenter View, Lock Rotation and
Toggle Touch Controls, and the Control Zones panel. Kept apart so it can be removed as a unit once Blender ships its
own touch navigation (ADR 0001): delete this package and its lines in source/__init__.py. Nothing else imports it;
its settings are still add-on preferences (preferences.py). The object tap (features/object_tap) takes a touch first
and hands it over here once it moves."""

from types import ModuleType

from ..core import register_parts, unregister_parts
from . import keymaps, overlay, panel, touch, view

# modules with register()/unregister(), registered in this order and unregistered in reverse
PARTS: list[ModuleType] = [
    view,
    touch,
    # after the operators they run
    keymaps,
    overlay,
    panel,
]


def register():
    register_parts(PARTS)


def unregister():
    unregister_parts(PARTS)
