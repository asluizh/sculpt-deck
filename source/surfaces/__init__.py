"""Action Surfaces: the widget, the action pie, pen buttons and clicks, each with its settings and panels."""

from types import ModuleType

from ..core import register_parts, unregister_parts
from . import action_slots, pie, widget

# modules with register()/unregister(), registered in this order and unregistered in reverse
PARTS: list[ModuleType] = [
    action_slots,
    widget,
    pie,
]


def register():
    register_parts(PARTS)


def unregister():
    unregister_parts(PARTS)
