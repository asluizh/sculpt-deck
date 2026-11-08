"""Object tap: tap an object to select it or switch to it, double tap, long press to toggle its selection. Sculpt
workflow, not navigation (ADR 0001); see tap.py for how it shares a touch with navigation."""

from types import ModuleType

from ...core import register_parts, unregister_parts
from . import settings, tap

# modules with register()/unregister(), registered in this order and unregistered in reverse
PARTS: list[ModuleType] = [
    settings,
    tap,
]


def register():
    register_parts(PARTS)


def unregister():
    unregister_parts(PARTS)
