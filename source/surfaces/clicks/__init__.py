"""Double click and right click: an action per mode for mouse and touch, from the pen button click list, with
their sidebar panels. The bindings are stored with the pen buttons (pen/settings.py) and run by its BindingRunner."""

from types import ModuleType

from ...core import register_parts, unregister_parts
from . import action, panel

PARTS: list[ModuleType] = [action, panel]


def register():
    register_parts(PARTS)


def unregister():
    unregister_parts(PARTS)
