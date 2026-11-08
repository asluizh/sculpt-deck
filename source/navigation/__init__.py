"""Viewport navigation by touch: pan, rotate and zoom regions and their overlay, Recenter View, Lock Rotation and
Toggle Touch Controls, the floating toggle, its settings, the input mode in the sidebar and the Control Zones panel.
Kept apart so it can be removed as a unit once Blender ships its own touch navigation (ADR 0001): deleting this
package is enough, source/__init__.py registers it only when it's there. Nothing else imports it; its settings and
its Actions are in the add-on preferences and the Action catalog only while it's registered. The object tap
(features/object_tap) takes a touch first and hands it over here once it moves."""

from types import ModuleType

from ..core import register_parts, unregister_parts
from . import keymaps, overlay, panel, settings, toggle, touch, view

# modules with register()/unregister(), registered in this order and unregistered in reverse
PARTS: list[ModuleType] = [
    settings,
    view,
    touch,
    # after the operators they run
    keymaps,
    overlay,
    toggle,
    panel,
]


def register():
    register_parts(PARTS)


def unregister():
    unregister_parts(PARTS)
