"""The Widget: the on-screen buttons, each firing the Action set for it in the current mode, with its operators,
gizmos, settings panels and the floating touch toggle drawn by the same gizmo group."""

from types import ModuleType

from ...core import register_parts, unregister_parts
from . import gizmo_group_2d, operators, panels

# modules with register()/unregister(), registered in this order and unregistered in reverse
PARTS: list[ModuleType] = [operators, gizmo_group_2d, panels]


def register():
    register_parts(PARTS)


def unregister():
    unregister_parts(PARTS)
