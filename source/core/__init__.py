"""Shared mechanisms every part builds on: the Action catalog and Action Lists, Detour, Hop, Scene Checkpoint,
settings and preferences. See GLOSSARY.md for the terms."""

from types import ModuleType

# modules with register()/unregister(), registered in this order and unregistered in reverse
PARTS: list[ModuleType] = []


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
