"""The Action Pie: a pie of Actions set per mode, opened from a Widget or pen button, and the All Actions popup it
can hold, with its settings panel."""

from types import ModuleType

from ...core import register_parts, unregister_parts
from . import menus, panels

# modules with register()/unregister(), registered in this order and unregistered in reverse
PARTS: list[ModuleType] = [menus, panels]


def register():
    register_parts(PARTS)


def unregister():
    unregister_parts(PARTS)
