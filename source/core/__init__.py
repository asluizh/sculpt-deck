"""Shared mechanisms every part builds on: the Action catalog and Action Lists, Detour, Hop, Scene Checkpoint, the
modal drag the tool gizmos share, settings and preferences. See GLOSSARY.md for the terms."""

from types import ModuleType

from . import detour, history, settings, step_over, ui

# modules with register()/unregister(), registered in this order and unregistered in reverse
PARTS: list[ModuleType] = [
    settings,
    # the main sidebar panel, before the parts' sub-panels
    ui,
    detour,
    step_over,
    history,
]


def register_parts(parts: list[ModuleType]):
    for part in parts:
        part.register()


def unregister_parts(parts: list[ModuleType]):
    for part in reversed(parts):
        part.unregister()


def register():
    register_parts(PARTS)


def unregister():
    unregister_parts(PARTS)
