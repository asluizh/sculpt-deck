"""Interface: what otherwise needs the keyboard around the viewport. Toggle Sidebar, Tools Region Swap, the next
Pivot mode and Cycle Control Gizmo, a left-click drag that scrolls UI lists and menus, and the Viewport Options
sidebar panel. Its setting is the Sculpt Pivot Mode."""

from types import ModuleType

from ...core import register_parts, unregister_parts
from . import list_drag, panel, settings, toggles

# modules with register()/unregister(), registered in this order and unregistered in reverse
PARTS: list[ModuleType] = [
    settings,
    toggles,
    list_drag,
    panel,
]


def register():
    register_parts(PARTS)


def unregister():
    unregister_parts(PARTS)
