"""Interface: what otherwise needs the keyboard around the viewport. Toggle Sidebar, Tools Region Swap and the next
Pivot mode, and a left-click drag that scrolls UI lists and menus.

The Sculpt Pivot Mode setting is still an add-on preference (preferences.py); it moves with the settings (#12)."""

from types import ModuleType

from ...core import register_parts, unregister_parts
from . import list_drag, toggles

# modules with register()/unregister(), registered in this order and unregistered in reverse
PARTS: list[ModuleType] = [
    toggles,
    list_drag,
]


def register():
    register_parts(PARTS)


def unregister():
    unregister_parts(PARTS)
