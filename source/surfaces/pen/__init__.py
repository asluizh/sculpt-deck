"""Pen buttons: a click and a hold for each pen side button, per mode, with their settings and sidebar panel."""

from types import ModuleType

from ...core import register_parts, unregister_parts
from . import button, panel, settings

# settings first: the add-on preferences, registered after every part, hold them
PARTS: list[ModuleType] = [settings, button, panel]


def register():
    register_parts(PARTS)


def unregister():
    unregister_parts(PARTS)
